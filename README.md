# 🚀 AI Demo Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/Gradio-5.37.0-orange.svg)](https://gradio.app/)

社内で開発されたAIデモアプリケーションを効率的に共有・管理するためのWebアプリケーションです。

> 📚 **[利用マニュアル](USER_GUIDE.md)** 

## ✨ 概要

AI Demo Hubは、Databricks環境で動作するGradioベースのWebアプリケーションです。社内のAI・MLプロジェクトのデモを一元管理し、チーム間での知識共有を促進します。

### 🎯 主要機能

- **📋 デモ一覧表示**: 登録されたデモの検索・閲覧
- **➕ 新規デモ登録**: AI自動生成機能付きの簡単登録
- **✏️ デモ情報管理**: 既存デモの編集・削除
- **🤖 セマンティック検索**: RAGシステムによる自然言語検索
- **👥 ユーザー管理**: 作成者・投稿者の自動識別
- **🔒 アクセス制御**: 社内認証システムとの連携

## 🛠️ 技術スタック

### 開発環境
- **[Cursor](https://cursor.sh/)** - AI駆動型統合開発環境
- **[Databricks MCP](https://docs.databricks.com/en/dev-tools/mcp/index.html)** - Unity Catalog連携機能
- **[uv](https://github.com/astral-sh/uv)** - 高速Pythonパッケージマネージャー

### フロントエンド
- **[Gradio 5.37.0](https://gradio.app/)** - Web UI フレームワーク
- **Markdown** - コンテンツレンダリング
- **Pandas** - データ表示

### バックエンド
- **Python 3.10+** - メインプログラミング言語
- **Databricks SQL Statement REST API** - データベース接続
- **Databricks SDK** - LLM統合 (Claude-3-7-sonnet)
- **OpenAI ChatCompletion** - RAGシステム連携

### インフラ
- **Databricks Apps** - アプリケーションホスティング
- **Unity Catalog** - データガバナンス
- **SQL Warehouse** - データ処理エンジン

## 🚀 Getting Started

### 前提条件

- Python 3.10以上
- [uv](https://github.com/astral-sh/uv) パッケージマネージャー
- [Cursor](https://cursor.sh/) - 開発環境（推奨）
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) - デプロイ用
- Databricksワークスペースへのアクセス
- Unity Catalogの有効化

### 1. リポジトリのクローン

```bash
git clone https://github.com/hiouchiy/ai_demo_hub.git
cd ai_demo_hub
```

### 2. 開発環境の設定

#### Cursorエディターの設定

Cursor（推奨開発環境）でDatabricks MCP機能を使用するために、以下の設定を行います：

1. Cursorのワークスペース設定ファイル（`.cursor/mcp.json`）を作成：

```json
{
  "mcpServers": {
    "uc-function-mcp": {
      "type": "streamable-http",
      "url": "https://YOUR_WORKSPACE.azuredatabricks.net/api/2.0/mcp/functions/CATALOG/SCHEMA",
      "headers": {
        "Authorization": "Bearer DATABRICKS_TOKEN"
      },
      "note": "Databricks UC function for searching delta tables in the Databricks workspace"
    }
  }
}
```

> ⚠️ `YOUR_WORKSPACE`を実際のワークスペース名に、`DATABRICKS_TOKEN`を実際のトークンに置き換えてください。

### 3. uvパッケージマネージャーのインストール

#### Mac OSの場合

```bash
# Homebrewを使用（推奨）
brew install uv

# または、curl（Homebrewがない場合）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### その他のOS

```bash
# pip経由でのインストール
pip install uv

# または、curl（Linux/macOS）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### インストール確認

```bash
uv --version
```

### 4. 依存関係のインストール

```bash
# uvを使用してパッケージをインストール
uv pip install -r requirements.txt
```

### 5. 環境変数の設定

`.env`ファイルを作成し、以下の環境変数を設定：

```bash
# .envファイルをenv.exampleからコピー
cp env.example .env
```

`.env`ファイルを編集：

```env
# Databricks接続情報
DATABRICKS_HOST=your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-databricks-token
DATABRICKS_WAREHOUSE_ID=your-warehouse-id

# RAGエンドポイント
RAG_ENDPOINT=https://your-workspace.cloud.databricks.com/serving-endpoints/YOUR_RAG_ENDPOINT_NAME/invocations
```

### 6. データベースの準備

Unity Catalogに以下のテーブルを作成：

```sql
CREATE TABLE hiroshi.ai_demo_hub.demos (
    demo_id BIGINT GENERATED ALWAYS AS IDENTITY,
    title STRING NOT NULL,
    summary STRING,
    description_md STRING NOT NULL,
    owner_emp_id STRING NOT NULL,
    creator_emp_id STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    status STRING NOT NULL,
    demo_url STRING NOT NULL,
    repo_url STRING,
    products ARRAY<STRING>,
    confidentiality STRING,
    remarks STRING,
    all_info_md STRING
);
```

> 📝 **詳細な手順**: [Create Table.ipynb](Create%20Table.ipynb)を参照

### 7. アプリケーションの起動

#### 開発環境での起動

```bash
DATABRICKS_TOKEN=YOUR_TOKEN RAG_ENDPOINT=https://YOUR_HOST/serving-endpoints/YOUR_ENDPOINT_NAME/invocations DATABRICKS_WAREHOUSE_ID=YOUR_DW_ID DATABRICKS_HOST=YOUR_HOST python app.py
```

### 8. アクセス

ブラウザで http://localhost:7860 にアクセスしてアプリケーションを利用できます。

## 📊 データベーススキーマ

### `hiroshi.ai_demo_hub.demos` テーブル

| 列名 | 型 | 説明 |
|------|----|----|
| `demo_id` | BIGINT | 自動生成される一意識別子 |
| `title` | STRING | デモのタイトル（必須） |
| `summary` | STRING | デモの要約 |
| `description_md` | STRING | 詳細説明（Markdown対応、必須） |
| `owner_emp_id` | STRING | 代表投稿者のメールアドレス（必須） |
| `creator_emp_id` | STRING | デモ作成者のメールアドレス |
| `created_at` | TIMESTAMP | 作成日時（自動設定） |
| `updated_at` | TIMESTAMP | 更新日時（自動設定） |
| `status` | STRING | ステータス（draft/published/archived） |
| `demo_url` | STRING | デモのURL（必須） |
| `repo_url` | STRING | リポジトリのURL |
| `products` | ARRAY<STRING> | 利用Databricks製品 |
| `confidentiality` | STRING | 機密性（internal/confidential/public） |
| `remarks` | STRING | 備考 |
| `all_info_md` | STRING | 自動生成される全情報（Markdown） |

## 🔧 設定

### 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `DATABRICKS_HOST` | ✅ | DatabricksワークスペースのURL |
| `DATABRICKS_TOKEN` | ✅ | Personal Access Token |
| `DATABRICKS_WAREHOUSE_ID` | ✅ | SQLウェアハウスのID |
| `RAG_ENDPOINT` | ✅ | セマンティック検索用RAGエンドポイント |

### 認証

アプリケーションは以下のヘッダーから現在のユーザー情報を取得します：

- `x-forwarded-email`
- `x-forwarded-user` 
- `x-forwarded-preferred-username`

ローカル開発時は `unknown@databricks.com` がデフォルト値として使用されます。

## 🎨 AI機能

### タイトル・要約自動生成

Databricks Claude-3-7-sonnetモデルを使用して：
- **タイトル生成**: 詳細説明からキャッチーなタイトルを自動生成
- **要約生成**: 詳細説明から適切な要約を自動生成
- **文章清書**: ラフなメモをプロフェッショナルな文章に変換

### セマンティック検索

RAGシステムと連携して：
- 自然言語での検索が可能
- 会話履歴を保持した対話形式
- Markdown形式での結果表示
- URL自動リンク化

## 📁 プロジェクト構造

```
ai_demo_hub/
├── app.py                    # メインアプリケーション
├── api_database_manager.py   # データベース操作
├── run_app.py               # 本番起動スクリプト
├── start_app.sh             # シェルスクリプト
├── requirements.txt         # Python依存関係
├── env.example             # 環境変数テンプレート
├── USER_GUIDE.md           # 利用者向けマニュアル
├── Create Table.ipynb      # データベースセットアップ
└── test/                   # テストスクリプト
    ├── debug_db.py
    ├── query_test.py
    └── ...
```

## 🚢 デプロイメント

### Databricks Appsへのデプロイ

本番環境では**Databricks Apps**を使用してデプロイします。

#### 1. Databricks CLIのセットアップ

```bash
# Databricks CLIのインストール（pipx推奨）
pipx install databricks-cli

# または pip
pip install databricks-cli

# 認証設定
databricks configure --token
```

#### 2. コードの同期

```bash
# ワークスペースにコードを同期（ウォッチモード）
databricks sync --watch . /Workspace/Users/hiroshi.ouchiyama@databricks.com/japan-ai-demo-hub
```

> 💡 `--watch`オプションにより、ローカルファイルの変更が自動的にワークスペースに同期されます。

#### 3. アプリのデプロイ

```bash
# Databricks Appsとしてデプロイ
databricks apps deploy japan-ai-demo-hub --source-code-path /Workspace/Users/hiroshi.ouchiyama@databricks.com/japan-ai-demo-hub
```

#### 4. 環境変数の設定

Databricksワークスペースで以下の環境変数をSecretとして設定：

1. **Databricks Secrets CLIを使用:**
```bash
# Secretスコープを作成
databricks secrets create-scope ai-demo-hub

# 各環境変数をSecretとして登録
databricks secrets put-secret ai-demo-hub DATABRICKS_TOKEN
databricks secrets put-secret ai-demo-hub RAG_ENDPOINT
databricks secrets put-secret ai-demo-hub DATABRICKS_SERVER_HOSTNAME
databricks secrets put-secret ai-demo-hub DATABRICKS_WAREHOUSE_ID
```

2. **アプリ設定ファイル（app.yaml）で参照:**
```yaml
# app.yamlの例
env:
  - name: DATABRICKS_TOKEN
    valueFrom:
      secretKeyRef:
        scope: ai-demo-hub
        key: DATABRICKS_TOKEN
  - name: RAG_ENDPOINT
    valueFrom:
      secretKeyRef:
        scope: ai-demo-hub
        key: RAG_ENDPOINT
```

#### 5. アプリの管理

```bash
# アプリ一覧表示
databricks apps list

# アプリ詳細確認
databricks apps describe japan-ai-demo-hub

# アプリ停止
databricks apps stop japan-ai-demo-hub

# アプリ削除
databricks apps delete japan-ai-demo-hub
```

## 🤝 開発への貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 🆕 更新履歴

詳細な変更履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。

## 🙋 サポート・問い合わせ

- **Issues**: GitHub Issues でバグ報告や機能要求を受け付けています
- **Wiki**: 詳細なドキュメントは Wiki を参照
- **Discussions**: 質問や議論は Discussions をご利用ください

## 📄 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

```
MIT License

Copyright (c) 2025 AI Demo Hub Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

⭐ このプロジェクトが役に立ったら、スターをつけていただけると嬉しいです！