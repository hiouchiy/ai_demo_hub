# 🏗️ AI Demo Hub アーキテクチャ

## 📋 概要

AI Demo Hubは、Databricksプラットフォーム上で動作するWebアプリケーションです。社内のAI・MLデモを効率的に管理・共有するための統合システムとして設計されています。

## 🎯 システム構成図

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           👤 ユーザー                                        │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    🌐 フロントエンド層                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  📱 Gradio Web UI                                                          │
│  ├── 4つのタブ (一覧/新規/更新/相談)                                         │
│  ├── 多言語対応 (日本語/英語)                                               │
│  ├── レスポンシブデザイン                                                    │
│  └── リアルタイム更新                                                       │
│                                                                             │
│  🔐 ユーザー認証・識別                                                      │
│  ├── Databricks Apps認証                                                   │
│  ├── ヘッダーベース識別 (x-forwarded-*)                                     │
│  └── 時間帯別挨拶表示                                                       │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     🔧 バックエンド層                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  🐍 Python アプリケーション                                                │
│  ├── app.py (メインアプリケーション)                                        │
│  ├── api_database_manager.py (データベース操作)                             │
│  └── run_app.py (起動管理)                                                  │
│                                                                             │
│  🔑 認証システム                                                            │
│  ├── PAT認証 (ローカル開発用)                                               │
│  ├── OAuth認証 (本番用)                                                     │
│  └── ユーザートークン (データベースアクセス用)                               │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   🗄️ データストレージ層                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  📊 Unity Catalog データベース                                              │
│  ├── テーブル: hiroshi.ai_demo_hub.demos                                    │
│  ├── 15個のフィールド (demo_id, title, summary, etc.)                       │
│  └── データ型: BIGINT, STRING, TIMESTAMP, ARRAY<STRING>                     │
│                                                                             │
│  ⚡ SQL Warehouse                                                           │
│  ├── Databricks SQL Statement REST API                                     │
│  ├── クエリ実行エンジン                                                     │
│  └── パフォーマンス最適化                                                    │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   🤖 AI・ML サービス層                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  🧠 LLM サービス                                                           │
│  ├── Claude-3-7-sonnet (Databricks Serving Endpoints)                     │
│  ├── タイトル自動生成                                                       │
│  ├── 要約自動生成                                                           │
│  └── 文章清書機能                                                           │
│                                                                             │
│  🔍 RAG システム                                                           │
│  ├── Agent Bricks RAGエンドポイント                                         │
│  ├── セマンティック検索                                                     │
│  ├── 会話履歴管理                                                           │
│  └── 自然言語クエリ処理                                                     │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  ☁️ インフラ・デプロイ層                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  🚀 Databricks Apps                                                        │
│  ├── アプリケーションホスティング                                           │
│  ├── 自動スケーリング                                                       │
│  ├── 統合認証                                                               │
│  └── ワークスペース連携                                                     │
│                                                                             │
│  🏢 Databricks Workspace                                                   │
│  ├── 開発環境                                                               │
│  ├── Unity Catalog連携                                                     │
│  └── リソース管理                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔗 コンポーネント詳細

### 1. **🎨 フロントエンド層**

#### **Gradio Web UI**
- **技術**: Gradio 5.37.0
- **特徴**: 
  - タブベースのインターフェース (デモ一覧/新規登録/情報更新/Botに相談)
  - 多言語対応 (日本語/英語切り替え)
  - レスポンシブデザイン
  - リアルタイム更新機能

#### **ユーザー認証・識別**
- **認証方式**: Databricks Apps統合認証
- **ユーザー識別**: ヘッダーベース (`x-forwarded-email`, `x-forwarded-user`)
- **UI機能**: 時間帯別挨拶表示、ユーザー名表示

### 2. **🔧 バックエンド層**

#### **Python アプリケーション**
```
app.py                    # メインアプリケーション (2,400行)
├── UI定義・イベントハンドリング
├── 国際化対応 (TRANSLATIONS)
├── AI機能統合 (RAG, LLM)
└── データベース操作統合

api_database_manager.py   # データベース操作 (540行)
├── SQL Statement REST API
├── CRUD操作
├── 認証トークン管理
└── エラーハンドリング

run_app.py               # 起動管理 (80行)
├── 環境変数チェック
├── 依存関係検証
└── 安全な起動処理
```

#### **認証システム**
- **ローカル開発**: PAT (Personal Access Token)
- **本番環境**: OAuth 2.0 M2M (Machine-to-Machine)
- **データベース**: ユーザートークン (`x-forwarded-access-token`)

### 3. **🗄️ データストレージ層**

#### **Unity Catalog データベース**
```sql
TABLE: hiroshi.ai_demo_hub.demos
├── demo_id (BIGINT, AUTO INCREMENT)     # 主キー
├── title (STRING, NOT NULL)             # デモタイトル
├── summary (STRING)                     # 要約
├── description_md (STRING, NOT NULL)    # 詳細説明 (Markdown)
├── owner_emp_id (STRING, NOT NULL)      # 代表投稿者ID
├── creator_emp_id (STRING)              # デモ作成者ID
├── created_at (TIMESTAMP)               # 作成日時
├── updated_at (TIMESTAMP)               # 更新日時
├── status (STRING, NOT NULL)            # ステータス
├── demo_url (STRING, NOT NULL)          # デモURL
├── repo_url (STRING)                    # リポジトリURL
├── products (ARRAY<STRING>)             # 利用製品
├── confidentiality (STRING)             # 機密性
├── remarks (STRING)                     # 備考
└── all_info_md (STRING)                 # 自動生成情報 (Markdown)
```

#### **SQL Warehouse**
- **API**: Databricks SQL Statement REST API
- **機能**: クエリ実行、パフォーマンス最適化
- **認証**: Bearer Token (適応型認証)

### 4. **🤖 AI・ML サービス層**

#### **LLM サービス (Claude-3-7-sonnet)**
```python
Claude-3-7-sonnet (Databricks Serving Endpoints)
├── タイトル自動生成
│   └── 詳細説明 → キャッチーなタイトル
├── 要約自動生成  
│   └── 詳細説明 → 適切な要約
└── 文章清書機能
    └── ラフなメモ → プロフェッショナルな文章
```

#### **RAG システム (Agent Bricks)**
```python
Agent Bricks RAGエンドポイント
├── セマンティック検索
│   └── 自然言語クエリ → 関連デモ検索
├── 会話履歴管理
│   └── チャット形式の対話継続
├── Markdown応答
│   └── リッチなフォーマット表示
└── URL自動リンク化
    └── レスポンス内URL → クリック可能リンク
```

### 5. **☁️ インフラ・デプロイ層**

#### **Databricks Apps**
```yaml
# databricks.yaml
bundle:
  name: japan-ai-demo-hub

resources:
  apps:
    japan-ai-demo-hub:
      user_api_scopes: [sql]
      resources:
        - sql_warehouse: CAN_USE
```

#### **開発・運用ツール**
- **IDE**: Cursor (AI駆動型開発)
- **Unity Catalog連携**: Databricks MCP
- **パッケージ管理**: uv (高速Python環境)

## 📊 データフロー

### **入力データパス**
```
ユーザー入力 → Gradio UI → Python Backend → SQL Warehouse → Unity Catalog
```

### **出力データパス**  
```
Unity Catalog → SQL Warehouse → Python Backend → Gradio UI → ユーザー表示
```

### **AI処理パス**
```
ユーザークエリ → RAG/LLM Endpoints → AI応答 → Gradio表示
```

## 🔐 認証フロー

### **適応型認証戦略**
```
1. ユーザートークン (x-forwarded-access-token)
   ├── 権限テスト (SQL Warehouse アクセス)
   └── ✅ 成功 → 使用

2. Service Principal トークン (OAuth環境)
   ├── OAuth 2.0 M2M認証
   ├── 権限テスト
   └── ✅ 成功 → 使用

3. システムトークン (PAT環境)
   └── DATABRICKS_TOKEN → 使用
```

## 🚀 デプロイメント

### **本番デプロイ (Databricks Apps)**
```bash
# コード同期
databricks sync --watch . /Workspace/Users/{user}/japan-ai-demo-hub

# アプリデプロイ
databricks apps deploy japan-ai-demo-hub \
  --source-code-path /Workspace/Users/{user}/japan-ai-demo-hub
```

### **ローカル開発**
```bash
# 依存関係インストール
uv install

# 環境変数設定
cp env.example .env

# アプリケーション起動
python run_app.py
```

## 📈 スケーラビリティ・パフォーマンス

### **水平スケーリング**
- **Databricks Apps**: 自動スケーリング対応
- **SQL Warehouse**: 動的リソース割り当て
- **AI Endpoints**: Databricks管理のスケーリング

### **パフォーマンス最適化**
- **データベース**: インデックス最適化、クエリキャッシュ
- **フロントエンド**: 段階的データロード、キャッシュ戦略
- **AI処理**: 非同期処理、応答ストリーミング

## 🛡️ セキュリティ

### **認証・認可**
- **多層認証**: OAuth, PAT, ユーザートークン
- **権限ベース**: SQL Warehouse アクセス制御
- **データ保護**: Unity Catalog統合権限

### **データセキュリティ**
- **機密性管理**: internal/confidential/public分類
- **アクセスログ**: Databricks監査機能
- **暗号化**: transport/rest暗号化

---

## 📚 関連ドキュメント

- **[利用マニュアル](USER_GUIDE.md)** - エンドユーザー向け操作説明
- **[開発者ガイド](README.md)** - 開発環境構築・デプロイ手順
- **[データベーススキーマ](Create%20Table.ipynb)** - テーブル作成手順

---

*このアーキテクチャドキュメントは、AI Demo Hub v1.1 に基づいています。*