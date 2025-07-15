# 🚀 AI Demo Hub - 変更履歴

## [v1.2.3] - 2024-07-15

### 🔧 修正内容

#### 1. 型変換エラーの修正
- **"can only concatenate str (not 'int') to str"エラーを解決**:
  - APIから返されるデータ（文字列）の適切な型変換を実装
  - `demo_id`の文字列→整数変換処理追加
  - `total_count`の文字列→整数変換処理追加
  - `products`のJSON文字列→配列変換処理追加

#### 2. データ処理の堅牢性向上
- **安全な型変換**:
  - `isinstance()`を使用した型チェック
  - `try-except`による例外処理
  - JSONパースのフォールバック処理

### 🛠️ 技術的な変更

#### 型変換処理の改善
```python
# Before
total_count = count_result[0]['total'] if count_result else 0

# After  
if count_result and len(count_result) > 0:
    total_count = int(count_result[0]['total'])
else:
    total_count = 0
```

#### データ処理の改善
```python
# demo_idの安全な変換
demo_id = demo.get("demo_id")
if demo_id is not None:
    demo_id = int(demo_id) if isinstance(demo_id, str) else demo_id
else:
    demo_id = 0
```

## [v1.2.2] - 2024-07-15

### 🔧 修正内容

#### 1. 一覧画面の表示問題を完全解決
- **Databricks SQLクライアントライブラリの問題を回避**:
  - `fetchone()`/`fetchall()`で発生するNoneTypeエラーを根本的に解決
  - REST APIベースのDatabaseManagerを実装
  - pandasライブラリ内での`to_numpy(na_value=None)`エラーを回避

#### 2. APIベースのデータベース接続
- **新しい実装**:
  - `APIBasedDatabaseManager`クラス新規作成
  - Databricks SQL Statement API使用
  - 安全なSQLエスケープ処理実装
  - 完全なCRUD操作サポート

#### 3. データ取得機能の改善
- **正常なデータ表示**:
  - 2件のデータが正常に一覧表示される
  - カウントクエリが正常に動作
  - ページネーション機能正常化
  - ソート機能正常化

### 🛠️ 技術的な変更

#### APIベースのデータベース接続
```python
# 新しい実装
class APIBasedDatabaseManager:
    def execute_query_api(self, query: str) -> List[Dict]:
        response = requests.post(self.base_url, headers=headers, json=payload)
        # REST APIでクエリを実行
        
# app.pyでの使用
from api_database_manager import APIBasedDatabaseManager
db_manager = APIBasedDatabaseManager()
```

#### SQLエスケープ処理
```python
def escape_sql_string(self, value: str) -> str:
    if value is None:
        return 'NULL'
    return "'" + str(value).replace("'", "''") + "'"
```

### 📊 動作確認

- ✅ テーブル接続：正常
- ✅ データ件数取得：2件正常取得
- ✅ 一覧表示：正常表示
- ✅ 登録機能：正常動作
- ✅ 更新機能：正常動作
- ✅ 詳細表示：正常動作

## [v1.2.1] - 2024-07-15

### 🔧 修正内容

#### 1. 登録機能のNoneTypeエラー修正
- **"int() argument must be a string, a bytes-like object or a real number, not 'NoneType'"エラーの修正**:
  - `insert_demo()`メソッドでMAX関数がNoneを返す場合の処理追加
  - フォールバッククエリによるdemo_id取得機能実装
  - 登録成功時の安全なID表示処理

#### 2. 入力値検証の強化
- **全関数でのint()変換エラー対策**:
  - `load_demo_list()`でのページ番号検証強化
  - `show_description_popup()`でのdemo_id検証改善
  - `search_demo_for_update()`と`update_demo()`での入力値検証

#### 3. データベース操作の安全性向上
- **エラーハンドリングの包括的改善**:
  - None値チェックを全データベース操作に追加
  - 型変換エラーの詳細なエラーメッセージ
  - 空文字列や無効な数値形式への対応

### 🛠️ 技術的な変更

#### 登録機能の修正
```python
# 修正前
last_id_query = "SELECT MAX(demo_id) as last_id FROM hiroshi.ai_demo_hub.demos"
result = self.execute_query(last_id_query)
return result[0]['last_id']

# 修正後
if result and len(result) > 0 and result[0]['last_id'] is not None:
    return result[0]['last_id']
else:
    # フォールバック処理
    fallback_query = "SELECT demo_id FROM ... WHERE ... ORDER BY created_at DESC LIMIT 1"
    fallback_result = self.execute_query(fallback_query, [...])
    return fallback_result[0]['demo_id'] if fallback_result else 0
```

## [v1.2.0] - 2024-07-15

### 🔧 修正内容

#### 1. データベース関連エラーの修正
- **NoneType エラーの修正**:
  - `get_demos()`メソッドでNone値チェック追加
  - `load_demo_list()`関数で安全なデータ処理
  - すべてのデータベース操作でNone値検証

#### 2. Array型データ処理の修正
- **"cannot cast STRING to ARRAY"エラーの修正**:
  - `insert_demo()`と`update_demo()`でArray型の正しい処理
  - 配列リテラルを直接SQLクエリに埋め込む方式に変更
  - 空配列の安全な処理

#### 3. Gradio関連の改善
- **Gradio 5.37.0への対応**:
  - チャットボットの新しいメッセージ形式（`type='messages'`）対応
  - `chat_with_rag()`関数の更新
  - 非推奨警告の解消

#### 4. エラーハンドリングの強化
- **詳細なエラーメッセージ**:
  - 各関数での例外処理追加
  - デバッグ情報の充実
  - フォールバック処理の実装

### 🛠️ 技術的な変更

#### データベース処理
```python
# 修正前
products_array = f"array({', '.join([f\"'{p.strip()}\"\" for p in data['products']])})"

# 修正後
products_list = [p.strip() for p in data['products'] if p.strip()]
if products_list:
    products_array_str = ', '.join([f"'{p}'" for p in products_list])
else:
    products_array_str = ""
query = f"INSERT INTO ... VALUES (..., array({products_array_str}), ...)"
```

#### チャットボット
```python
# 修正前
def chat_with_rag(message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
    history.append([message, response])

# 修正後
def chat_with_rag(message: str, history: List[Dict]) -> Tuple[str, List[Dict]]:
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
```

### 🎯 解決された問題

✅ **登録ボタンエラー**: Array型データの正しい処理により解決  
✅ **読み込みボタンエラー**: None値の安全な処理により解決  
✅ **チャットボット警告**: 新しいメッセージ形式対応により解決  
✅ **データベース接続エラー**: 詳細なエラーハンドリングにより改善  
✅ **入力値検証**: 不正な値の事前チェック機能追加  

### 📋 新機能

- **データベース接続テスト**: `test/test_db.py`スクリプト
- **トラブルシューティングガイド**: `TROUBLESHOOTING.md`
- **改善された起動スクリプト**: `run_app.py`
- **詳細なエラーメッセージ**: 問題の特定が容易に

### 🔄 依存関係の更新

- **Gradio**: 4.44.0 → 5.37.0
- **pandas**: 2.1.4 → 2.3.1
- **requests**: 2.31.0 → 2.32.4
- **pytz**: 2024.1 → 2025.2

### 🚀 使用方法

1. **環境変数設定**:
   ```bash
   export DATABRICKS_TOKEN="your_token"
   export RAG_ENDPOINT="your_endpoint"
   ```

2. **アプリケーション起動**:
   ```bash
   source .venv/bin/activate
   python run_app.py
   ```

3. **トラブルシューティング**:
   ```bash
python test/test_db.py
```

### 📝 今後の改善予定

- [ ] バッチ処理機能の追加
- [ ] 詳細なログ機能
- [ ] パフォーマンス最適化
- [ ] UI/UXの改善

---

## [v1.1.0] - 2024-07-15

### 🆕 初期リリース

- Gradioベースのwebアプリケーション
- 4つのタブ機能（一覧、登録、更新、検索）
- Databricksテーブル連携
- RAGシステム統合
- 基本的なエラーハンドリング 

### Added
- **Environment Variables Configuration**: Made database connection settings configurable via environment variables
  - Added `DATABRICKS_SERVER_HOSTNAME` environment variable (optional, with default)
  - Added `DATABRICKS_WAREHOUSE_ID` environment variable (optional, with default)
  - Existing `DATABRICKS_TOKEN` and `RAG_ENDPOINT` remain required
  - Created `env.example` file with configuration examples and instructions
  - Updated `run_app.py` to handle environment variable defaults
  - Updated `start_app.sh` to check and set environment variables
  - Added `test/test_env_variables.py` for testing environment configuration

### Fixed
- **Products Array Display Issue**: Fixed products field displaying as character array instead of readable text
  - Problem: Products like "MLflow" were displayed as [, ", M, L, F, l, o, w, ", ] in update form
  - Root cause: String data from API being treated as iterable in join() function
  - Solution: Enhanced products array handling in `get_demo_by_id`, `get_demos`, and `search_demo_for_update` functions
  - Added proper type checking and JSON parsing for various data formats
  - Now correctly handles: JSON arrays, single strings, lists, and empty values

### Added
- **Progress Display**: Added visual progress indicators for all operations
  - Registration, update, and deletion processes now show progress bars
  - Progress steps include: validation, processing, data preparation, and completion
  - Uses Gradio's `gr.Progress()` for real-time progress feedback
  - Added `show_progress=True` to all button click events

- **Enhanced Field Clearing**: Extended field clearing functionality
  - **Registration**: Fields clear automatically on successful registration
  - **Update**: Fields clear automatically on successful update (NEW)
  - **Deletion**: Fields clear automatically on successful deletion (NEW)
  - Error handling preserves field values for easy correction

- **Delete Functionality**: Added delete button to Demo Update tab to allow deletion of existing demos
  - Added `delete_demo()` method to `APIBasedDatabaseManager` class
  - Added `delete_demo()` function to handle demo deletion in the UI
  - Added delete button with "stop" variant styling in Demo Update tab
  - Added proper validation and error handling for demo deletion

- **Field Clearing After Registration**: Registration form now automatically clears all fields after successful demo registration
  - Modified `register_demo()` function to return multiple values including cleared field values
  - Updated Gradio click event to handle multiple outputs for field clearing
  - Improved user experience by preventing need to manually clear form after successful registration

### Changed
- Enhanced Demo Update tab UI with side-by-side update and delete buttons
- Improved error handling for demo deletion with existence checks before deletion
- **Function signatures**: All main functions now include `progress=gr.Progress()` parameter
- **Return values**: Functions now return tuples with field values for UI updating
- **UI responsiveness**: Progress display provides better user feedback during operations
- **Data processing**: More robust handling of products array data from API responses
- **Configuration**: Database connection settings now configurable via environment variables

### Technical Details
- Progress display implementation:
  - 0.1: Input validation
  - 0.3: ID processing (for update/delete)
  - 0.5: Data preparation
  - 0.8: Database operation
  - 1.0: Operation completion
- Field clearing on success returns empty strings with default values for dropdowns
- Error handling preserves original values for user convenience
- Products array processing handles JSON strings, single strings, lists, and null values
- Environment variables with defaults allow customization without breaking existing setups

### Environment Variables
- **Required**: `DATABRICKS_TOKEN`, `RAG_ENDPOINT`
- **Optional**: `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_WAREHOUSE_ID`
- **Setup**: Copy `env.example` to `.env` and customize values

### Security
- Added validation to ensure demo exists before deletion
- Maintained secure API-based approach for all database operations
- Progress display does not expose sensitive information
- Environment variables allow secure credential management 