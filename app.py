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
ITEMS_PER_PAGE = 20
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
        """Get demo by ID"""
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
                
            # Build query with array literal directly in SQL
            query = f"""
            INSERT INTO hiroshi.ai_demo_hub.demos 
            (title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products, confidentiality, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, array({products_array_str}), ?, ?)
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
                data['remarks']
            ]
            
            self.execute_query(query, params)
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
            # Convert products list to array format for Databricks
            products_list = [p.strip() for p in data['products'] if p.strip()]
            if products_list:
                products_array_str = ', '.join([f"'{p}'" for p in products_list])
            else:
                products_array_str = ""
                
            # Build query with array literal directly in SQL
            query = f"""
            UPDATE hiroshi.ai_demo_hub.demos 
            SET title = ?, summary = ?, description_md = ?, owner_emp_id = ?, status = ?, 
                demo_url = ?, repo_url = ?, products = array({products_array_str}), confidentiality = ?, remarks = ?
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

# Utility functions
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

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
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]*'
    return re.sub(url_pattern, r'<a href="\g<0>" target="_blank">\g<0></a>', text)

# Tab 1: Demo List
def load_demo_list(page: int = 1, sort_column: str = "created_at", sort_order: str = "ASC"):
    """Load demo list with pagination and sorting"""
    try:
        # Validate inputs with proper type checking
        if page is None or not isinstance(page, (int, float)):
            page = 1
        else:
            page = int(page)
            
        if sort_column is None or not isinstance(sort_column, str):
            sort_column = "created_at"
        if sort_order is None or not isinstance(sort_order, str):
            sort_order = "ASC"
        
        demos, total_count = db_manager.get_demos(page, sort_column, sort_order)
        
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
                    "created_at": format_datetime(demo.get("created_at")),
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
        
        df = pd.DataFrame(formatted_demos)
        
        # Calculate pagination info - ensure proper type conversion
        total_count = int(total_count) if total_count is not None else 0
        total_pages = max(1, (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        page_info = f"Page {page} of {total_pages} (Total: {total_count} demos)"
        
        return df, page_info, total_pages
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Load demo list error: {error_msg}")
        return pd.DataFrame(), error_msg, 1

def show_description_popup(demo_id):
    """Show description popup for selected demo"""
    try:
        # Validate demo_id
        if demo_id is None or demo_id == "":
            return "Please enter a valid demo ID."
        
        # Convert to int if necessary with better error handling
        try:
            if isinstance(demo_id, str) and demo_id.strip() == "":
                return "Please enter a valid demo ID."
            demo_id = int(float(demo_id))  # Handle both int and float inputs
            if demo_id <= 0:
                return "Demo ID must be a positive number."
        except (ValueError, TypeError, OverflowError):
            return "Invalid demo ID format. Please enter a valid number."
            
        description = db_manager.get_description_by_id(demo_id)
        if description:
            return render_markdown(description)
        else:
            return "Description not found."
    except Exception as e:
        return f"Error loading description: {str(e)}"

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
def chat_with_rag(message: str, history: List[Dict]) -> Tuple[str, List[Dict]]:
    """Chat with RAG system"""
    try:
        # Build messages for RAG endpoint (simplified format)
        messages = []
        
        # Add conversation history (limit to recent messages to avoid token limits)
        recent_history = history[-6:] if len(history) > 6 else history
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
        
        # Make URLs clickable
        response_with_links = make_clickable_links(response)
        
        # Update history with new message format
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_with_links})
        
        return "", history
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return "", history

# Create Gradio interface
def create_interface():
    """Create the main Gradio interface"""
    
    with gr.Blocks(title="AI Demo Hub", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 AI Demo Hub - 社内AIデモ共有サイト")
        
        with gr.Tabs():
            # Tab 1: Demo List
            with gr.TabItem("📋 デモ一覧"):
                gr.Markdown("## デモ一覧")
                
                with gr.Row():
                    page_input = gr.Number(label="ページ", value=1, precision=0, minimum=1)
                    sort_column = gr.Dropdown(
                        label="ソート列",
                        choices=["demo_id", "title", "created_at", "updated_at", "status", "owner_emp_id"],
                        value="created_at"
                    )
                    sort_order = gr.Dropdown(
                        label="ソート順",
                        choices=["ASC", "DESC"],
                        value="ASC"
                    )
                    load_btn = gr.Button("読み込み", variant="primary")
                
                page_info = gr.Markdown("")
                demo_table = gr.DataFrame(
                    headers=["demo_id", "title", "summary", "owner_emp_id", "created_at", "updated_at", "status", "demo_url", "repo_url", "products", "confidentiality", "remarks"],
                    interactive=False
                )
                
                with gr.Row():
                    demo_id_input = gr.Number(label="詳細を見るDemo ID", precision=0)
                    show_desc_btn = gr.Button("詳細表示")
                
                description_popup = gr.HTML(label="詳細説明")
                
                # Event handlers
                load_btn.click(
                    load_demo_list,
                    inputs=[page_input, sort_column, sort_order],
                    outputs=[demo_table, page_info]
                )
                
                show_desc_btn.click(
                    show_description_popup,
                    inputs=[demo_id_input],
                    outputs=[description_popup]
                )
                
                # Load initial data
                demo.load(
                    load_demo_list,
                    inputs=[gr.Number(value=1, visible=False), gr.Textbox(value="created_at", visible=False), gr.Textbox(value="ASC", visible=False)],
                    outputs=[demo_table, page_info]
                )
            
            # Tab 2: New Demo Registration
            with gr.TabItem("➕ 新規登録"):
                gr.Markdown("## 新規デモ登録")
                
                with gr.Column():
                    reg_title = gr.Textbox(label="タイトル *", placeholder="デモのタイトル")
                    reg_summary = gr.Textbox(label="要約", placeholder="カード表示用の要約")
                    reg_description = gr.Textbox(label="詳細説明 (Markdown)", lines=5, placeholder="詳細説明をMarkdown形式で記載")
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
                    upd_description = gr.Textbox(label="詳細説明 (Markdown)", lines=5, placeholder="詳細説明をMarkdown形式で記載")
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
            server_name="127.0.0.1",
            server_port=7860,
            # share=False,
            show_error=True,
            debug=False
        )
    except Exception as e:
        print(f"Launch error: {e}")
        print("Trying alternative launch configuration...")
        interface.launch(
            share=True,
            show_error=True,
            debug=False
        ) 