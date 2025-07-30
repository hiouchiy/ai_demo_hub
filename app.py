import gradio as gr
import pandas as pd
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
import requests
import markdown
import pytz
from databricks import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
RAG_ENDPOINT = os.getenv("RAG_ENDPOINT")
ITEMS_PER_PAGE = 10
JST = pytz.timezone('Asia/Tokyo')

class DatabaseManager:
    """Database connection and operations manager"""
    
    def __init__(self):
        self.server_hostname = DATABRICKS_SERVER_HOSTNAME
        self.http_path = f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}"
        self.access_token = DATABRICKS_TOKEN
        
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            query = "SELECT 1 as test"
            result = self.execute_query(query)
            return len(result) > 0
        except Exception as e:
            print(f"Database connection test failed: {str(e)}")
            return False
        
    def get_connection(self):
        """Get database connection"""
        return sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token
        )
    
    def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict]:
        """Execute query and return results"""
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            
            # ❌ fetchall()はDatabricksライブラリのバグでエラーが発生する
            # 代替アプローチ: 一行ずつ取得してリストに追加
            rows = []
            try:
                while True:
                    row = cursor.fetchone()
                    if row is None:
                        break
                    rows.append(row)
            except Exception as fetch_error:
                # fetchone()でもエラーが発生する場合は、pandasアプローチを試す
                print(f"🔍 fetchone() failed: {fetch_error}")
                try:
                    import pandas as pd
                    df = pd.read_sql(query, connection)
                    # DataFrameをリストに変換
                    rows = [tuple(row) for row in df.values]
                    columns = df.columns.tolist()
                except Exception as pandas_error:
                    print(f"🔍 pandas approach failed: {pandas_error}")
                    # 最後の手段: 空のリストを返す
                    return []
            
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            raise Exception(f"Database error: {str(e)}")
        finally:
            cursor.close()
            connection.close()
    
    def get_demos(self, page: int = 1, sort_column: str = "created_at", sort_order: str = "ASC") -> Tuple[List[Dict], int]:
        """Get paginated demo list with sorting"""
        try:
            # Validate and sanitize inputs
            if page is None or page < 1:
                page = 1
            
            offset = (page - 1) * ITEMS_PER_PAGE
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM hiroshi.ai_demo_hub.demos"
            count_result = self.execute_query(count_query)
            total_count = count_result[0]['total'] if count_result and count_result[0]['total'] is not None else 0
            
            # Get paginated data
            valid_columns = ["demo_id", "title", "summary", "owner_emp_id", "created_at", "updated_at", "status", "demo_url", "repo_url", "products", "confidentiality", "remarks"]
            if sort_column not in valid_columns:
                sort_column = "created_at"
            
            if sort_order.upper() not in ["ASC", "DESC"]:
                sort_order = "ASC"
                
            query = f"""
            SELECT demo_id, title, summary, owner_emp_id, created_at, updated_at, status, 
                   demo_url, repo_url, products, confidentiality, remarks
            FROM hiroshi.ai_demo_hub.demos
            ORDER BY {sort_column} {sort_order}
            LIMIT {ITEMS_PER_PAGE} OFFSET {offset}
            """
            
            results = self.execute_query(query)
            
            # Validate and clean results
            cleaned_results = []
            for result in results:
                if result.get('demo_id') is not None:
                    cleaned_results.append(result)
            
            return cleaned_results, total_count
            
        except Exception as e:
            print(f"Error in get_demos: {str(e)}")
            return [], 0
    
    def get_demo_by_id(self, demo_id: int) -> Optional[Dict]:
        """Get demo by ID (excluding all_info_md from user-facing operations)"""
        query = """SELECT demo_id, title, summary, description_md, owner_emp_id, created_at, updated_at, 
                          status, demo_url, repo_url, products, confidentiality, remarks 
                   FROM hiroshi.ai_demo_hub.demos WHERE demo_id = ?"""
        results = self.execute_query(query, [demo_id])
        return results[0] if results else None
    
    def get_demo_by_id_internal(self, demo_id: int) -> Optional[Dict]:
        """Get demo by ID for internal operations (includes all columns including all_info_md)"""
        query = "SELECT * FROM hiroshi.ai_demo_hub.demos WHERE demo_id = ?"
        results = self.execute_query(query, [demo_id])
        return results[0] if results else None
    
    def get_description_by_id(self, demo_id: int) -> Optional[str]:
        """Get description_md by demo_id"""
        try:
            if demo_id is None:
                return None
                
            query = "SELECT description_md FROM hiroshi.ai_demo_hub.demos WHERE demo_id = ?"
            results = self.execute_query(query, [demo_id])
            
            if results and len(results) > 0:
                return results[0].get('description_md')
            return None
        except Exception as e:
            print(f"Error in get_description_by_id: {str(e)}")
            return None
    
    def insert_demo(self, data: Dict) -> int:
        """Insert new demo"""
        try:
            # Convert products list to array format for Databricks
            products_list = [p.strip() for p in data['products'] if p.strip()]
            if products_list:
                products_array_str = ', '.join([f"'{p}'" for p in products_list])
            else:
                products_array_str = ""
            
            # Generate timestamp for both created_at and updated_at
            current_time = datetime.now(JST)
            
            # Build query with array literal directly in SQL (including all_info_md and timestamps)
            query = f"""
            INSERT INTO hiroshi.ai_demo_hub.demos 
            (title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products, confidentiality, remarks, created_at, updated_at, all_info_md)
            VALUES (?, ?, ?, ?, ?, ?, ?, array({products_array_str}), ?, ?, ?, ?, ?)
            """
            
            # Generate all_info_md with actual data (demo_id will be updated after INSERT)
            data_with_metadata = data.copy()
            data_with_metadata['demo_id'] = 'TBD'  # Will be updated after INSERT
            data_with_metadata['created_at'] = current_time
            data_with_metadata['updated_at'] = current_time
            all_info_md = generate_all_info_md(data_with_metadata)
            
            params = [
                data['title'],
                data['summary'],
                data['description_md'],
                data['owner_emp_id'],
                data['status'],
                data['demo_url'],
                data['repo_url'],
                data['confidentiality'],
                data['remarks'],
                current_time,
                current_time,
                all_info_md
            ]
            
            self.execute_query(query, params)
            
            # Get the inserted demo ID to update all_info_md with correct demo_id
            last_id_query = "SELECT MAX(demo_id) as last_id FROM hiroshi.ai_demo_hub.demos"
            result = self.execute_query(last_id_query)
            
            if result and len(result) > 0 and result[0]['last_id'] is not None:
                new_demo_id = result[0]['last_id']
                
                # Update all_info_md with correct demo_id
                data_with_metadata['demo_id'] = new_demo_id
                updated_all_info_md = generate_all_info_md(data_with_metadata)
                
                update_query = "UPDATE hiroshi.ai_demo_hub.demos SET all_info_md = ? WHERE demo_id = ?"
                self.execute_query(update_query, [updated_all_info_md, new_demo_id])
                
        except Exception as e:
            raise Exception(f"Failed to insert demo: {str(e)}")
        
        # Get the last inserted ID with proper error handling
        try:
            last_id_query = "SELECT MAX(demo_id) as last_id FROM hiroshi.ai_demo_hub.demos"
            result = self.execute_query(last_id_query)
            
            if result and len(result) > 0 and result[0]['last_id'] is not None:
                return result[0]['last_id']
            else:
                # Fallback: try to get the ID of the inserted record by matching the exact data
                fallback_query = """
                SELECT demo_id FROM hiroshi.ai_demo_hub.demos 
                WHERE title = ? AND owner_emp_id = ? AND demo_url = ?
                ORDER BY created_at DESC LIMIT 1
                """
                fallback_result = self.execute_query(fallback_query, [data['title'], data['owner_emp_id'], data['demo_url']])
                if fallback_result and len(fallback_result) > 0:
                    return fallback_result[0]['demo_id']
                else:
                    # If all else fails, return a default message
                    return 0
        except Exception as e:
            print(f"Error getting last inserted ID: {str(e)}")
            return 0
    
    def update_demo(self, demo_id: int, data: Dict) -> bool:
        """Update existing demo"""
        try:
            # Get existing demo data to preserve timestamps and demo_id for all_info_md
            existing_demo = self.get_demo_by_id_internal(demo_id)
            if existing_demo:
                # Include demo_id and timestamps in data for all_info_md generation
                data_with_metadata = data.copy()
                data_with_metadata['demo_id'] = existing_demo.get('demo_id', demo_id)
                data_with_metadata['created_at'] = existing_demo.get('created_at')
                data_with_metadata['updated_at'] = existing_demo.get('updated_at')
            else:
                data_with_metadata = data.copy()
                data_with_metadata['demo_id'] = demo_id
            
            # Convert products list to array format for Databricks
            products_list = [p.strip() for p in data['products'] if p.strip()]
            if products_list:
                products_array_str = ', '.join([f"'{p}'" for p in products_list])
            else:
                products_array_str = ""
            
            # Generate updated all_info_md content with complete metadata
            all_info_md = generate_all_info_md(data_with_metadata)
                
            # Generate current timestamp for updated_at
            current_time = datetime.now(JST)
            
            # Update metadata with current timestamp
            data_with_metadata['updated_at'] = current_time
            
            # Generate updated all_info_md content with complete metadata
            all_info_md = generate_all_info_md(data_with_metadata)
            
            # Build query with array literal directly in SQL (including all_info_md and updated_at)
            query = f"""
            UPDATE hiroshi.ai_demo_hub.demos 
            SET title = ?, summary = ?, description_md = ?, owner_emp_id = ?, status = ?, 
                demo_url = ?, repo_url = ?, products = array({products_array_str}), confidentiality = ?, remarks = ?, 
                updated_at = ?, all_info_md = ?
            WHERE demo_id = ?
            """
            
            params = [
                data['title'],
                data['summary'],
                data['description_md'],
                data['owner_emp_id'],
                data['status'],
                data['demo_url'],
                data['repo_url'],
                data['confidentiality'],
                data['remarks'],
                current_time,
                all_info_md,
                demo_id
            ]
            
            self.execute_query(query, params)
            return True
        except Exception as e:
            raise Exception(f"Failed to update demo: {str(e)}")

class RAGClient:
    """RAG system client for semantic search"""
    
    def __init__(self):
        self.endpoint = RAG_ENDPOINT
        self.token = DATABRICKS_TOKEN
        
    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Send chat completion request to RAG system"""
        if not self.endpoint:
            return "RAG_ENDPOINTが設定されていません。環境変数を確認してください。"
            
        data = {
            "messages": messages
        }
        
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {self.token}"
        }
        
        # Debug: Print request details
        print(f"🔍 RAG Request Debug:")
        print(f"   Endpoint: {self.endpoint}")
        print(f"   Messages count: {len(messages)}")
        print(f"   Request data: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        try:
            response = requests.post(
                url=self.endpoint, 
                json=data, 
                headers=headers
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   Response text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            print(f"   Response success: {len(result.get('choices', []))} choices")
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"   RAG Error: {str(e)}")
            return f"エラーが発生しました: {str(e)}"

# Global instances
# APIベースのDatabaseManagerを使用してsqlクライアントの問題を回避
from api_database_manager import APIBasedDatabaseManager
db_manager = APIBasedDatabaseManager()
rag_client = RAGClient()

# Global variable to store current demo list for table click functionality
current_demo_list = []

# Utility functions
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_all_info_md(data: Dict) -> str:
    """Generate all_info_md content from demo data (includes ALL columns except all_info_md)"""
    # Handle products - could be list or string
    products = data.get('products', [])
    if isinstance(products, list):
        products_str = ", ".join(products) if products else "なし"
    else:
        products_str = str(products) if products else "なし"
    
    # Format timestamps if available
    created_at_str = format_datetime(data.get('created_at')) if data.get('created_at') else "未設定"
    updated_at_str = format_datetime(data.get('updated_at')) if data.get('updated_at') else "未更新"
    
    # Get actual values or show empty/default values
    demo_id = data.get('demo_id', 'TBD')
    title = data.get('title', '') or 'タイトル未設定'
    summary = data.get('summary', '') or '概要未設定'
    description_md = data.get('description_md', '') or '詳細説明未設定'
    owner_emp_id = data.get('owner_emp_id', '') or '未設定'
    status = data.get('status', '') or '未設定'
    demo_url = data.get('demo_url', '') or 'なし'
    repo_url = data.get('repo_url', '') or 'なし'
    confidentiality = data.get('confidentiality', '') or '未設定'
    remarks = data.get('remarks', '') or 'なし'
    
    md_content = f"""# {title}

## 基本情報
- **Demo ID**: {demo_id}
- **代表投稿者**: {owner_emp_id}
- **ステータス**: {status}
- **機密レベル**: {confidentiality}
- **登録日時**: {created_at_str}
- **最終編集日時**: {updated_at_str}

## 概要
{summary}

## 詳細説明
{description_md}

## リンク
- **デモURL**: {demo_url}
- **リポジトリURL**: {repo_url}

## 利用製品
{products_str}

## 備考
{remarks}
"""
    return md_content

def format_datetime(dt) -> str:
    """Format datetime to JST string"""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    # Convert to JST
    jst_dt = dt.astimezone(JST)
    return jst_dt.strftime("%Y-%m-%d %H:%M:%S JST")

def parse_products(products_str: str) -> List[str]:
    """Parse products string to list"""
    if not products_str:
        return []
    # Handle comma-separated values
    return [p.strip() for p in products_str.split(',') if p.strip()]

def render_markdown(text: str) -> str:
    """Render markdown to HTML"""
    if not text:
        return ""
    try:
        html = markdown.markdown(text, extensions=['tables', 'fenced_code'])
        return html
    except:
        return text

def make_clickable_links(text: str) -> str:
    """Convert URLs in text to clickable links"""
    # URL pattern that includes valid URL characters
    url_pattern = r'https?://[a-zA-Z0-9._~:/?#[\]@!$&\'()*+,;=%\-]*[a-zA-Z0-9_~/#@$*+=\-]'
    
    def replace_url(match):
        url = match.group(0)
        
        # Remove trailing punctuation and encoded Japanese punctuation
        # Common patterns: )%E3%80%82 (encoded 。), )%E3%80%81 (encoded 、)
        if ')%E3%80%82' in url:  # )。
            url = url.split(')%E3%80%82')[0]
        elif ')%E3%80%81' in url:  # )、
            url = url.split(')%E3%80%81')[0]
        else:
            # Remove common trailing punctuation
            while url and url[-1] in '。、,，!！)）]】〉》」』':
                url = url[:-1]
        
        return f'<a href="{url}" target="_blank">{url}</a>'
    
    return re.sub(url_pattern, replace_url, text)

def convert_markdown_footnotes(text: str) -> str:
    """Convert Markdown footnote references to readable superscript numbers"""
    import re
    
    # Find all footnote references
    footnote_pattern = r'\[\^[^\]]+\]'
    footnotes = re.findall(footnote_pattern, text)
    
    if not footnotes:
        return text
    
    # Create mapping from footnote to superscript number
    footnote_map = {}
    for i, footnote in enumerate(set(footnotes), 1):
        # Use Unicode superscript characters for numbers 1-9, then fallback
        if i <= 9:
            superscript_nums = ['¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']
            footnote_map[footnote] = superscript_nums[i-1]
        else:
            # For more than 9 footnotes, use parentheses format
            footnote_map[footnote] = f'({i})'
    
    # Replace footnotes with superscript numbers
    result = text
    for footnote, replacement in footnote_map.items():
        result = result.replace(footnote, replacement)
    
    return result

# Global variables for table click optimization
last_displayed_demo_id = None
last_displayed_demo_html = None

def get_previous_page(current_page: int) -> int:
    """Get previous page number"""
    return max(1, current_page - 1)

def get_next_page(current_page: int, total_pages: int) -> int:
    """Get next page number"""
    return min(total_pages, current_page + 1)

def get_button_states(current_page: int, total_pages: int) -> tuple:
    """Get the interactive states for previous and next buttons"""
    prev_enabled = current_page > 1
    next_enabled = current_page < total_pages
    return prev_enabled, next_enabled

# Tab 1: Demo List
def load_demo_list(page: int = 1):
    """Load demo list with pagination and sorting"""
    try:
        # Validate inputs with proper type checking
        if page is None or not isinstance(page, (int, float)):
            page = 1
        else:
            page = int(page)
            
        # Use default sorting by created_at DESC (newest first)
        demos, total_count = db_manager.get_demos(page, "created_at", "DESC")
        
        # Format data for display
        formatted_demos = []
        for demo in demos:
            # Safely handle None values and type conversion
            try:
                # Handle demo_id - convert string to int if needed
                demo_id = demo.get("demo_id")
                if demo_id is not None:
                    demo_id = int(demo_id) if isinstance(demo_id, str) else demo_id
                else:
                    demo_id = 0
                
                # Handle products - could be string or list
                products = demo.get("products", [])
                if isinstance(products, str):
                    # Handle JSON string format like '["Apps"]'
                    try:
                        import json
                        products = json.loads(products)
                    except:
                        # If JSON parsing fails, treat as comma-separated string
                        products = [p.strip() for p in products.split(',') if p.strip()]
                products_str = ", ".join(products) if products else ""
                
                formatted_demo = {
                    "demo_id": demo_id,
                    "title": demo.get("title") or "",
                    "summary": demo.get("summary") or "",
                    "owner_emp_id": demo.get("owner_emp_id") or "",
                    "updated_at": format_datetime(demo.get("updated_at")),
                    "status": demo.get("status") or "",
                    "demo_url": demo.get("demo_url") or "",
                    "repo_url": demo.get("repo_url") or "",
                    "products": products_str,
                    "confidentiality": demo.get("confidentiality") or "",
                    "remarks": demo.get("remarks") or ""
                }
                formatted_demos.append(formatted_demo)
            except Exception as format_error:
                print(f"Error formatting demo: {format_error}")
                continue
        
        # Store current demo list globally for table click functionality
        global current_demo_list, last_displayed_demo_id, last_displayed_demo_html
        current_demo_list = formatted_demos
        
        # Clear cache when new demo list is loaded
        last_displayed_demo_id = None
        last_displayed_demo_html = None
        
        df = pd.DataFrame(formatted_demos)
        
        # Calculate pagination info - ensure proper type conversion
        total_count = int(total_count) if total_count is not None else 0
        total_pages = max(1, (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        page_info = f"Page {page} of {total_pages} (Total: {total_count} demos)"
        
        # Calculate button states
        prev_enabled, next_enabled = get_button_states(page, total_pages)
        
        return df, page_info, page, total_pages, prev_enabled, next_enabled
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Load demo list error: {error_msg}")
        return pd.DataFrame(), error_msg, 1, 1, False, False

def show_demo_all_info_by_click(evt: gr.SelectData):
    """Show all_info_md content when a table row is clicked"""
    try:
        global current_demo_list, last_displayed_demo_id, last_displayed_demo_html
        
        if evt is None or evt.index is None:
            return "テーブルの行をクリックしてください。"
        
        # Get the clicked row index
        row_idx = evt.index[0]
        
        # Check if we have the current demo list and valid row index
        if not current_demo_list or row_idx >= len(current_demo_list):
            return "データが見つかりません。ページを再読み込みしてください。"
        
        # Get demo_id from the current demo list
        demo = current_demo_list[row_idx]
        demo_id = demo.get("demo_id")
        
        if not demo_id:
            return "Demo IDが見つかりません。"
        
        # Check if we already have this demo's details cached
        if demo_id == last_displayed_demo_id and last_displayed_demo_html:
            # Return cached result to avoid unnecessary database query
            return last_displayed_demo_html
        
        # Get demo with all_info_md using internal function
        demo_full = db_manager.get_demo_by_id_internal(demo_id)
        
        if demo_full and demo_full.get('all_info_md'):
            # Convert markdown to HTML for display
            html_content = markdown.markdown(demo_full['all_info_md'])
            formatted_html = f'<div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; max-height: 600px; overflow-y: auto;">{html_content}</div>'
            
            # Cache the result
            last_displayed_demo_id = demo_id
            last_displayed_demo_html = formatted_html
            
            return formatted_html
        elif demo_full:
            error_msg = "このデモにはall_info_md情報がありません。（古いデータの可能性があります）"
            # Cache the error result as well
            last_displayed_demo_id = demo_id
            last_displayed_demo_html = error_msg
            return error_msg
        else:
            return "指定されたDemo IDのデモが見つかりません。"
            
    except Exception as e:
        return f"エラー: {str(e)}"

# Tab 2: New Demo Registration
def register_demo(title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, progress=gr.Progress()):
    """Register new demo with progress display"""
    try:
        progress(0.1, desc="Validating input...")
        
        # Validation
        if not title or not owner_emp_id or not status or not demo_url:
            return "Error: Required fields (title, owner_emp_id, status, demo_url) cannot be empty.", title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks
        
        if not validate_email(owner_emp_id):
            return "Error: Invalid email format for owner_emp_id.", title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks
        
        progress(0.3, desc="Processing products...")
        
        products = parse_products(products_str)
        
        progress(0.5, desc="Preparing data...")
        
        # Ensure all fields have safe default values
        data = {
            "title": title or "",
            "summary": summary or "",
            "description_md": description_md or "",
            "owner_emp_id": owner_emp_id or "",
            "status": status or "draft",
            "demo_url": demo_url or "",
            "repo_url": repo_url or "",
            "products": products or [],
            "confidentiality": confidentiality or "internal",
            "remarks": remarks or ""
        }
        
        progress(0.8, desc="Registering demo...")
        
        demo_id = db_manager.insert_demo(data)
        
        progress(1.0, desc="Registration completed!")
        
        # Handle the case where demo_id might be None or 0
        if demo_id and demo_id > 0:
            # Clear all fields after successful registration
            return f"Success: Demo registered with ID {demo_id}", "", "", "", "", "draft", "", "", "", "internal", ""
        else:
            # Clear all fields after successful registration
            return "Success: Demo registered successfully", "", "", "", "", "draft", "", "", "", "internal", ""
        
    except Exception as e:
        return f"Error: {str(e)}", title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks

# Tab 3: Demo Update
def search_demo_for_update(demo_id: str):
    """Search demo by ID for update"""
    try:
        if not demo_id or demo_id.strip() == "":
            return "", "", "", "", "", "", "", "", "", "", "Please enter a demo ID."
        
        # Convert to int with better error handling
        try:
            demo_id_int = int(float(demo_id.strip()))
            if demo_id_int <= 0:
                return "", "", "", "", "", "", "", "", "", "", "Demo ID must be a positive number."
        except (ValueError, TypeError, OverflowError):
            return "", "", "", "", "", "", "", "", "", "", "Invalid demo ID format. Please enter a valid number."
        
        demo = db_manager.get_demo_by_id(demo_id_int)
        
        if not demo:
            return "", "", "", "", "", "", "", "", "", "", "Demo not found."
        
        # Handle products array properly
        products_str = ""
        if demo.get("products"):
            products_value = demo["products"]
            
            if isinstance(products_value, list):
                # If it's already a list, join it
                products_str = ", ".join(products_value)
            elif isinstance(products_value, str):
                # If it's a string, check if it's JSON format
                try:
                    import json
                    if products_value.startswith('[') and products_value.endswith(']'):
                        products_list = json.loads(products_value)
                        products_str = ", ".join(products_list)
                    else:
                        # If it's just a plain string, use it as is
                        products_str = products_value
                except json.JSONDecodeError:
                    # If JSON parsing fails, use the string as is
                    products_str = products_value
            else:
                # For any other type, convert to string
                products_str = str(products_value)
        
        return (
            demo["title"],
            demo["summary"] or "",
            demo["description_md"] or "",
            demo["owner_emp_id"],
            demo["status"],
            demo["demo_url"],
            demo["repo_url"] or "",
            products_str,
            demo["confidentiality"] or "",
            demo["remarks"] or "",
            f"Demo found: {demo['title']}"
        )
        
    except ValueError:
        return "", "", "", "", "", "", "", "", "", "", "Invalid demo ID format."
    except Exception as e:
        return "", "", "", "", "", "", "", "", "", "", f"Error: {str(e)}"

def update_demo(demo_id: str, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, progress=gr.Progress()):
    """Update existing demo with progress display"""
    try:
        progress(0.1, desc="Validating input...")
        
        if not demo_id or demo_id.strip() == "":
            return "Error: Please search for a demo first.", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Please search for a demo first."
        
        # Validation
        if not title or not owner_emp_id or not status or not demo_url:
            return "Error: Required fields (title, owner_emp_id, status, demo_url) cannot be empty.", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Required fields cannot be empty."
        
        if not validate_email(owner_emp_id):
            return "Error: Invalid email format for owner_emp_id.", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid email format."
        
        progress(0.3, desc="Processing demo ID...")
        
        # Convert to int with better error handling
        try:
            demo_id_int = int(float(demo_id.strip()))
            if demo_id_int <= 0:
                return "Error: Demo ID must be a positive number.", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid demo ID."
        except (ValueError, TypeError, OverflowError):
            return "Error: Invalid demo ID format.", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid demo ID format."
        
        progress(0.5, desc="Preparing data...")
        
        products = parse_products(products_str)
        
        data = {
            "title": title,
            "summary": summary,
            "description_md": description_md,
            "owner_emp_id": owner_emp_id,
            "status": status,
            "demo_url": demo_url,
            "repo_url": repo_url,
            "products": products,
            "confidentiality": confidentiality,
            "remarks": remarks
        }
        
        progress(0.8, desc="Updating demo...")
        
        db_manager.update_demo(demo_id_int, data)
        
        progress(1.0, desc="Update completed!")
        
        # Clear all fields on successful update
        return "Success: Demo updated successfully.", "", "", "", "", "", "draft", "", "", "", "internal", "", ""
        
    except ValueError:
        return "Error: Invalid demo ID format.", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid demo ID format."
    except Exception as e:
        return f"Error: {str(e)}", demo_id, title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, f"Error: {str(e)}"

def delete_demo(demo_id: str, progress=gr.Progress()):
    """Delete demo by ID with progress display"""
    try:
        progress(0.1, desc="Validating input...")
        
        if not demo_id or demo_id.strip() == "":
            return "Error: Please search for a demo first.", demo_id, "", "", "", "", "draft", "", "", "", "internal", "", "Please search for a demo first."
        
        progress(0.3, desc="Processing demo ID...")
        
        # Convert to int with better error handling
        try:
            demo_id_int = int(float(demo_id.strip()))
            if demo_id_int <= 0:
                return "Error: Demo ID must be a positive number.", demo_id, "", "", "", "", "draft", "", "", "", "internal", "", "Invalid demo ID."
        except (ValueError, TypeError, OverflowError):
            return "Error: Invalid demo ID format.", demo_id, "", "", "", "", "draft", "", "", "", "internal", "", "Invalid demo ID format."
        
        progress(0.5, desc="Checking demo existence...")
        
        # Check if demo exists before deletion
        demo = db_manager.get_demo_by_id(demo_id_int)
        if not demo:
            return "Error: Demo not found.", demo_id, "", "", "", "", "draft", "", "", "", "internal", "", "Demo not found."
        
        progress(0.8, desc="Deleting demo...")
        
        # Delete the demo
        db_manager.delete_demo(demo_id_int)
        
        progress(1.0, desc="Deletion completed!")
        
        # Clear all fields on successful deletion
        return f"Success: Demo ID {demo_id_int} has been deleted successfully.", "", "", "", "", "", "draft", "", "", "", "internal", "", ""
        
    except ValueError:
        return "Error: Invalid demo ID format.", demo_id, "", "", "", "", "draft", "", "", "", "internal", "", "Invalid demo ID format."
    except Exception as e:
        return f"Error: {str(e)}", demo_id, "", "", "", "", "draft", "", "", "", "internal", "", f"Error: {str(e)}"

# Tab 4: Semantic Search Chat
def chat_with_rag(message: str, history: List[Dict]):
    """Chat with RAG system - progressive update with thinking indicator"""
    try:
        # First, add user message to history and yield to show it immediately
        history.append({"role": "user", "content": message})
        yield "", history
        
        # Add animated "thinking" indicator with blinking and loading dots effect
        thinking_msg = '''<div style="color: #666; font-size: 14px;">
        <style>
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.4; }
        }
        @keyframes loading {
            0% { content: ""; }
            25% { content: "."; }
            50% { content: ".."; }
            75% { content: "..."; }
            100% { content: ""; }
        }
        .thinking {
            animation: blink 2s infinite;
        }
        .dots::after {
            content: "";
            animation: loading 1.5s infinite;
        }
        </style>
        <span class="thinking">🤖 考え中</span><span class="dots"></span> 💭
        </div>'''
        history.append({"role": "assistant", "content": thinking_msg})
        yield "", history
        
        # Build messages for RAG endpoint (simplified format)
        messages = []
        
        # Add conversation history (limit to recent messages to avoid token limits)
        # Exclude the user message and thinking indicator we just added
        recent_history = history[:-2][-6:] if len(history) > 8 else history[:-2]
        for msg in recent_history:
            if msg.get("role") and msg.get("content"):
                messages.append({
                    "role": msg["role"], 
                    "content": msg["content"]
                })
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Get response from RAG
        response = rag_client.chat_completion(messages)
        
        # Convert markdown footnotes to readable format and make URLs clickable
        response_converted = convert_markdown_footnotes(response)
        response_with_links = make_clickable_links(response_converted)
        
        # Replace thinking indicator with actual response
        history[-1] = {"role": "assistant", "content": response_with_links}
        yield "", history
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        
        # Add user message first if not already added
        if not history or history[-1].get("role") != "user" or history[-1].get("content") != message:
            history.append({"role": "user", "content": message})
            yield "", history
        
        # Add animated "thinking" indicator with blinking and loading dots effect
        thinking_msg = '''<div style="color: #666; font-size: 14px;">
        <style>
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.4; }
        }
        @keyframes loading {
            0% { content: ""; }
            25% { content: "."; }
            50% { content: ".."; }
            75% { content: "..."; }
            100% { content: ""; }
        }
        .thinking {
            animation: blink 2s infinite;
        }
        .dots::after {
            content: "";
            animation: loading 1.5s infinite;
        }
        </style>
        <span class="thinking">🤖 考え中</span><span class="dots"></span> 💭
        </div>'''
        history.append({"role": "assistant", "content": thinking_msg})
        yield "", history
        
        # Replace thinking indicator with error message
        history[-1] = {"role": "assistant", "content": error_msg}
        yield "", history

# Create Gradio interface
def create_interface():
    """Create the main Gradio interface"""
    
    with gr.Blocks(title="AI Demo Hub", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 AI Demo Hub - 社内AIデモ共有サイト")
        
        with gr.Tabs():
            # Tab 1: Demo List
            with gr.TabItem("📋 デモ一覧"):
                gr.Markdown("## デモ一覧")
                gr.Markdown("**使い方**: テーブルの行をクリックすると、そのデモの詳細情報が下に表示されます。")
                
                with gr.Row():
                    page_input = gr.Number(label="ページ", value=1, precision=0, minimum=1)
                    refresh_btn = gr.Button("🔄 最新情報に更新", variant="primary")
                
                # Pagination controls
                with gr.Row():
                    prev_btn = gr.Button("« 前へ", size="sm")
                    page_info = gr.Markdown("")
                    next_btn = gr.Button("次へ »", size="sm")
                
                # Hidden states for pagination
                current_page_state = gr.State(value=1)
                total_pages_state = gr.State(value=1)
                
                demo_table = gr.DataFrame(
                    headers=["demo_id", "title", "summary", "owner_emp_id", "updated_at", "status", "demo_url", "repo_url", "products", "confidentiality", "remarks"],
                    interactive=False
                )
                
                demo_details = gr.HTML(label="デモ詳細", value="<p>テーブルの行をクリックすると詳細が表示されます。</p>")
                
                # Event handlers
                def refresh_demo_list(page):
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(page)
                    return df, page_info, current_page, total_pages, gr.update(interactive=prev_enabled), gr.update(interactive=next_enabled)
                
                refresh_btn.click(
                    refresh_demo_list,
                    inputs=[page_input],
                    outputs=[demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
                
                # Previous page button
                def go_previous_page(current_page, total_pages):
                    new_page = get_previous_page(current_page)
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(new_page)
                    return new_page, df, page_info, current_page, total_pages, gr.update(interactive=prev_enabled), gr.update(interactive=next_enabled)
                
                prev_btn.click(
                    go_previous_page,
                    inputs=[current_page_state, total_pages_state],
                    outputs=[page_input, demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
                
                # Next page button
                def go_next_page(current_page, total_pages):
                    new_page = get_next_page(current_page, total_pages)
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(new_page)
                    return new_page, df, page_info, current_page, total_pages, gr.update(interactive=prev_enabled), gr.update(interactive=next_enabled)
                
                next_btn.click(
                    go_next_page,
                    inputs=[current_page_state, total_pages_state],
                    outputs=[page_input, demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
                
                demo_table.select(
                    show_demo_all_info_by_click,
                    outputs=[demo_details]
                )
                
                # Load initial data
                demo.load(
                    refresh_demo_list,
                    inputs=[gr.Number(value=1, visible=False)],
                    outputs=[demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
            
            # Tab 2: New Demo Registration
            with gr.TabItem("➕ 新規登録"):
                gr.Markdown("## 新規デモ登録")
                
                with gr.Column():
                    reg_title = gr.Textbox(label="タイトル *", placeholder="デモのタイトル")
                    reg_summary = gr.Textbox(label="要約", placeholder="カード表示用の要約")
                    reg_description = gr.Textbox(label="詳細説明 (Markdownも可)", lines=5, placeholder="詳細説明をMarkdown形式でも記載可能")
                    reg_owner = gr.Textbox(label="代表投稿者メールアドレス *", placeholder="john.smith@databricks.com")
                    reg_status = gr.Dropdown(
                        label="ステータス *",
                        choices=["draft", "in_review", "published", "archived"],
                        value="draft"
                    )
                    reg_demo_url = gr.Textbox(label="デモURL *", placeholder="https://example.com/demo")
                    reg_repo_url = gr.Textbox(label="リポジトリURL", placeholder="https://github.com/user/repo")
                    reg_products = gr.Textbox(label="利用製品", placeholder="製品名をカンマ区切りで入力 (例: Databricks, MLflow, Delta Lake)")
                    reg_confidentiality = gr.Dropdown(
                        label="機密レベル",
                        choices=["public", "internal"],
                        value="internal"
                    )
                    reg_remarks = gr.Textbox(label="備考", lines=3, placeholder="追加の備考があれば記載")
                
                reg_btn = gr.Button("登録", variant="primary")
                reg_result = gr.Markdown("")
                
                reg_btn.click(
                    register_demo,
                    inputs=[reg_title, reg_summary, reg_description, reg_owner, reg_status, reg_demo_url, reg_repo_url, reg_products, reg_confidentiality, reg_remarks],
                    outputs=[reg_result, reg_title, reg_summary, reg_description, reg_owner, reg_status, reg_demo_url, reg_repo_url, reg_products, reg_confidentiality, reg_remarks],
                    show_progress=True
                )
            
            # Tab 3: Demo Update
            with gr.TabItem("✏️ 情報更新"):
                gr.Markdown("## デモ情報更新")
                
                with gr.Row():
                    upd_demo_id = gr.Textbox(label="Demo ID", placeholder="更新するデモのID")
                    search_btn = gr.Button("検索", variant="secondary")
                
                search_result = gr.Markdown("")
                
                with gr.Column():
                    upd_title = gr.Textbox(label="タイトル *", placeholder="デモのタイトル")
                    upd_summary = gr.Textbox(label="要約", placeholder="カード表示用の要約")
                    upd_description = gr.Textbox(label="詳細説明 (Markdownも可)", lines=5, placeholder="詳細説明をMarkdown形式でも記載可能")
                    upd_owner = gr.Textbox(label="代表投稿者メールアドレス *", placeholder="john.smith@databricks.com")
                    upd_status = gr.Dropdown(
                        label="ステータス *",
                        choices=["draft", "in_review", "published", "archived"],
                        value="draft"
                    )
                    upd_demo_url = gr.Textbox(label="デモURL *", placeholder="https://example.com/demo")
                    upd_repo_url = gr.Textbox(label="リポジトリURL", placeholder="https://github.com/user/repo")
                    upd_products = gr.Textbox(label="利用製品", placeholder="製品名をカンマ区切りで入力 (例: Databricks, MLflow, Delta Lake)")
                    upd_confidentiality = gr.Dropdown(
                        label="機密レベル",
                        choices=["public", "internal"],
                        value="internal"
                    )
                    upd_remarks = gr.Textbox(label="備考", lines=3, placeholder="追加の備考があれば記載")
                
                with gr.Row():
                    upd_btn = gr.Button("更新", variant="primary")
                    del_btn = gr.Button("削除", variant="stop")
                
                upd_result = gr.Markdown("")
                
                search_btn.click(
                    search_demo_for_update,
                    inputs=[upd_demo_id],
                    outputs=[upd_title, upd_summary, upd_description, upd_owner, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result]
                )
                
                upd_btn.click(
                    update_demo,
                    inputs=[upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks],
                    outputs=[upd_result, upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result],
                    show_progress=True
                )
                
                del_btn.click(
                    delete_demo,
                    inputs=[upd_demo_id],
                    outputs=[upd_result, upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result],
                    show_progress=True
                )
            
            # Tab 4: Semantic Search Chat
            with gr.TabItem("🤖 セマンティック検索"):
                gr.Markdown("## AIチャットボットによるデモ検索")
                gr.Markdown("デモに関する質問をしてください。AIが関連するデモを見つけてお答えします。")
                
                chatbot = gr.Chatbot(
                    height=400,
                    show_label=False,
                    type='messages',
                    avatar_images=("https://cdn-icons-png.flaticon.com/512/1053/1053244.png", "https://cdn-icons-png.flaticon.com/512/4712/4712109.png")
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="メッセージ",
                        placeholder="例: 機械学習に関するデモはありますか？",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("送信", variant="primary", scale=1)
                
                clear_btn = gr.Button("チャット履歴をクリア", variant="secondary")
                
                send_btn.click(
                    chat_with_rag,
                    inputs=[msg, chatbot],
                    outputs=[msg, chatbot]
                )
                
                msg.submit(
                    chat_with_rag,
                    inputs=[msg, chatbot],
                    outputs=[msg, chatbot]
                )
                
                clear_btn.click(
                    lambda: ([], ""),
                    outputs=[chatbot, msg]
                )
    
    return demo

if __name__ == "__main__":
    # Check environment variables
    if not DATABRICKS_TOKEN:
        print("Error: DATABRICKS_TOKEN environment variable is not set")
        exit(1)
    
    if not RAG_ENDPOINT:
        print("Error: RAG_ENDPOINT environment variable is not set")
        exit(1)
    
    # Create and launch the interface
    interface = create_interface()
    
    # Launch with error handling
    try:
        interface.launch(
            # server_name="127.0.0.1",
            # server_port=7860,
            # share=False,
            # show_error=True,
            # debug=False
        )
    except Exception as e:
        print(f"Launch error: {e}")
        print("Trying alternative launch configuration...")
        interface.launch(
            share=True,
            show_error=True,
            debug=False
        ) 