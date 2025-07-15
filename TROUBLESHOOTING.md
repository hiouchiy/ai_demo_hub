# 🔧 トラブルシューティングガイド

## よくある問題と解決方法

### 1. "Database error: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'"

**原因**: データベースから取得したデータにNone値が含まれている

**修正済み**: 
- `get_demos()`メソッドでNone値のチェック追加
- `load_demo_list()`関数で安全なデータ処理
- すべてのデータベース操作でNone値チェック

**対処法**:
```python
# 修正前
demo_id = demo["demo_id"]  # None値でエラー

# 修正後
demo_id = demo.get("demo_id") or 0  # 安全に処理
```

### 1.5. "Database error: cannot cast STRING to ARRAY"

**原因**: DatabricksでのArray型データの不正な処理

**修正済み**: 
- `insert_demo()`と`update_demo()`でArray型の正しい処理
- 配列リテラルを直接SQLクエリに埋め込む方式に変更
- 空配列の安全な処理

**対処法**:
```python
# 修正前
products_array = f"array({', '.join([f\"'{p.strip()}\"\" for p in data['products']])})"

# 修正後
products_list = [p.strip() for p in data['products'] if p.strip()]
products_array_str = ', '.join([f"'{p}'" for p in products_list])
query = f"INSERT INTO ... VALUES (..., array({products_array_str}), ...)"
```

### 2. Gradioの起動エラー

**原因**: バージョン互換性問題、localhost接続問題

**修正済み**:
- Gradio 5.37.0へアップグレード
- `share=True`で共有URL生成
- フォールバック起動設定

### 3. 環境変数未設定エラー

**症状**: "Environment variable not set"

**対処法**:
```bash
export DATABRICKS_TOKEN="your_actual_token"
export RAG_ENDPOINT="your_actual_endpoint"
```

### 4. データベース接続エラー

**テスト方法**:
```bash
python test/test_db.py
```

**対処法**:
- DATABRICKS_TOKENが有効か確認
- ネットワーク接続を確認
- Databricksワークスペースのアクセス権限を確認

### 5. 空のデモリスト

**原因**: テーブルにデータがない、または権限不足

**対処法**:
- テーブルの存在確認
- データの有無確認
- 権限設定確認

### 6. ポップアップエラー

**症状**: "Invalid demo ID format"

**対処法**:
- 有効なDemo IDを入力
- 数値のみ入力可能

## 起動時のエラーハンドリング

### 改善された機能
- None値の安全な処理
- エラーメッセージの詳細化
- フォールバック機能
- 入力値検証

### デバッグ方法

1. **環境変数確認**:
   ```bash
   python test/test_db.py
   ```

2. **データベース直接テスト**:
   ```python
   from app import DatabaseManager
   db = DatabaseManager()
   db.test_connection()
   ```

3. **ログ確認**:
   - コンソール出力を確認
   - エラーメッセージを確認

## 推奨起動手順

1. **環境変数設定**:
   ```bash
   export DATABRICKS_TOKEN="your_token"
   export RAG_ENDPOINT="your_endpoint"
   ```

2. **依存関係確認**:
   ```bash
   uv pip install -r requirements.txt
   ```

3. **アプリケーション起動**:
   ```bash
   source .venv/bin/activate
   python run_app.py
   ```

## サポート

問題が解決しない場合は、以下の情報を含めてお問い合わせください：

- エラーメッセージ全体
- 実行したコマンド
- 環境設定情報
- `python test/test_db.py`の結果 