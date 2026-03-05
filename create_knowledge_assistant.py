# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Knowledge Assistant 作成ノートブック
# MAGIC
# MAGIC Vector Search Index を知識ソースとして、Agent Bricks Knowledge Assistant を
# MAGIC REST API (`POST /api/2.0/knowledge-assistants`) で作成します。
# MAGIC
# MAGIC **前提条件:**
# MAGIC - Vector Search Index が作成済み & ONLINE であること
# MAGIC - エンベディングモデルが `databricks-gte-large-en` であること（KA の制約）

# COMMAND ----------

dbutils.widgets.text("ka_name", "ai_demo_hub_assistant", "KA 名")
dbutils.widgets.text("vs_index", "hiroshi.ai_demo_hub.demos_vs_index", "Vector Search インデックス名")
dbutils.widgets.text("text_col", "all_info_md", "テキスト列")
dbutils.widgets.text("doc_uri_col", "demo_url", "ドキュメント URI 列")
dbutils.widgets.text("description", "社内 AI デモカタログのナレッジアシスタント。デモの検索、製品・技術に関する質問に回答します。", "KA の説明")
dbutils.widgets.text("instructions", "あなたは社内 AI デモカタログのナレッジアシスタントです。ユーザーからの質問に対して、デモカタログを検索し、関連するデモ情報を分かりやすく日本語で回答してください。検索結果がある場合は、デモのタイトル、概要、利用製品、デモURLなどを整理して提示してください。", "KA への指示")

ka_name = dbutils.widgets.get("ka_name")
vs_index = dbutils.widgets.get("vs_index")
text_col = dbutils.widgets.get("text_col")
doc_uri_col = dbutils.widgets.get("doc_uri_col")
ka_description = dbutils.widgets.get("description")
ka_instructions = dbutils.widgets.get("instructions")

# COMMAND ----------

import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.config.host.rstrip("/")
token = w.config.token

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. 既存の KA を検索（同名があれば更新、なければ新規作成）

# COMMAND ----------

# 同名の KA を検索
resp = requests.get(
    f"{host}/api/2.0/tiles",
    headers=headers,
    params={"tile_types": "KA"},
)
resp.raise_for_status()

existing_tile_id = None
for tile in resp.json().get("tiles", []):
    if tile.get("name") == ka_name:
        existing_tile_id = tile["tile_id"]
        print(f"既存の KA を検出: tile_id={existing_tile_id}")
        break

if not existing_tile_id:
    print("既存の KA なし。新規作成します。")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Knowledge Assistant を作成 / 更新

# COMMAND ----------

payload = {
    "name": ka_name,
    "description": ka_description,
    "instructions": ka_instructions,
    "knowledge_sources": [
        {
            "index_source": {
                "name": f"source_{ka_name}",
                "type": "index",
                "description": ka_description,
                "index": {
                    "name": vs_index,
                    "text_col": text_col,
                    "doc_uri_col": doc_uri_col,
                },
            }
        }
    ],
}

if existing_tile_id:
    # 更新
    resp = requests.patch(
        f"{host}/api/2.0/knowledge-assistants/{existing_tile_id}",
        headers=headers,
        json=payload,
    )
else:
    # 新規作成
    resp = requests.post(
        f"{host}/api/2.0/knowledge-assistants",
        headers=headers,
        json=payload,
    )

resp.raise_for_status()
result = resp.json()

ka_info = result.get("knowledge_assistant", result)
tile_id = ka_info.get("id") or ka_info.get("tile", {}).get("tile_id")
endpoint_name = ka_info.get("endpoint_name") or ka_info.get("tile", {}).get("serving_endpoint_name")

print(f"KA 名: {ka_name}")
print(f"Tile ID: {tile_id}")
print(f"エンドポイント名: {endpoint_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. エンドポイントの起動を待機

# COMMAND ----------

import time

for i in range(30):
    resp = requests.get(
        f"{host}/api/2.0/knowledge-assistants/{tile_id}",
        headers=headers,
    )
    resp.raise_for_status()
    ka_status = resp.json()
    tile = ka_status.get("knowledge_assistant", {}).get("tile", {})
    ep_status = tile.get("serving_endpoint_status", "UNKNOWN")

    if ep_status == "ONLINE":
        print(f"エンドポイント {endpoint_name} は ONLINE です。")
        break

    print(f"[{i+1}/30] ステータス: {ep_status} ... 30秒後に再確認")
    time.sleep(30)
else:
    print("タイムアウト: エンドポイントが ONLINE になりませんでした。手動で確認してください。")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. テストクエリ

# COMMAND ----------

test_resp = requests.post(
    f"{host}/serving-endpoints/{endpoint_name}/invocations",
    headers=headers,
    json={
        "input": [{"role": "user", "content": "RAGに関するデモはありますか？"}]
    },
)
test_resp.raise_for_status()
test_result = test_resp.json()

# 回答テキストを抽出
texts = []
for output_item in test_result.get("output", []):
    for content_item in output_item.get("content", []):
        if "text" in content_item:
            texts.append(content_item["text"])

print("Q: RAGに関するデモはありますか？")
print(f"A: {''.join(texts)}")
