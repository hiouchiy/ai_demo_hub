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
from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_HOST")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
RAG_ENDPOINT = os.getenv("RAG_ENDPOINT")
ITEMS_PER_PAGE = 10
JST = pytz.timezone('Asia/Tokyo')

# Translation dictionary for multilingual support
TRANSLATIONS = {
    "ja": {
        # Tab names
        "tab_demo_list": "📋 デモ一覧",
        "tab_new_registration": "➕ 新規登録",
        "tab_update_info": "✏️ 情報更新",
        "tab_ask_bot": "🤖 Botに相談",
        
        # Button labels
        "btn_refresh": "🔄 最新情報に更新",
        "btn_previous": "« 前へ",
        "btn_next": "次へ »",
        "btn_ai_generate": "🤖 AIで自動生成",
        "btn_ai_polish": "🤖 AIで自動清書",
        "btn_register": "登録",
        "btn_search": "検索",
        "btn_update": "更新",
        "btn_delete": "削除",
        "btn_cancel": "キャンセル",
        "btn_send": "送信",
        "btn_clear_chat": "チャット履歴をクリア",
        "btn_language": "言語",
        
        # Field labels
        "label_page": "ページ",
        "label_demo_details": "デモ詳細",
        "label_title_required": "タイトル *",
        "label_summary": "要約",
        "label_description_required": "詳細説明 (Markdownも可) *",
        "label_owner_email_required": "代表投稿者メールアドレス *",
        "label_creator_email": "デモ作成者メールアドレス",
        "label_status_required": "ステータス *",
        "label_demo_url_required": "デモURL *",
        "label_repo_url": "リポジトリURL",
        "label_products": "利用製品",
        "label_confidentiality": "機密レベル",
        "label_remarks": "備考",
        "label_demo_id": "Demo ID",
        "label_message": "メッセージ（入力後にShift+Enterで送信）",
        
        # Placeholders
        "placeholder_demo_title": "デモのタイトル",
        "placeholder_card_summary": "カード表示用の要約",
        "placeholder_description_md": "詳細説明をMarkdown形式でも記載可能",
        "placeholder_creator_email": "デモを作成した人のメールアドレス（不明の場合は空白でOK）",
        "placeholder_demo_url": "https://example.com/demo",
        "placeholder_repo_url": "https://github.com/user/repo",
        "placeholder_products": "製品名をカンマ区切りで入力 (例: Databricks, MLflow, Delta Lake)",
        "placeholder_remarks": "追加の備考があれば記載",
        "placeholder_demo_id_update": "更新するデモのID（半角数値のみ）",
        "placeholder_chat_message": "例: 機械学習に関するデモはありますか？",
        
        # Section headers
        "header_demo_list": "## デモ一覧",
        "header_new_registration": "## 新規デモ登録",
        "header_update_info": "## デモ情報更新",
        "header_ai_chat": "## AIチャットボットによるデモ検索（Powered by Agent Bricks）",
        
        # Instructions and descriptions
        "instruction_table_click": "**使い方**: テーブルの行をクリックすると、そのデモの詳細情報が下に表示されます。",
        "instruction_demo_questions": "デモに関する質問をしてください。AIが関連するデモを見つけてお答えします。",
        "default_demo_details": "<p>テーブルの行をクリックすると詳細が表示されます。</p>",
        
        # Main title and messages
        "main_title": "🚀 AI Demo Hub - 社内AIデモ共有サイト [📚 操作方法](https://github.com/hiouchiy/ai_demo_hub/blob/main/USER_GUIDE.md)",
        "greeting_morning": "おはようございます",
        "greeting_afternoon": "こんにちは", 
        "greeting_evening": "こんばんは",
        "greeting_night": "お疲れ様です",
        
        # Status options
        "status_draft": "draft",
        "status_in_review": "in_review", 
        "status_published": "published",
        "status_archived": "archived",
        
        # Confidentiality levels
        "confidentiality_public": "public",
        "confidentiality_internal": "internal",
        
        # Table headers
        "table_demo_id": "デモID",
        "table_title": "タイトル",
        "table_summary": "要約",
        "table_creator": "デモ作成者",
        "table_owner": "代表投稿者",
        "table_updated": "更新日時",
        "table_status": "ステータス",
        "table_demo_url": "デモURL",
        "table_repo_url": "リポジトリURL",
        "table_products": "利用製品",
        "table_confidentiality": "機密性",
        "table_remarks": "備考",
    },
    
    "en": {
        # Tab names
        "tab_demo_list": "📋 Demo List",
        "tab_new_registration": "➕ New Registration",
        "tab_update_info": "✏️ Update Info",
        "tab_ask_bot": "🤖 Ask Bot",
        
        # Button labels
        "btn_refresh": "🔄 Refresh",
        "btn_previous": "« Previous",
        "btn_next": "Next »",
        "btn_ai_generate": "🤖 AI Auto-Generate",
        "btn_ai_polish": "🤖 AI Polish",
        "btn_register": "Register",
        "btn_search": "Search",
        "btn_update": "Update",
        "btn_delete": "Delete",
        "btn_cancel": "Cancel",
        "btn_send": "Send",
        "btn_clear_chat": "Clear Chat History",
        "btn_language": "Language",
        
        # Field labels
        "label_page": "Page",
        "label_demo_details": "Demo Details",
        "label_title_required": "Title *",
        "label_summary": "Summary",
        "label_description_required": "Detailed Description (Markdown supported) *",
        "label_owner_email_required": "Representative Poster Email *",
        "label_creator_email": "Demo Creator Email",
        "label_status_required": "Status *",
        "label_demo_url_required": "Demo URL *",
        "label_repo_url": "Repository URL",
        "label_products": "Products Used",
        "label_confidentiality": "Confidentiality Level",
        "label_remarks": "Remarks",
        "label_demo_id": "Demo ID",
        "label_message": "Message (Press Shift+Enter to send)",
        
        # Placeholders
        "placeholder_demo_title": "Demo title",
        "placeholder_card_summary": "Summary for card display",
        "placeholder_description_md": "Detailed description in Markdown format",
        "placeholder_creator_email": "Email of the demo creator (leave blank if unknown)",
        "placeholder_demo_url": "https://example.com/demo",
        "placeholder_repo_url": "https://github.com/user/repo",
        "placeholder_products": "Product names separated by commas (e.g., Databricks, MLflow, Delta Lake)",
        "placeholder_remarks": "Additional remarks if any",
        "placeholder_demo_id_update": "Demo ID to update (half-width numbers only)",
        "placeholder_chat_message": "e.g., Are there any machine learning demos?",
        
        # Section headers
        "header_demo_list": "## Demo List",
        "header_new_registration": "## New Demo Registration",
        "header_update_info": "## Demo Information Update",
        "header_ai_chat": "## AI Chatbot Demo Search (Powered by Agent Bricks)",
        
        # Instructions and descriptions
        "instruction_table_click": "**How to use**: Click on a table row to display detailed information below.",
        "instruction_demo_questions": "Please ask questions about demos. AI will find relevant demos and answer.",
        "default_demo_details": "<p>Click on a table row to display details.</p>",
        
        # Main title and messages
        "main_title": "🚀 AI Demo Hub - Internal AI Demo Sharing Site [📚 User Guide](https://github.com/hiouchiy/ai_demo_hub/blob/main/USER_GUIDE.md)",
        "greeting_morning": "Good morning",
        "greeting_afternoon": "Good afternoon", 
        "greeting_evening": "Good evening",
        "greeting_night": "Good work today",
        
        # Status options
        "status_draft": "draft",
        "status_in_review": "in_review",
        "status_published": "published", 
        "status_archived": "archived",
        
        # Confidentiality levels
        "confidentiality_public": "public",
        "confidentiality_internal": "internal",
        
        # Table headers
        "table_demo_id": "Demo ID",
        "table_title": "Title",
        "table_summary": "Summary",
        "table_creator": "Demo Creator",
        "table_owner": "Representative Poster", 
        "table_updated": "Updated",
        "table_status": "Status",
        "table_demo_url": "Demo URL",
        "table_repo_url": "Repository URL",
        "table_products": "Products Used",
        "table_confidentiality": "Confidentiality",
        "table_remarks": "Remarks",
    }
}

def get_text(key: str, lang: str = "ja") -> str:
    """Get translated text by key and language"""
    return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["ja"].get(key, key))

def rename_table_columns(df, language: str):
    """Rename DataFrame columns based on language without reloading data"""
    if df.empty:
        # For empty DataFrame, create with proper column names for the target language
        column_order = [
            get_text("table_demo_id", language),
            get_text("table_title", language),
            get_text("table_summary", language),
            get_text("table_creator", language),
            get_text("table_owner", language),
            get_text("table_updated", language),
            get_text("table_status", language),
            get_text("table_demo_url", language),
            get_text("table_repo_url", language),
            get_text("table_products", language),
            get_text("table_confidentiality", language),
            get_text("table_remarks", language)
        ]
        return pd.DataFrame(columns=column_order)
    
    # Create mapping from current columns to new language columns
    # We need to map both directions since we don't know the current language
    ja_to_en = {
        "デモID": "Demo ID",
        "タイトル": "Title",
        "要約": "Summary", 
        "デモ作成者": "Demo Creator",
        "代表投稿者": "Representative Poster",
        "更新日時": "Updated",
        "ステータス": "Status",
        "デモURL": "Demo URL",
        "リポジトリURL": "Repository URL",
        "利用製品": "Products Used",
        "機密性": "Confidentiality",
        "備考": "Remarks"
    }
    
    en_to_ja = {v: k for k, v in ja_to_en.items()}
    
    # Determine current language and target mapping
    current_columns = list(df.columns)
    
    if language == "en":
        # Convert to English
        column_mapping = ja_to_en
    else:
        # Convert to Japanese
        column_mapping = en_to_ja
    
    # Apply mapping
    new_columns = []
    for col in current_columns:
        new_columns.append(column_mapping.get(col, col))
    
    # Create new DataFrame with renamed columns
    new_df = df.copy()
    new_df.columns = new_columns
    
    return new_df

def switch_language(language: str):
    """Switch interface language and return updated content"""
    # Update section headers
    demo_list_header = get_text("header_demo_list", language)
    new_reg_header = get_text("header_new_registration", language)
    update_header = get_text("header_update_info", language)
    ai_chat_header = get_text("header_ai_chat", language)
    
    # Update instructions
    table_instruction = get_text("instruction_table_click", language)
    demo_questions_instruction = get_text("instruction_demo_questions", language)
    default_details = get_text("default_demo_details", language)
    
    # Update field labels for registration form
    reg_title_update = gr.update(label=get_text("label_title_required", language), placeholder=get_text("placeholder_demo_title", language))
    reg_summary_update = gr.update(label=get_text("label_summary", language), placeholder=get_text("placeholder_card_summary", language))
    reg_description_update = gr.update(label=get_text("label_description_required", language), placeholder=get_text("placeholder_description_md", language))
    reg_owner_update = gr.update(label=get_text("label_owner_email_required", language))
    reg_creator_update = gr.update(label=get_text("label_creator_email", language), placeholder=get_text("placeholder_creator_email", language))
    reg_status_update = gr.update(label=get_text("label_status_required", language))
    reg_demo_url_update = gr.update(label=get_text("label_demo_url_required", language), placeholder=get_text("placeholder_demo_url", language))
    reg_repo_url_update = gr.update(label=get_text("label_repo_url", language), placeholder=get_text("placeholder_repo_url", language))
    reg_products_update = gr.update(label=get_text("label_products", language), placeholder=get_text("placeholder_products", language))
    reg_confidentiality_update = gr.update(label=get_text("label_confidentiality", language))
    reg_remarks_update = gr.update(label=get_text("label_remarks", language), placeholder=get_text("placeholder_remarks", language))
    
    # Update field labels for update form
    upd_demo_id_update = gr.update(label=get_text("label_demo_id", language), placeholder=get_text("placeholder_demo_id_update", language))
    upd_title_update = gr.update(label=get_text("label_title_required", language), placeholder=get_text("placeholder_demo_title", language))
    upd_summary_update = gr.update(label=get_text("label_summary", language), placeholder=get_text("placeholder_card_summary", language))
    upd_description_update = gr.update(label=get_text("label_description_required", language), placeholder=get_text("placeholder_description_md", language))
    upd_owner_update = gr.update(label=get_text("label_owner_email_required", language))
    upd_creator_update = gr.update(label=get_text("label_creator_email", language), placeholder=get_text("placeholder_creator_email", language))
    upd_status_update = gr.update(label=get_text("label_status_required", language))
    upd_demo_url_update = gr.update(label=get_text("label_demo_url_required", language), placeholder=get_text("placeholder_demo_url", language))
    upd_repo_url_update = gr.update(label=get_text("label_repo_url", language), placeholder=get_text("placeholder_repo_url", language))
    upd_products_update = gr.update(label=get_text("label_products", language), placeholder=get_text("placeholder_products", language))
    upd_confidentiality_update = gr.update(label=get_text("label_confidentiality", language))
    upd_remarks_update = gr.update(label=get_text("label_remarks", language), placeholder=get_text("placeholder_remarks", language))
    
    # Update button labels
    btn_refresh_update = gr.update(value=get_text("btn_refresh", language))
    btn_prev_update = gr.update(value=get_text("btn_previous", language))
    btn_next_update = gr.update(value=get_text("btn_next", language))
    btn_ai_generate_update = gr.update(value=get_text("btn_ai_generate", language))
    btn_ai_summary_update = gr.update(value=get_text("btn_ai_generate", language))
    btn_ai_polish_update = gr.update(value=get_text("btn_ai_polish", language))
    btn_register_update = gr.update(value=get_text("btn_register", language))
    btn_search_update = gr.update(value=get_text("btn_search", language))
    btn_update_update = gr.update(value=get_text("btn_update", language))
    btn_delete_update = gr.update(value=get_text("btn_delete", language))
    btn_cancel_update = gr.update(value=get_text("btn_cancel", language))
    btn_send_update = gr.update(value=get_text("btn_send", language))
    btn_clear_chat_update = gr.update(value=get_text("btn_clear_chat", language))
    
    # Update other UI elements
    page_input_update = gr.update(label=get_text("label_page", language))
    demo_details_update = gr.update(label=get_text("label_demo_details", language), value=default_details)
    
    # Update main title with Markdown header formatting
    main_title_update = f"# {get_text('main_title', language)}"
    
    # Greeting message will be updated separately via .then() to include user name
    
    # Update chat message input
    chat_msg_update = gr.update(label=get_text("label_message", language), placeholder=get_text("placeholder_chat_message", language))
    
    # Note: Table data update will be handled separately to avoid unnecessary database queries
    # Only column names need to be updated, not the data itself
    
    # Update tab labels (experimental - may not work in all Gradio versions)
    tab_demo_list_update = gr.update(label=get_text("tab_demo_list", language))
    tab_new_reg_update = gr.update(label=get_text("tab_new_registration", language))
    tab_update_update = gr.update(label=get_text("tab_update_info", language))
    tab_chat_update = gr.update(label=get_text("tab_ask_bot", language))
    
    # Return all updated components
    return (
        language,  # language_state
        demo_list_header,  # demo_list_header
        table_instruction,  # table_instruction
        default_details,  # demo_details value
        new_reg_header,  # reg_header
        update_header,  # upd_header
        ai_chat_header,  # chat_header
        demo_questions_instruction,  # chat_instruction
        # Registration form updates
        reg_title_update, reg_summary_update, reg_description_update, reg_owner_update, reg_creator_update,
        reg_status_update, reg_demo_url_update, reg_repo_url_update, reg_products_update, 
        reg_confidentiality_update, reg_remarks_update,
        # Update form updates  
        upd_demo_id_update, upd_title_update, upd_summary_update, upd_description_update, upd_owner_update, upd_creator_update,
        upd_status_update, upd_demo_url_update, upd_repo_url_update, upd_products_update,
        upd_confidentiality_update, upd_remarks_update,
        # Button updates
        btn_refresh_update, btn_prev_update, btn_next_update, btn_ai_generate_update, btn_ai_summary_update, btn_ai_polish_update,
        btn_register_update, btn_search_update, btn_update_update, btn_delete_update, btn_cancel_update,
        btn_send_update, btn_clear_chat_update,
        # Other UI updates
        page_input_update, demo_details_update,
        # New UI updates
        main_title_update, chat_msg_update,
        # Tab label updates
        tab_demo_list_update, tab_new_reg_update, tab_update_update, tab_chat_update
    )

def get_current_user_email(request: gr.Request) -> str:
    """Get current user's email from request headers"""
    try:
        # Try different header names for email
        email = request.headers.get("x-forwarded-email")
        if not email:
            email = request.headers.get("x-forwarded-user")
        if not email:
            email = request.headers.get("x-forwarded-preferred-username")
        
        # If no email found, use default for local testing
        if not email:
            email = "unknown@databricks.com"
            
        return email
    except Exception as e:
        print(f"Warning: Failed to get user email: {str(e)}")
        return "unknown@databricks.com"

def get_greeting_message(request: gr.Request, language: str = "ja") -> str:
    """Generate greeting message based on current time and user"""
    from datetime import datetime
    
    try:
        # Get user email
        email = get_current_user_email(request)
        
        # Extract name from email (e.g., "john.smith@databricks.com" -> "John Smith")
        username = email.split('@')[0]
        if '.' in username:
            first_name, last_name = username.split('.', 1)
            display_name = f"{first_name.title()} {last_name.title()}"
        else:
            display_name = username.title()
        
        # Get current time in JST
        current_time = datetime.now(JST)
        hour = current_time.hour
        
        # Determine greeting based on time
        if 5 <= hour < 12:
            greeting = get_text("greeting_morning", language)
            emoji = "🌅"
        elif 12 <= hour < 18:
            greeting = get_text("greeting_afternoon", language)
            emoji = "☀️"
        elif 18 <= hour < 22:
            greeting = get_text("greeting_evening", language)
            emoji = "🌆"
        else:
            greeting = get_text("greeting_night", language)
            emoji = "🌙"
        
        if language == "ja":
            return f"{emoji} {greeting}、{display_name}さん！"
        else:
            return f"{emoji} {greeting}, {display_name}!"
        
    except Exception as e:
        print(f"Warning: Failed to generate greeting: {str(e)}")
        if language == "ja":
            return "👋 こんにちは！"
        else:
            return "👋 Hello!"

def check_ownership_permission(demo_id, current_user_email: str, user_token: str = None) -> Tuple[bool, str, str]:
    """Check if current user has permission to modify/delete the demo
    
    Returns:
        tuple: (has_permission, original_owner_email, message)
    """
    try:
        # Convert number to string if needed
        if demo_id is None or demo_id == "":
            return False, "", "Demo IDが入力されていません。"
        
        demo_id_str = str(int(demo_id)) if isinstance(demo_id, (int, float)) else str(demo_id).strip()
        
        if not demo_id_str:
            return False, "", "Demo IDが入力されていません。"
        
        # Convert to int with error handling
        try:
            demo_id_int = int(float(demo_id_str))
            if demo_id_int <= 0:
                return False, "", "無効なDemo IDです。"
        except (ValueError, TypeError, OverflowError):
            return False, "", "Demo IDの形式が正しくありません。"
        
        # Get demo data from database
        user_db_manager = APIBasedDatabaseManager(user_token)
        demo = user_db_manager.get_demo_by_id(demo_id_int)
        if not demo:
            return False, "", "指定されたデモが見つかりません。"
        
        original_owner = demo.get("owner_emp_id", "")
        
        # Check if current user is the original owner
        if current_user_email == original_owner:
            return True, original_owner, "権限があります。"
        else:
            return False, original_owner, f"権限がありません。このデモの投稿者は {original_owner} です。"
            
    except Exception as e:
        return False, "", f"権限チェック中にエラーが発生しました: {str(e)}"

def get_service_principal_token() -> str:
    """Get Service Principal OAuth token for database operations"""
    try:
        client_id = os.getenv('DATABRICKS_CLIENT_ID', '').strip()
        client_secret = os.getenv('DATABRICKS_CLIENT_SECRET', '').strip()
        databricks_host = os.getenv('DATABRICKS_HOST')
        
        if not all([client_id, client_secret, databricks_host]):
            missing = []
            if not client_id: missing.append("CLIENT_ID")
            if not client_secret: missing.append("CLIENT_SECRET") 
            if not databricks_host: missing.append("DATABRICKS_HOST")
            raise ValueError(f"Service Principal credentials missing: {', '.join(missing)}")
        
        # Ensure https:// scheme is present
        if not databricks_host.startswith('https://') and not databricks_host.startswith('http://'):
            databricks_host = f"https://{databricks_host}"
        
        token_url = f"{databricks_host}/oidc/v1/token"
        
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials", "scope": "all-apis"},
            timeout=30
        )
        
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data["access_token"]
        return access_token
    except Exception as e:
        raise

def test_token_permissions(token: str) -> bool:
    """Test if a token has SQL Warehouse access permissions"""
    try:
        from api_database_manager import APIBasedDatabaseManager
        test_manager = APIBasedDatabaseManager(token)
        # Simple test query to check permissions
        result = test_manager.execute_query_api("SELECT 1 as test_permission")
        return len(result) > 0  # If we get any result, permissions are OK
    except Exception as e:
        return False

def get_user_access_token(request: gr.Request) -> str:
    """Get access token for database operations with fallback priority:
    1. User token from headers (x-forwarded-access-token) - test permissions first
    2. Service Principal token (OAuth environment)
    3. System token (PAT environment)
    """
    # Check if running in OAuth environment
    client_id = os.getenv('DATABRICKS_CLIENT_ID', '').strip()
    client_secret = os.getenv('DATABRICKS_CLIENT_SECRET', '').strip()
    use_oauth = bool(client_id and client_secret)
    
    # Try different possible header names for user token
    possible_headers = [
        "x-forwarded-access-token",
        "X-Forwarded-Access-Token", 
        "authorization",
        "Authorization"
    ]
    
    user_token = None
    for header_name in possible_headers:
        user_token = request.headers.get(header_name)
        if user_token:
            # Test if user token has SQL Warehouse permissions
            if test_token_permissions(user_token):
                return user_token
            else:
                if use_oauth:
                    break  # Fall through to Service Principal logic
                else:
                    return DATABRICKS_TOKEN or ""
    
    if use_oauth:
        # Priority 2: Service Principal token in OAuth environment
        try:
            service_token = get_service_principal_token()
            # Test Service Principal token permissions as well
            if test_token_permissions(service_token):
                return service_token
            else:
                return ""
                
        except Exception as e:
            return ""
    else:
        # Priority 3: System token for local testing
        return DATABRICKS_TOKEN or ""

class DatabaseManager:
    """Database connection and operations manager"""
    
    def __init__(self, user_token: str = None):
        self.server_hostname = DATABRICKS_SERVER_HOSTNAME
        self.http_path = f"/sql/1.0/warehouses/{DATABRICKS_WAREHOUSE_ID}"
        self.access_token = user_token or DATABRICKS_TOKEN
        
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
        # Check if running in Databricks Apps environment
        self.client_id = os.getenv('DATABRICKS_CLIENT_ID', '').strip()
        self.client_secret = os.getenv('DATABRICKS_CLIENT_SECRET', '').strip()
        self.pat_token = DATABRICKS_TOKEN
        
        # Determine authentication method - both client_id and client_secret must be non-empty
        self.use_oauth = bool(self.client_id and self.client_secret)
        
        # OAuth or PAT authentication is determined by use_oauth flag
    
    def get_oauth_token(self):
        """Get OAuth access token for Service Principal authentication"""
        try:
            # Get host directly from environment variable to avoid Config conflicts
            databricks_host = os.getenv('DATABRICKS_HOST')
            if not databricks_host:
                raise ValueError("DATABRICKS_HOST environment variable is required for OAuth authentication")
            
            # Ensure https:// scheme is present
            if not databricks_host.startswith('https://') and not databricks_host.startswith('http://'):
                databricks_host = f"https://{databricks_host}"
            
            token_url = f"{databricks_host}/oidc/v1/token"
            
            response = requests.post(
                token_url,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials", "scope": "all-apis"},
                timeout=30
            )
                
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data["access_token"]
            return access_token
            
        except Exception as e:
            raise
        
    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Send chat completion request to RAG system"""
        if not self.endpoint:
            return "RAG_ENDPOINTが設定されていません。環境変数を確認してください。"
            
        # Get authentication token based on environment
        try:
            if self.use_oauth:
                # Use OAuth Service Principal authentication for production
                token = self.get_oauth_token()
            else:
                # Use PAT token for local development
                if not self.pat_token:
                    return "DATABRICKS_TOKENが設定されていません。環境変数を確認してください。"
                token = self.pat_token
        except Exception as e:
            return f"認証エラーが発生しました: {str(e)}"
            
        # Convert messages to the expected input format
        # RAG endpoint expects messages array in the input field with system message
        input_messages = [
            {"role": "system", "content": "You are a helpful agent that assists users with finding information about AI demos. Please respond in Japanese."}
        ]
        
        # Add the original messages to the input
        input_messages.extend(messages)
        
        data = {
            "input": input_messages
        }
        
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(
                url=self.endpoint, 
                json=data, 
                headers=headers
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if "output" in result and len(result["output"]) > 0:
                # RAG Agent response format: output[0].content[0].text
                output_item = result["output"][0]
                if "content" in output_item and len(output_item["content"]) > 0:
                    content_item = output_item["content"][0]
                    if "text" in content_item:
                        return content_item["text"]
                    else:
                        print(f"   No 'text' field in content item: {content_item}")
                        return str(content_item)
                else:
                    print(f"   No 'content' field in output item: {output_item}")
                    return str(output_item)
            elif "choices" in result and len(result["choices"]) > 0:
                # OpenAI-style response format
                return result["choices"][0]["message"]["content"]
            elif "predictions" in result and len(result["predictions"]) > 0:
                # Databricks serving endpoint format
                prediction = result["predictions"][0]
                if isinstance(prediction, dict) and "content" in prediction:
                    return prediction["content"]
                elif isinstance(prediction, str):
                    return prediction
                else:
                    return str(prediction)
            elif "result" in result:
                # Result format
                return str(result["result"])
            else:
                # Fallback: return the entire result as string
                print(f"   Unknown response format, returning full result")
                return str(result)
        except Exception as e:
            print(f"   RAG Error: {str(e)}")
            return f"エラーが発生しました: {str(e)}"

class TitleGenerator:
    """AI-powered title generation using Databricks Claude model"""
    
    def __init__(self):
        try:
            # Get authentication variables
            databricks_host = os.getenv('DATABRICKS_HOST')
            databricks_token = os.getenv('DATABRICKS_TOKEN')
            client_id = os.getenv('DATABRICKS_CLIENT_ID', '').strip()
            client_secret = os.getenv('DATABRICKS_CLIENT_SECRET', '').strip()
            
            if not databricks_host:
                raise ValueError("DATABRICKS_HOST environment variable is required")
            
            # Determine authentication method - both client_id and client_secret must be non-empty
            use_oauth = bool(client_id and client_secret)
            
            if use_oauth:
                # Use OAuth Service Principal authentication for production
                self.client = WorkspaceClient(
                    host=databricks_host,
                    client_id=client_id,
                    client_secret=client_secret,
                    auth_type="oauth-m2m"  # M2M OAuth を明示
                )
            else:
                # Use PAT token for local development
                if not databricks_token:
                    raise ValueError("DATABRICKS_TOKEN environment variable is required for PAT authentication")
                self.client = WorkspaceClient(
                    host=databricks_host,
                    token=databricks_token,
                    auth_type="pat"
                )
                
            self.openai_client = self.client.serving_endpoints.get_open_ai_client()
            
        except Exception as e:
            print(f"Warning: Failed to initialize TitleGenerator: {str(e)}")
            self.openai_client = None
    
    def generate_title(self, description: str) -> str:
        """Generate a catchy title from demo description"""
        if not self.openai_client:
            return "Error: LLM client not initialized"
        
        if not description or description.strip() == "":
            return ""
        
        system_prompt = """あなたは魅力的で簡潔なタイトルを作成する専門家です。
以下の詳細説明を読んで、キャッチーで興味を引く日本語のタイトルを1つ生成してください。

ルール:
- 20文字以内で簡潔に
- 技術的な内容を一般の人にも伝わりやすく
- 興味を引く表現を使用
- 「〜について」「〜の話」などの余計な言葉は避ける
- タイトルのみを出力（説明文不要）"""

        try:
            response = self.openai_client.chat.completions.create(
                model="databricks-claude-3-7-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"以下の詳細説明からキャッチーなタイトルを生成してください:\n\n{description}",
                    }
                ],
                max_tokens=256
            )
            
            generated_title = response.choices[0].message.content.strip()
            return generated_title
            
        except Exception as e:
            print(f"Title generation error: {str(e)}")
            return f"Error: タイトル生成に失敗しました ({str(e)})"
    
    def generate_summary(self, description: str) -> str:
        """Generate a concise summary from demo description"""
        if not self.openai_client:
            return "Error: LLM client not initialized"
        
        if not description or description.strip() == "":
            return ""
        
        system_prompt = """あなたは技術的内容を分かりやすく要約する専門家です。
以下の詳細説明を読んで、簡潔で分かりやすい要約を1つ生成してください。

ルール:
- 50-80文字程度で簡潔に
- 技術的な専門用語を使いながらも理解しやすく
- デモの核心となる価値・機能を伝える
- 「このデモは」「これは」などの冗長な表現は避ける
- 要約文のみを出力（説明文不要）"""

        try:
            response = self.openai_client.chat.completions.create(
                model="databricks-claude-3-7-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"以下の詳細説明から簡潔な要約を生成してください:\n\n{description}",
                    }
                ],
                max_tokens=256
            )
            
            generated_summary = response.choices[0].message.content.strip()
            return generated_summary
            
        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            return f"Error: 要約生成に失敗しました ({str(e)})"
    
    def polish_description(self, rough_description: str) -> str:
        """Polish rough description into professional, detailed content"""
        if not self.openai_client:
            return "Error: LLM client not initialized"
        
        if not rough_description or rough_description.strip() == "":
            return ""
        
        system_prompt = """あなたは技術文書の編集とライティングの専門家です。
ユーザーが入力したラフな下書きやメモ書きを、プロフェッショナルで分かりやすい詳細説明に書き直してください。

ルール:
- 元の内容の意図を正確に保持する
- 技術的な正確性を維持しながら、より詳細で具体的に
- プロフェッショナルで読みやすい文体に統一
- Markdown記法は使用しないで、プレーンなテキストで記載する
- 構造化された説明（必要に応じて見出しやリスト使用）
- 専門用語は適切に使用しつつ、理解しやすい説明を併記
- 曖昧な表現を具体的で明確な表現に改善"""

        try:
            response = self.openai_client.chat.completions.create(
                model="databricks-claude-3-7-sonnet",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"以下のラフな説明をプロフェッショナルで詳細な技術説明に書き直してください:\n\n{rough_description}",
                    }
                ],
                max_tokens=1024
            )
            
            polished_description = response.choices[0].message.content.strip()
            return polished_description
            
        except Exception as e:
            print(f"Description polishing error: {str(e)}")
            return f"Error: 清書に失敗しました ({str(e)})"

# Global instances
# APIベースのDatabaseManagerを使用してsqlクライアントの問題を回避
from api_database_manager import APIBasedDatabaseManager
db_manager = APIBasedDatabaseManager()
rag_client = RAGClient()
title_generator = TitleGenerator()

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
def load_demo_list(page: int = 1, language: str = "ja", request: gr.Request = None):
    """Load demo list with pagination and sorting"""
    try:
        # Validate inputs with proper type checking
        if page is None or not isinstance(page, (int, float)):
            page = 1
        else:
            page = int(page)
            
        # Get user token and create database manager
        user_token = get_user_access_token(request) if request else None
        user_db_manager = APIBasedDatabaseManager(user_token)
        
        # Use default sorting by created_at DESC (newest first)
        demos, total_count = user_db_manager.get_demos(page, "created_at", "DESC")
        
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
                    get_text("table_demo_id", language): demo_id,
                    get_text("table_title", language): demo.get("title") or "",
                    get_text("table_summary", language): demo.get("summary") or "",
                    get_text("table_owner", language): demo.get("owner_emp_id") or "",
                    get_text("table_creator", language): demo.get("creator_emp_id") or "",
                    get_text("table_updated", language): format_datetime(demo.get("updated_at")),
                    get_text("table_status", language): demo.get("status") or "",
                    get_text("table_demo_url", language): demo.get("demo_url") or "",
                    get_text("table_repo_url", language): demo.get("repo_url") or "",
                    get_text("table_products", language): products_str,
                    get_text("table_confidentiality", language): demo.get("confidentiality") or "",
                    get_text("table_remarks", language): demo.get("remarks") or ""
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
        
        # Define column order with creator_emp_id before owner_emp_id
        column_order = [
            get_text("table_demo_id", language),
            get_text("table_title", language),
            get_text("table_summary", language),
            get_text("table_creator", language),
            get_text("table_owner", language),
            get_text("table_updated", language),
            get_text("table_status", language),
            get_text("table_demo_url", language),
            get_text("table_repo_url", language),
            get_text("table_products", language),
            get_text("table_confidentiality", language),
            get_text("table_remarks", language)
        ]
        
        # Handle empty data case properly
        if formatted_demos:
            df = pd.DataFrame(formatted_demos)[column_order]
        else:
            # Create empty DataFrame with proper column names for empty data
            df = pd.DataFrame(columns=column_order)
        
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
        # Create empty DataFrame with proper column names for error case
        column_order = [
            get_text("table_demo_id", language),
            get_text("table_title", language),
            get_text("table_summary", language),
            get_text("table_creator", language),
            get_text("table_owner", language),
            get_text("table_updated", language),
            get_text("table_status", language),
            get_text("table_demo_url", language),
            get_text("table_repo_url", language),
            get_text("table_products", language),
            get_text("table_confidentiality", language),
            get_text("table_remarks", language)
        ]
        return pd.DataFrame(columns=column_order), error_msg, 1, 1, False, False

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
        demo_id = demo.get("デモID")
        
        if not demo_id:
            return "Demo IDが見つかりません。"
        
        # Check if we already have this demo's details cached
        if demo_id == last_displayed_demo_id and last_displayed_demo_html:
            # Return cached result to avoid unnecessary database query
            return last_displayed_demo_html
        
        # Get demo with all_info_md using internal function
        # Use Service Principal token for read-only operations in event handlers
        try:
            # Try to get Service Principal token for OAuth environment
            client_id = os.getenv('DATABRICKS_CLIENT_ID', '').strip()
            client_secret = os.getenv('DATABRICKS_CLIENT_SECRET', '').strip()
            use_oauth = bool(client_id and client_secret)
            
            if use_oauth:
                service_token = get_service_principal_token()
                fallback_db_manager = APIBasedDatabaseManager(service_token)
            else:
                # Use system token for local development
                fallback_db_manager = APIBasedDatabaseManager()
        except Exception as e:
            # Fallback to system token
            fallback_db_manager = APIBasedDatabaseManager()
            
        demo_full = fallback_db_manager.get_demo_by_id_internal(demo_id)
        
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

# AI Title Generation
def generate_title_from_description(description: str) -> str:
    """Generate catchy title from demo description using AI"""
    try:
        if not description or description.strip() == "":
            return "詳細説明を入力してからタイトル生成ボタンを押してください。"
        
        generated_title = title_generator.generate_title(description)
        
        if generated_title.startswith("Error:"):
            return generated_title
        elif generated_title == "":
            return "詳細説明を入力してからタイトル生成ボタンを押してください。"
        else:
            return generated_title
            
    except Exception as e:
        return f"Error: タイトル生成に失敗しました ({str(e)})"

# AI Summary Generation
def generate_summary_from_description(description: str) -> str:
    """Generate concise summary from demo description using AI"""
    try:
        if not description or description.strip() == "":
            return "詳細説明を入力してから要約生成ボタンを押してください。"
        
        generated_summary = title_generator.generate_summary(description)
        
        if generated_summary.startswith("Error:"):
            return generated_summary
        elif generated_summary == "":
            return "詳細説明を入力してから要約生成ボタンを押してください。"
        else:
            return generated_summary
            
    except Exception as e:
        return f"Error: 要約生成に失敗しました ({str(e)})"

# AI Description Polishing
def polish_description_text(rough_description: str) -> str:
    """Polish rough description text using AI"""
    try:
        if not rough_description or rough_description.strip() == "":
            return "詳細説明を入力してから清書ボタンを押してください。"
        
        polished_description = title_generator.polish_description(rough_description)
        
        if polished_description.startswith("Error:"):
            return polished_description
        elif polished_description == "":
            return "詳細説明を入力してから清書ボタンを押してください。"
        else:
            return polished_description
            
    except Exception as e:
        return f"Error: 清書に失敗しました ({str(e)})"

# Tab 2: New Demo Registration
def register_demo(title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, request: gr.Request, progress=gr.Progress()):
    """Register new demo with progress display"""
    try:
        progress(0.1, desc="Validating input...")
        
        # Validation
        if not title or not owner_emp_id or not status or not demo_url:
            return "Error: Required fields (title, owner_emp_id, status, demo_url) cannot be empty.", title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks
        
        if not validate_email(owner_emp_id):
            return "Error: Invalid email format for owner_emp_id.", title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks
        
        # Validate creator_emp_id if provided
        if creator_emp_id and not validate_email(creator_emp_id):
            return "Error: Invalid email format for creator_emp_id.", title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks
        
        progress(0.3, desc="Processing products...")
        
        products = parse_products(products_str)
        
        progress(0.5, desc="Preparing data...")
        
        # Ensure all fields have safe default values
        data = {
            "title": title or "",
            "summary": summary or "",
            "description_md": description_md or "",
            "owner_emp_id": owner_emp_id or "",
            "creator_emp_id": creator_emp_id or "",
            "status": status or "draft",
            "demo_url": demo_url or "",
            "repo_url": repo_url or "",
            "products": products or [],
            "confidentiality": confidentiality or "internal",
            "remarks": remarks or ""
        }
        
        progress(0.8, desc="Registering demo...")
        
        # Get user token and create database manager
        user_token = get_user_access_token(request)
        user_db_manager = APIBasedDatabaseManager(user_token)
        
        demo_id = user_db_manager.insert_demo(data)
        
        progress(1.0, desc="Registration completed!")
        
        # Handle the case where demo_id might be None or 0
        if demo_id and demo_id > 0:
            # Clear all fields after successful registration, but keep owner_emp_id for consecutive registrations
            return f"Success: Demo registered with ID {demo_id}", "", "", "", owner_emp_id, "", "draft", "", "", "", "internal", ""
        else:
            # Clear all fields after successful registration, but keep owner_emp_id for consecutive registrations
            return "Success: Demo registered successfully", "", "", "", owner_emp_id, "", "draft", "", "", "", "internal", ""
        
    except Exception as e:
        return f"Error: {str(e)}", title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks

# Tab 3: Demo Update
def search_demo_for_update(demo_id, request: gr.Request):
    """Search demo by ID for update"""
    try:
        # Convert number to string if needed
        if demo_id is None or demo_id == "":
            return "", "", "", "", "", "", "", "", "", "", "", "デモIDを入力してください。"
        
        demo_id_str = str(int(demo_id)) if isinstance(demo_id, (int, float)) else str(demo_id).strip()
        
        if not demo_id_str:
            return "", "", "", "", "", "", "", "", "", "", "", "デモIDを入力してください。"
        
        # Convert to int with better error handling
        try:
            demo_id_int = int(float(demo_id_str))
            if demo_id_int <= 0:
                return "", "", "", "", "", "", "", "", "", "", "", "デモIDは正の数値である必要があります。"
        except (ValueError, TypeError, OverflowError):
            return "", "", "", "", "", "", "", "", "", "", "", "無効なデモID形式です。正の数値を入力してください。"
        
        # Get user access token for database operations
        user_token = get_user_access_token(request)
        user_db_manager = APIBasedDatabaseManager(user_token)
        demo = user_db_manager.get_demo_by_id(demo_id_int)
        
        if not demo:
            return "", "", "", "", "", "", "", "", "", "", "", "Demo not found."
        
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
            demo.get("creator_emp_id", "") or "",
            demo["status"],
            demo["demo_url"],
            demo["repo_url"] or "",
            products_str,
            demo["confidentiality"] or "",
            demo["remarks"] or "",
            f"Demo found: {demo['title']}"
        )
        
    except ValueError:
        return "", "", "", "", "", "", "", "", "", "", "", "Invalid demo ID format."
    except Exception as e:
        return "", "", "", "", "", "", "", "", "", "", "", f"Error: {str(e)}"

def check_update_permission_or_execute(demo_id: str, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, request: gr.Request):
    """Check permission before update or show confirmation"""
    current_user_email = get_current_user_email(request)
    user_token = get_user_access_token(request)
    has_permission, original_owner, message = check_ownership_permission(demo_id, current_user_email, user_token)
    
    if has_permission:
        # Direct execution - user owns the demo
        return update_demo(demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, request) + (gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False))
    else:
        # Show confirmation area
        confirmation_msg = f"""
### ⚠️ 権限確認

あなた（**{current_user_email}**）は、このデモの投稿者（**{original_owner}**）ではありません。

それでも更新を実行しますか？

**注意**: 他の人が投稿したデモを変更することは、通常推奨されません。
        """
        # Return current state + show confirmation area  
        safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
        return ("", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "", gr.update(visible=True), confirmation_msg, gr.update(value="確認して更新実行", visible=True), gr.update(visible=False))

def check_delete_permission_or_execute(demo_id: str, request: gr.Request):
    """Check permission before delete or show confirmation"""
    current_user_email = get_current_user_email(request)
    user_token = get_user_access_token(request)
    has_permission, original_owner, message = check_ownership_permission(demo_id, current_user_email, user_token)
    
    if has_permission:
        # Direct execution - user owns the demo
        return delete_demo(demo_id, request) + (gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False))
    else:
        # Show confirmation area
        confirmation_msg = f"""
### ⚠️ 削除権限確認

あなた（**{current_user_email}**）は、このデモの投稿者（**{original_owner}**）ではありません。

それでも削除を実行しますか？

**⚠️ 重要**: 他の人が投稿したデモを削除することは非常に慎重に行ってください。
削除したデータは復元できません。
        """
        # Return current state + show confirmation area
        safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
        return ("", safe_demo_id, "", "", "", "", "", "draft", "", "", "", "internal", "", "", gr.update(visible=True), confirmation_msg, gr.update(visible=False), gr.update(value="確認して削除実行", visible=True))

def update_demo(demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, request: gr.Request, progress=gr.Progress()):
    """Update existing demo with progress display"""
    try:
        progress(0.1, desc="Validating input...")
        
        # Convert number to string if needed
        if demo_id is None or demo_id == "":
            return "Error: デモを検索してください。", None, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "デモを検索してください。"
        
        demo_id_str = str(int(demo_id)) if isinstance(demo_id, (int, float)) else str(demo_id).strip()
        
        if not demo_id_str:
            return "Error: デモを検索してください。", None, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "デモを検索してください。"
        
        # Validation
        if not title or not owner_emp_id or not status or not demo_url:
            safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
            return "Error: Required fields (title, owner_emp_id, status, demo_url) cannot be empty.", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Required fields cannot be empty."
        
        if not validate_email(owner_emp_id):
            safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
            return "Error: Invalid email format for owner_emp_id.", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid email format."
        
        # Validate creator_emp_id if provided
        if creator_emp_id and not validate_email(creator_emp_id):
            safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
            return "Error: Invalid email format for creator_emp_id.", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid email format."
        
        progress(0.3, desc="Processing demo ID...")
        
        # Convert to int with better error handling
        try:
            demo_id_int = int(float(demo_id_str))
            if demo_id_int <= 0:
                safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
                return "Error: デモIDは正の数値である必要があります。", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "無効なデモIDです。"
        except (ValueError, TypeError, OverflowError):
            safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
            return "Error: 無効なデモID形式です。", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "無効なデモID形式です。"
        
        progress(0.5, desc="Preparing data...")
        
        products = parse_products(products_str)
        
        data = {
            "title": title,
            "summary": summary,
            "description_md": description_md,
            "owner_emp_id": owner_emp_id,
            "creator_emp_id": creator_emp_id,
            "status": status,
            "demo_url": demo_url,
            "repo_url": repo_url,
            "products": products,
            "confidentiality": confidentiality,
            "remarks": remarks
        }
        
        progress(0.8, desc="Updating demo...")
        
        # Get user token and create database manager
        user_token = get_user_access_token(request)
        user_db_manager = APIBasedDatabaseManager(user_token)
        
        user_db_manager.update_demo(demo_id_int, data)
        
        progress(1.0, desc="Update completed!")
        
        # Clear all fields on successful update
        return "Success: Demo updated successfully.", None, "", "", "", "", "", "draft", "", "", "", "internal", "", ""
        
    except ValueError:
        # Ensure demo_id is numeric or None for gr.Number component
        safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
        return "Error: Invalid demo ID format.", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, "Invalid demo ID format."
    except Exception as e:
        # Ensure demo_id is numeric or None for gr.Number component
        safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
        return f"Error: {str(e)}", safe_demo_id, title, summary, description_md, owner_emp_id, creator_emp_id, status, demo_url, repo_url, products_str, confidentiality, remarks, f"Error: {str(e)}"

def delete_demo(demo_id, request: gr.Request, progress=gr.Progress()):
    """Delete demo by ID with progress display"""
    try:
        progress(0.1, desc="Validating input...")
        
        # Convert number to string if needed
        if demo_id is None or demo_id == "":
            return "Error: デモを検索してください。", None, "", "", "", "", "", "draft", "", "", "", "internal", "", "デモを検索してください。"
        
        demo_id_str = str(int(demo_id)) if isinstance(demo_id, (int, float)) else str(demo_id).strip()
        
        if not demo_id_str:
            return "Error: デモを検索してください。", None, "", "", "", "", "", "draft", "", "", "", "internal", "", "デモを検索してください。"
        
        progress(0.3, desc="Processing demo ID...")
        
        # Convert to int with better error handling
        try:
            demo_id_int = int(float(demo_id_str))
            if demo_id_int <= 0:
                safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
                return "Error: デモIDは正の数値である必要があります。", safe_demo_id, "", "", "", "", "", "draft", "", "", "", "internal", "", "無効なデモIDです。"
        except (ValueError, TypeError, OverflowError):
            safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
            return "Error: 無効なデモID形式です。", safe_demo_id, "", "", "", "", "", "draft", "", "", "", "internal", "", "無効なデモID形式です。"
        
        progress(0.5, desc="Checking demo existence...")
        
        # Get user token and create database manager
        user_token = get_user_access_token(request)
        user_db_manager = APIBasedDatabaseManager(user_token)
        
        # Check if demo exists before deletion
        demo = user_db_manager.get_demo_by_id(demo_id_int)
        if not demo:
            return "Error: Demo not found.", demo_id, "", "", "", "", "", "draft", "", "", "", "internal", "", "Demo not found."
        
        progress(0.8, desc="Deleting demo...")
        
        # Delete the demo
        user_db_manager.delete_demo(demo_id_int)
        
        progress(1.0, desc="Deletion completed!")
        
        # Clear all fields on successful deletion
        return f"Success: Demo ID {demo_id_int} has been deleted successfully.", None, "", "", "", "", "", "draft", "", "", "", "internal", "", ""
        
    except ValueError:
        # Ensure demo_id is numeric or None for gr.Number component
        safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
        return "Error: Invalid demo ID format.", safe_demo_id, "", "", "", "", "", "draft", "", "", "", "internal", "", "Invalid demo ID format."
    except Exception as e:
        # Ensure demo_id is numeric or None for gr.Number component  
        safe_demo_id = None if demo_id == "" or demo_id is None else demo_id
        return f"Error: {str(e)}", safe_demo_id, "", "", "", "", "", "draft", "", "", "", "internal", "", f"Error: {str(e)}"

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
        
        # Convert markdown footnotes to readable format and render as markdown
        response_converted = convert_markdown_footnotes(response)
        response_html = render_markdown(response_converted)
        
        # Replace thinking indicator with actual response
        history[-1] = {"role": "assistant", "content": response_html}
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
        # Language state
        language_state = gr.State(value="ja")
        # User email state for greeting updates
        user_email_state = gr.State(value="")
        
        # Header with language switch
        with gr.Row():
            with gr.Column(scale=8):
                title_display = gr.Markdown(f"# {get_text('main_title', 'ja')}")
            with gr.Column(scale=1, min_width=120):
                language_switch = gr.Dropdown(
                    choices=[("🇯🇵 日本語", "ja"), ("🇺🇸 English", "en")],
                    value="ja",
                    show_label=False,
                    container=True,
                    elem_id="language-switch"
                )
        
        # User greeting area
        greeting_display = gr.Markdown("", elem_id="greeting")
        
        with gr.Tabs() as tabs:
            # Tab 1: Demo List
            with gr.TabItem(get_text("tab_demo_list", "ja")) as demo_list_tab:
                demo_list_header = gr.Markdown("## デモ一覧")
                table_instruction = gr.Markdown("**使い方**: テーブルの行をクリックすると、そのデモの詳細情報が下に表示されます。")
                
                with gr.Row():
                    gr.HTML("")  # Left spacer to push content to the right
                    with gr.Column(scale=1, min_width=200):
                        with gr.Row():
                            page_input = gr.Number(label="ページ", value=1, precision=0, minimum=1, container=False, scale=1)
                            refresh_btn = gr.Button("🔄 最新情報に更新", variant="primary", scale=1)
                
                # Pagination controls
                with gr.Row():
                    prev_btn = gr.Button("« 前へ", size="sm")
                    page_info = gr.Markdown("")
                    next_btn = gr.Button("次へ »", size="sm")
                
                # Hidden states for pagination
                current_page_state = gr.State(value=1)
                total_pages_state = gr.State(value=1)
                
                demo_table = gr.DataFrame(
                    headers=["デモID", "タイトル", "要約", "デモ作成者", "代表投稿者", "更新日時", "ステータス", "デモURL", "リポジトリURL", "利用製品", "機密性", "備考"],
                    interactive=False
                )
                
                demo_details = gr.HTML(label="デモ詳細", value="<p>テーブルの行をクリックすると詳細が表示されます。</p>")
                
                # Event handlers
                def refresh_demo_list(page, request: gr.Request):
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(page, "ja", request)
                    return df, page_info, current_page, total_pages, gr.update(interactive=prev_enabled), gr.update(interactive=next_enabled)
                
                def initial_load_demo_list(request: gr.Request):
                    """Initial load function that works with demo.load"""
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(1, "ja", request)
                    return df, page_info, current_page, total_pages, gr.update(interactive=prev_enabled), gr.update(interactive=next_enabled)
                
                refresh_btn.click(
                    refresh_demo_list,
                    inputs=[page_input],
                    outputs=[demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
                
                # Previous page button
                def go_previous_page(current_page, total_pages, request: gr.Request):
                    new_page = get_previous_page(current_page)
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(new_page, "ja", request)
                    return new_page, df, page_info, current_page, total_pages, gr.update(interactive=prev_enabled), gr.update(interactive=next_enabled)
                
                prev_btn.click(
                    go_previous_page,
                    inputs=[current_page_state, total_pages_state],
                    outputs=[page_input, demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
                
                # Next page button
                def go_next_page(current_page, total_pages, request: gr.Request):
                    new_page = get_next_page(current_page, total_pages)
                    df, page_info, current_page, total_pages, prev_enabled, next_enabled = load_demo_list(new_page, "ja", request)
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
                    initial_load_demo_list,
                    inputs=None,
                    outputs=[demo_table, page_info, current_page_state, total_pages_state, prev_btn, next_btn]
                )
            
            # Tab 2: New Demo Registration
            with gr.TabItem(get_text("tab_new_registration", "ja")) as new_reg_tab:
                reg_header = gr.Markdown("## 新規デモ登録")
                
                with gr.Column():
                    # Title with AI generation button
                    with gr.Row():
                        reg_title = gr.Textbox(label="タイトル *", placeholder="デモのタイトル", scale=6)
                        ai_title_btn = gr.Button("🤖 AIで自動生成", size="sm", min_width=120, variant="secondary")
                    # Summary with AI generation button
                    with gr.Row():
                        reg_summary = gr.Textbox(label="要約", placeholder="カード表示用の要約", scale=6)
                        ai_summary_btn = gr.Button("🤖 AIで自動生成", size="sm", min_width=120, variant="secondary")
                    # Description with AI polishing button
                    with gr.Row():
                        reg_description = gr.Textbox(label="詳細説明 (Markdownも可) *", lines=5, max_lines=10, placeholder="詳細説明をMarkdown形式でも記載可能", scale=6)
                        ai_polish_btn = gr.Button("🤖 AIで自動清書", size="sm", min_width=120, variant="secondary")
                    reg_owner = gr.Textbox(label="代表投稿者メールアドレス *", placeholder="john.smith@databricks.com", interactive=False)
                    reg_creator = gr.Textbox(label="デモ作成者メールアドレス", placeholder="デモを作成した人のメールアドレス（不明の場合は空白でOK）")
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
                    reg_remarks = gr.Textbox(label="備考", lines=3, max_lines=8, placeholder="追加の備考があれば記載")
                
                reg_btn = gr.Button("登録", variant="primary")
                reg_result = gr.Markdown("")
                
                # AI Title Generation Event Handler
                ai_title_btn.click(
                    generate_title_from_description,
                    inputs=[reg_description],
                    outputs=[reg_title],
                    show_progress=True
                )
                
                # AI Summary Generation Event Handler
                ai_summary_btn.click(
                    generate_summary_from_description,
                    inputs=[reg_description],
                    outputs=[reg_summary],
                    show_progress=True
                )
                
                # AI Description Polishing Event Handler
                ai_polish_btn.click(
                    polish_description_text,
                    inputs=[reg_description],
                    outputs=[reg_description],
                    show_progress=True
                )
                
                reg_btn.click(
                    register_demo,
                    inputs=[reg_title, reg_summary, reg_description, reg_owner, reg_creator, reg_status, reg_demo_url, reg_repo_url, reg_products, reg_confidentiality, reg_remarks],
                    outputs=[reg_result, reg_title, reg_summary, reg_description, reg_owner, reg_creator, reg_status, reg_demo_url, reg_repo_url, reg_products, reg_confidentiality, reg_remarks],
                    show_progress=True
                )
            
            # Tab 3: Demo Update
            with gr.TabItem(get_text("tab_update_info", "ja")) as update_tab:
                upd_header = gr.Markdown("## デモ情報更新")
                
                with gr.Row():
                    upd_demo_id = gr.Number(label="Demo ID", placeholder="更新するデモのID（半角数値のみ）", precision=0, minimum=1)
                    search_btn = gr.Button("検索", variant="secondary")
                
                search_result = gr.Markdown("")
                
                with gr.Column():
                    upd_title = gr.Textbox(label="タイトル *", placeholder="デモのタイトル")
                    upd_summary = gr.Textbox(label="要約", placeholder="カード表示用の要約")
                    upd_description = gr.Textbox(label="詳細説明 (Markdownも可)", lines=5, max_lines=10, placeholder="詳細説明をMarkdown形式でも記載可能")
                    upd_owner = gr.Textbox(label="代表投稿者メールアドレス *", placeholder="john.smith@databricks.com", interactive=False)
                    upd_creator = gr.Textbox(label="デモ作成者メールアドレス", placeholder="デモを作成した人のメールアドレス（不明の場合は空白でOK）")
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
                    upd_remarks = gr.Textbox(label="備考", lines=3, max_lines=8, placeholder="追加の備考があれば記載")
                
                with gr.Row():
                    upd_btn = gr.Button("更新", variant="primary")
                    del_btn = gr.Button("削除", variant="stop")
                
                upd_result = gr.Markdown("")
                
                # Permission check area (replaces modal)
                with gr.Column(visible=False) as permission_area:
                    permission_msg = gr.Markdown("")
                    with gr.Row():
                        permission_cancel_btn = gr.Button("キャンセル", variant="secondary")
                        permission_confirm_btn = gr.Button("", variant="primary", visible=False)
                        permission_delete_btn = gr.Button("", variant="stop", visible=False)
                
                search_btn.click(
                    search_demo_for_update,
                    inputs=[upd_demo_id],
                    outputs=[upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result]
                )
                
                # Update button - check permission first
                upd_btn.click(
                    check_update_permission_or_execute,
                    inputs=[upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks],
                    outputs=[upd_result, upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result, permission_area, permission_msg, permission_confirm_btn, permission_delete_btn]
                )
                
                # Delete button - check permission first
                del_btn.click(
                    check_delete_permission_or_execute,
                    inputs=[upd_demo_id],
                    outputs=[upd_result, upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result, permission_area, permission_msg, permission_confirm_btn, permission_delete_btn]
                )
                
                # Permission cancel button - hide permission area
                permission_cancel_btn.click(
                    lambda: [gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False)],
                    outputs=[permission_area, permission_msg, permission_confirm_btn, permission_delete_btn]
                )
                
                # Permission confirm button - execute update
                permission_confirm_btn.click(
                    update_demo,
                    inputs=[upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks],
                    outputs=[upd_result, upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result],
                    show_progress=True
                ).then(
                    lambda: [gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False)],
                    outputs=[permission_area, permission_msg, permission_confirm_btn, permission_delete_btn]
                )
                
                # Permission delete button - execute delete
                permission_delete_btn.click(
                    delete_demo,
                    inputs=[upd_demo_id],
                    outputs=[upd_result, upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator, upd_status, upd_demo_url, upd_repo_url, upd_products, upd_confidentiality, upd_remarks, search_result],
                    show_progress=True
                ).then(
                    lambda: [gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False)],
                    outputs=[permission_area, permission_msg, permission_confirm_btn, permission_delete_btn]
                )
            
            # Tab 4: Bot Consultation Chat
            with gr.TabItem(get_text("tab_ask_bot", "ja")) as chat_tab:
                chat_header = gr.Markdown("## AIチャットボットによるデモ検索（Powered by Agent Bricks）")
                chat_instruction = gr.Markdown("デモに関する質問をしてください。AIが関連するデモを見つけてお答えします。")
                
                chatbot = gr.Chatbot(
                    height=400,
                    show_label=False,
                    type='messages',
                    avatar_images=("https://cdn-icons-png.flaticon.com/512/1053/1053244.png", "https://cdn-icons-png.flaticon.com/512/4712/4712109.png")
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="メッセージ（入力後にShift+Enterで送信）",
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
    
        # Auto-set user email and greeting on demo load
        def set_user_info(request: gr.Request, language: str = "ja"):
            user_email = get_current_user_email(request)
            greeting_msg = get_greeting_message(request, language)
            return greeting_msg, user_email, user_email
        
        def update_greeting_only(language: str, user_email: str):
            """Update only greeting message when language changes"""
            # Create a fake request object with the stored user email
            class FakeRequest:
                def __init__(self, email):
                    self.headers = {"x-forwarded-email": email}
            
            fake_request = FakeRequest(user_email)
            return get_greeting_message(fake_request, language)
        
        demo.load(
            set_user_info,
            outputs=[greeting_display, reg_owner, user_email_state]
        )
        
        # Language switch event handler
        language_switch.change(
            switch_language,
            inputs=[language_switch],
            outputs=[
                # Basic state and headers
                language_state, demo_list_header, table_instruction, demo_details,
                reg_header, upd_header, chat_header, chat_instruction,
                # Registration form fields
                reg_title, reg_summary, reg_description, reg_owner, reg_creator,
                reg_status, reg_demo_url, reg_repo_url, reg_products, 
                reg_confidentiality, reg_remarks,
                # Update form fields
                upd_demo_id, upd_title, upd_summary, upd_description, upd_owner, upd_creator,
                upd_status, upd_demo_url, upd_repo_url, upd_products,
                upd_confidentiality, upd_remarks,
                # Buttons
                refresh_btn, prev_btn, next_btn, ai_title_btn, ai_summary_btn, ai_polish_btn,
                reg_btn, search_btn, upd_btn, del_btn, permission_cancel_btn,
                send_btn, clear_btn,
                # Other UI elements
                page_input, demo_details,
                # New UI elements
                title_display, msg,
                # Tab elements
                demo_list_tab, new_reg_tab, update_tab, chat_tab
            ]
        ).then(
            # Update table column names only (lightweight operation)
            rename_table_columns,
            inputs=[demo_table, language_state],
            outputs=[demo_table]
        ).then(
            # Update greeting message with user name in the new language
            update_greeting_only,
            inputs=[language_state, user_email_state],
            outputs=[greeting_display]
        )
    
    return demo

if __name__ == "__main__":
    # Check required environment variables based on authentication method
    client_id = os.getenv('DATABRICKS_CLIENT_ID', '').strip()
    client_secret = os.getenv('DATABRICKS_CLIENT_SECRET', '').strip()
    use_oauth = bool(client_id and client_secret)
    
    if use_oauth:
        # In OAuth environment, check required endpoints
        if not RAG_ENDPOINT:
            print("Error: RAG_ENDPOINT environment variable is not set")
            exit(1)
    else:
        # In PAT environment, DATABRICKS_TOKEN is required
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