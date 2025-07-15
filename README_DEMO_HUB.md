# AI Demo Hub - Gradio Web Application

総合的なAIデモメタデータ管理システムです。Databricksのテーブルに保存されたデモ情報を管理し、RAGシステムとの統合により高度な検索機能を提供します。

## 新機能（Latest Update）

### ⚙️ 環境変数設定の強化
- **データベース接続設定**を環境変数から設定可能に
- 必須変数：`DATABRICKS_TOKEN`、`RAG_ENDPOINT`
- オプション変数：`DATABRICKS_SERVER_HOSTNAME`、`DATABRICKS_WAREHOUSE_ID`
- `env.example`ファイルで設定例と手順を提供
- 既存の設定を壊すことなく、デフォルト値で動作

### 🔧 製品配列表示の修正
- **問題**: 更新フォームで製品名が `[, ", M, L, F, l, o, w, ", ]` のように文字ごとに分割されて表示
- **原因**: API から取得した文字列データが `join()` 関数で文字列として扱われていた
- **解決**: 製品配列処理の強化により、JSON配列、単一文字列、リスト、空値に対応
- **対象**: `get_demo_by_id`、`get_demos`、`search_demo_for_update` 関数

### 📊 プログレス表示機能
- **全操作**にリアルタイムプログレス表示を追加
- 新規登録、更新、削除の各処理でプログレスバーを表示
- 処理段階：入力検証 → データ処理 → データベース操作 → 完了
- ユーザーフィードバックの向上により、処理中の状況が明確に

### 🔄 拡張フィールドクリア機能
- **新規登録**：成功時に全フィールドを自動クリア
- **更新処理**：成功時に全フィールドを自動クリア（NEW）
- **削除処理**：成功時に全フィールドを自動クリア（NEW）
- エラー時はフィールド値を保持し、修正を容易に

### 🗑️ デモ削除機能
- **更新タブ**に削除ボタンを追加
- 既存のデモを安全に削除できます
- 削除前に確認チェックが実行されます
- エラーハンドリングにより、存在しないデモの削除を防止

## 機能概要

### 1. 📊 デモ一覧
- ページネーション機能（20件/ページ）
- ソート機能（全カラム対応）
- タイトルクリックで詳細表示
- JST表示対応
- **✅ 製品配列の正しい表示**

### 2. ✨ 新規登録
- 必須フィールドバリデーション
- メールアドレス形式チェック
- 製品名のカンマ区切り入力
- **📊 リアルタイムプログレス表示**
- **✅ 登録成功後の自動フィールドクリア**

### 3. ✏️ 情報更新
- ID検索による既存デモの取得
- 全フィールドの更新対応
- **✅ 製品配列の正しい表示**（文字分割問題解決）
- **📊 更新処理のプログレス表示**
- **✅ 更新成功後の自動フィールドクリア**
- **🗑️ デモ削除機能**
- **📊 削除処理のプログレス表示**
- **✅ 削除成功後の自動フィールドクリア**
- 更新・削除ボタンの並列配置

### 4. 🤖 セマンティック検索
- RAGシステムとの統合
- 会話履歴の保持
- 自然言語でのデモ検索

## 環境設定

### 🌟 新しい環境変数設定方法

#### 1. 設定ファイルの作成
```bash
# 例示ファイルをコピー
cp env.example .env

# 設定ファイルを編集
nano .env
```

#### 2. 必須環境変数
```bash
# Databricksアクセストークン（必須）
DATABRICKS_TOKEN=your_actual_token_here

# RAGシステムエンドポイント（必須）
RAG_ENDPOINT=your_actual_endpoint_here
```

#### 3. オプション環境変数（デフォルト値あり）
```bash
# Databricksサーバーホスト名（オプション）
DATABRICKS_SERVER_HOSTNAME=adb-984752964297111.11.azuredatabricks.net

# Databricksワークスペース ID（オプション）
DATABRICKS_WAREHOUSE_ID=148ccb90800933a1
```

#### 4. アプリケーション起動
```bash
# 方法1: 直接起動
python app.py

# 方法2: 拡張スクリプトで起動
./start_app.sh

# 方法3: Python スクリプトで起動
python run_app.py
```

### 従来の設定方法（まだ使用可能）
```bash
# 必要な環境変数を手動で設定
export DATABRICKS_TOKEN=your_token_here
export RAG_ENDPOINT=your_rag_endpoint_here

# オプション設定
export DATABRICKS_SERVER_HOSTNAME=your_server_hostname
export DATABRICKS_WAREHOUSE_ID=your_warehouse_id

# アプリケーション起動
python app.py
```

## 技術仕様

### 環境変数の設定
- **必須変数**: `DATABRICKS_TOKEN`, `RAG_ENDPOINT`
- **オプション変数**: `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_WAREHOUSE_ID`
- **デフォルト値**: 既存の設定値を使用し、後方互換性を保持
- **設定ファイル**: `.env`ファイルサポート（`python-dotenv`使用）

### 製品配列の処理
- **問題解決**: 文字列の文字分割問題を修正
- **対応形式**: JSON配列文字列、単一文字列、リスト、空値
- **処理ロジック**: 型チェックとJSON解析により適切な変換
- **表示形式**: カンマ区切りの読みやすい文字列

### プログレス表示
- **実装**: Gradio `gr.Progress()` を使用
- **段階**: 入力検証 → データ処理 → データベース操作 → 完了
- **フィードバック**: 各段階でのステータスメッセージ表示
- **UI**: ボタンクリック時に自動的にプログレスバーを表示

### フィールドクリア機能
- **成功時**: 全フィールドを空文字列に、ドロップダウンはデフォルト値に
- **エラー時**: 元の値を保持し、修正を容易に
- **戻り値**: 関数がタプルで複数値を返却し、UIに反映

### データベース接続
- **APIベース**: Databricks REST API使用
- **認証**: Bearer Token認証
- **エラーハンドリング**: 包括的なエラー処理
- **セキュリティ**: SQLインジェクション対策
- **設定**: 環境変数による柔軟な設定

## 使用方法

### 環境設定の確認
```bash
# 環境変数のテスト
python test/test_env_variables.py
```

### 製品配列の表示確認
1. **情報更新**タブで任意のデモを検索
2. 製品フィールドに製品名が正しく表示されることを確認
3. 例：`MLflow, Databricks, Delta Lake` のような形式

### プログレス表示の確認
1. 各操作（登録、更新、削除）を実行
2. 処理中にプログレスバーとステータスメッセージを確認
3. 完了時に結果メッセージを確認

### 削除機能の使用
1. **情報更新**タブを選択
2. **Demo ID**を入力して**検索**ボタンをクリック
3. デモ情報が表示されたら**削除**ボタンをクリック
4. プログレス表示を確認し、完了後に全フィールドがクリア

### 自動フィールドクリア
1. **新規登録**、**更新**、**削除**の各操作を実行
2. 成功時に全フィールドが自動的にクリア
3. エラー時は入力値が保持される

## 環境変数設定の詳細

### 設定ファイル例（env.example）
```bash
# 必須設定
DATABRICKS_TOKEN=your_databricks_token_here
RAG_ENDPOINT=your_rag_endpoint_here

# オプション設定（デフォルト値あり）
DATABRICKS_SERVER_HOSTNAME=adb-984752964297111.11.azuredatabricks.net
DATABRICKS_WAREHOUSE_ID=148ccb90800933a1
```

### 設定手順
1. **ファイルコピー**: `cp env.example .env`
2. **編集**: `nano .env`
3. **設定**: 実際の値に置き換え
4. **起動**: `python app.py`

### 設定の検証
```bash
# 設定確認スクリプト
python test/test_env_variables.py
```

## 製品配列処理の詳細

### 問題の例
```
# 修正前（問題のある表示）
Input: "MLflow"
Output: [, ", M, L, F, l, o, w, ", ]

# 修正後（正しい表示）
Input: "MLflow"
Output: MLflow
```

### 対応する入力形式
1. **JSON配列文字列**: `'["MLflow", "Databricks"]'` → `["MLflow", "Databricks"]`
2. **単一文字列**: `"MLflow"` → `["MLflow"]`
3. **既存のリスト**: `["MLflow", "Databricks"]` → `["MLflow", "Databricks"]`
4. **空値**: `""` または `null` → `[]`

### 実装例
```python
def process_products(products_value):
    if products_value:
        if isinstance(products_value, list):
            return products_value
        elif isinstance(products_value, str):
            if products_value.startswith('[') and products_value.endswith(']'):
                return json.loads(products_value)
            else:
                return [products_value]
    return []
```

## プログレス表示の詳細

### 処理段階
1. **入力検証 (10%)**: フォームデータの検証
2. **データ処理 (30%)**: ID処理、製品リスト処理
3. **データ準備 (50%)**: データベース用データの準備
4. **データベース操作 (80%)**: 実際のCRUD操作
5. **完了 (100%)**: 処理完了、結果表示

### 実装例
```python
def update_demo(..., progress=gr.Progress()):
    progress(0.1, desc="Validating input...")
    # 入力検証
    progress(0.3, desc="Processing demo ID...")
    # ID処理
    progress(0.5, desc="Preparing data...")
    # データ準備
    progress(0.8, desc="Updating demo...")
    # DB操作
    progress(1.0, desc="Update completed!")
    # 完了
```

## セキュリティ考慮事項

### 環境変数管理
- **機密情報**: `.env`ファイルは`.gitignore`に追加
- **セキュリティ**: 環境変数による認証情報の安全な管理
- **デフォルト値**: 機密情報以外のデフォルト値を提供

### 削除機能
- 削除前の存在確認
- 適切なエラーメッセージ
- 不正な入力値の検証

### プログレス表示
- 機密情報の非表示
- 適切なステータスメッセージ
- エラー情報の安全な処理

### API接続
- SQL インジェクション対策
- 認証トークンの適切な管理
- エラー情報の適切な処理

## トラブルシューティング

### 環境変数関連
- **問題**: 環境変数が読み込まれない
- **解決**: `.env`ファイルの存在確認、`python test/test_env_variables.py`でテスト
- **確認**: 設定値が正しく反映されているか確認

### 製品配列表示関連
- **問題**: 製品名が文字ごとに分割されて表示
- **解決**: 最新版では修正済み（製品配列処理の強化）
- **確認**: 更新フォームで製品名が正しく表示されることを確認

### プログレス表示関連
- プログレスバーが表示されない場合：ブラウザの再読み込み
- プログレスが途中で止まる場合：エラーログを確認

### 削除機能関連
- **Error: Please search for a demo first**: 先にデモを検索してください
- **Error: Demo not found**: 指定されたIDのデモが存在しません
- **Error: Invalid demo ID format**: 有効な数値のIDを入力してください

### フィールドクリア関連
- フィールドクリアが動作しない場合：ブラウザの再読み込み
- 部分的なクリアが発生する場合：エラーログを確認

## 技術サポート

より詳細な情報については、以下のファイルを参照してください：
- `CHANGELOG.md`: 変更履歴
- `TROUBLESHOOTING.md`: トラブルシューティング
- `api_database_manager.py`: API実装詳細
- `test/test_progress_features.py`: 新機能テストスクリプト
- `test/test_products_fix.py`: 製品配列処理テストスクリプト
- `test/test_env_variables.py`: 環境変数設定テストスクリプト
- `env.example`: 環境変数設定例

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。 