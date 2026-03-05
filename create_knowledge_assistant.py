# Databricks notebook source

# COMMAND ----------

# MAGIC %pip install databricks-agents unitycatalog-ai[databricks] mlflow
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "hiroshi", "カタログ名")
dbutils.widgets.text("schema", "ai_demo_hub", "スキーマ名")
dbutils.widgets.text("vs_endpoint", "one-env-shared-endpoint-1", "Vector Search エンドポイント名")
dbutils.widgets.text("vs_index", "hiroshi.ai_demo_hub.demos_vs_index", "Vector Search インデックス名")
dbutils.widgets.text("llm_endpoint", "databricks-claude-sonnet-4", "LLM エンドポイント名")
dbutils.widgets.text("agent_name", "ai_demo_hub_knowledge_assistant", "エージェント名")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
vs_endpoint = dbutils.widgets.get("vs_endpoint")
vs_index = dbutils.widgets.get("vs_index")
llm_endpoint = dbutils.widgets.get("llm_endpoint")
agent_name = dbutils.widgets.get("agent_name")

uc_function_name = f"{catalog}.{schema}.demos_retriever"
registered_model_name = f"{catalog}.{schema}.{agent_name}"

# COMMAND ----------

import mlflow
from databricks.sdk import WorkspaceClient

mlflow.set_registry_uri("databricks-uc")
w = WorkspaceClient()

# COMMAND ----------

# Unity Catalog に Vector Search リトリーバー関数を作成
from unitycatalog.ai.core.utils.function_processing_utils import generate_function_input_params_schema
from databricks.sdk.service.catalog import FunctionInfo

spark.sql(f"""
CREATE OR REPLACE FUNCTION {uc_function_name}(query STRING COMMENT 'ユーザーの検索クエリ')
RETURNS TABLE (
  demo_id BIGINT,
  title STRING,
  summary STRING,
  description_md STRING,
  demo_url STRING,
  repo_url STRING,
  products ARRAY<STRING>,
  status STRING,
  all_info_md STRING,
  score DOUBLE
)
COMMENT 'デモカタログからユーザーのクエリに関連するデモを検索します。製品名、技術、ユースケースなどのキーワードで検索できます。'
RETURN
  SELECT
    demo_id,
    title,
    summary,
    description_md,
    demo_url,
    repo_url,
    products,
    status,
    all_info_md,
    score
  FROM VECTOR_SEARCH(
    index => '{vs_index}',
    query => query,
    num_results => 5
  )
""")

print(f"UC function created: {uc_function_name}")

# COMMAND ----------

# エージェントの定義
from databricks_agents import ChatAgent, ChatAgentMessage, ChatAgentResponse, ChatAgentChunk
from unitycatalog.ai.core.databricks import DatabricksFunctionClient
import json

uc_client = DatabricksFunctionClient()

SYSTEM_PROMPT = """あなたは社内 AI デモカタログのナレッジアシスタントです。
ユーザーからの質問に対して、デモカタログを検索し、関連するデモ情報を分かりやすく日本語で回答してください。

回答のルール:
- 検索結果がある場合は、デモのタイトル、概要、利用製品、デモURLなどを整理して提示してください
- 検索結果がない場合は、その旨を伝え、別のキーワードでの検索を提案してください
- 複数のデモが見つかった場合は、関連度の高い順に紹介してください
- 回答は日本語で行ってください"""

class DemoKnowledgeAssistant(ChatAgent):
    def __init__(self):
        self.llm_endpoint = llm_endpoint
        self.uc_function_name = uc_function_name

    def predict(self, messages, context=None):
        user_query = messages[-1]["content"]

        # Vector Search で関連デモを検索
        try:
            result = uc_client.execute_function(
                self.uc_function_name,
                parameters={"query": user_query}
            )
            search_results = result.to_json() if hasattr(result, 'to_json') else str(result)
        except Exception as e:
            search_results = f"検索エラー: {str(e)}"

        # LLM に検索結果を含めて回答を生成
        augmented_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        # 既存の会話履歴を追加
        for msg in messages[:-1]:
            augmented_messages.append({"role": msg["role"], "content": msg["content"]})

        # ユーザーの質問と検索結果を結合
        augmented_messages.append({
            "role": "user",
            "content": f"""ユーザーの質問: {user_query}

以下はデモカタログの検索結果です:
{search_results}

上記の検索結果をもとに、ユーザーの質問に回答してください。"""
        })

        response = w.serving_endpoints.query(
            name=self.llm_endpoint,
            messages=augmented_messages,
        )

        assistant_message = response.choices[0].message.content

        return ChatAgentResponse(
            messages=[
                ChatAgentMessage(role="assistant", content=assistant_message)
            ]
        )

agent = DemoKnowledgeAssistant()

# COMMAND ----------

# エージェントのテスト
test_result = agent.predict(
    messages=[{"role": "user", "content": "RAGに関するデモはありますか？"}]
)
print(test_result.messages[0].content)

# COMMAND ----------

# MLflow にエージェントをログ & Unity Catalog に登録
mlflow.set_experiment(f"/Users/{w.current_user.me().user_name}/{agent_name}")

input_example = {
    "messages": [{"role": "user", "content": "機械学習に関するデモを教えてください"}]
}

with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=agent,
        input_example=input_example,
        registered_model_name=registered_model_name,
    )

print(f"Model registered: {registered_model_name}")
print(f"Model URI: {model_info.model_uri}")

# COMMAND ----------

# Agent をサービングエンドポイントとしてデプロイ
from databricks.agents import deploy

deployment = deploy(
    model_name=registered_model_name,
    model_version=1,
)

print(f"Agent deployed!")
print(f"Endpoint name: {deployment.endpoint_name}")
print(f"Endpoint URL: {deployment.endpoint_url}")
