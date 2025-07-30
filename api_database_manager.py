#!/usr/bin/env python3
"""
Alternative DatabaseManager using Databricks REST API
to avoid the sql client library issues
"""

import os
import requests
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

class APIBasedDatabaseManager:
    """REST API based Database Manager"""
    
    def __init__(self):
        self.server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME", "adb-984752964297111.11.azuredatabricks.net")
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID", "148ccb90800933a1")
        self.access_token = os.getenv("DATABRICKS_TOKEN")
        self.base_url = f"https://{self.server_hostname}/api/2.0/sql/statements"
        
    def execute_query_api(self, query: str) -> List[Dict]:
        """Execute query using Databricks REST API"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "statement": query,
            "warehouse_id": self.warehouse_id,
            "format": "JSON_ARRAY",
            "disposition": "INLINE"
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Check if the query was successful
            if result.get("status", {}).get("state") == "SUCCEEDED":
                # Get the result data
                data = result.get("result", {})
                
                # Get column names from manifest
                manifest = result.get("manifest", {})
                schema = manifest.get("schema", {})
                columns = [col["name"] for col in schema.get("columns", [])]
                
                if "data_array" in data:
                    rows = data["data_array"]
                    
                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        results.append(dict(zip(columns, row)))
                    
                    return results
                else:
                    print(f"No data_array in result: {result}")
                    return []
            else:
                print(f"Query failed: {result}")
                return []
                
        except Exception as e:
            print(f"API query failed: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            result = self.execute_query_api("SELECT 1 as test")
            return len(result) > 0 and str(result[0].get("test")) == "1"
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_demos(self, page: int = 1, sort_column: str = "created_at", sort_order: str = "ASC") -> Tuple[List[Dict], int]:
        """Get paginated demo list with sorting"""
        try:
            ITEMS_PER_PAGE = 10
            
            # Validate inputs
            if page is None or page < 1:
                page = 1
            
            offset = (page - 1) * ITEMS_PER_PAGE
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM hiroshi.ai_demo_hub.demos"
            count_result = self.execute_query_api(count_query)
            
            # Convert string to int - API returns all data as strings
            if count_result and len(count_result) > 0:
                total_count = int(count_result[0]['total'])
            else:
                total_count = 0
            
            # Get paginated data
            valid_columns = ["demo_id", "title", "summary", "owner_emp_id", "created_at", "updated_at", "status", "demo_url", "repo_url", "products", "confidentiality", "remarks"]
            if sort_column not in valid_columns:
                sort_column = "created_at"
            
            if sort_order.upper() not in ["ASC", "DESC"]:
                sort_order = "ASC"
            
            data_query = f"""
            SELECT demo_id, title, summary, owner_emp_id, created_at, updated_at, status, 
                   demo_url, repo_url, products, confidentiality, remarks
            FROM hiroshi.ai_demo_hub.demos
            ORDER BY {sort_column} {sort_order}
            LIMIT {ITEMS_PER_PAGE} OFFSET {offset}
            """
            
            results = self.execute_query_api(data_query)
            
            # Validate and clean results - ensure proper type conversion
            cleaned_results = []
            for result in results:
                demo_id = result.get('demo_id')
                if demo_id is not None:
                    # Convert demo_id to int if it's a string
                    if isinstance(demo_id, str):
                        try:
                            result['demo_id'] = int(demo_id)
                        except ValueError:
                            continue  # Skip invalid demo_id
                    
                    # Handle products array - convert string representation to list
                    if 'products' in result and result['products']:
                        products_value = result['products']
                        if isinstance(products_value, str):
                            try:
                                # Handle JSON string format
                                import json
                                if products_value.startswith('[') and products_value.endswith(']'):
                                    result['products'] = json.loads(products_value)
                                else:
                                    # Handle simple string format
                                    result['products'] = [products_value]
                            except json.JSONDecodeError:
                                # If JSON parsing fails, treat as single item
                                result['products'] = [products_value]
                        elif not isinstance(products_value, list):
                            # If it's not a list, make it a single-item list
                            result['products'] = [str(products_value)]
                    else:
                        result['products'] = []
                    
                    cleaned_results.append(result)
            
            return cleaned_results, total_count
            
        except Exception as e:
            print(f"Error in get_demos: {str(e)}")
            return [], 0
    
    def get_demo_by_id(self, demo_id: int) -> Optional[Dict]:
        """Get demo by ID (excluding all_info_md from user-facing operations)"""
        try:
            query = f"""SELECT demo_id, title, summary, description_md, owner_emp_id, created_at, updated_at, 
                               status, demo_url, repo_url, products, confidentiality, remarks 
                        FROM hiroshi.ai_demo_hub.demos WHERE demo_id = {demo_id}"""
            results = self.execute_query_api(query)
            
            if not results:
                return None
            
            result = results[0]
            
            # Convert demo_id to int if it's a string
            if 'demo_id' in result and isinstance(result['demo_id'], str):
                try:
                    result['demo_id'] = int(result['demo_id'])
                except ValueError:
                    pass
            
            # Handle products array - convert string representation to list
            if 'products' in result and result['products']:
                products_value = result['products']
                if isinstance(products_value, str):
                    try:
                        # Handle JSON string format
                        import json
                        if products_value.startswith('[') and products_value.endswith(']'):
                            result['products'] = json.loads(products_value)
                        else:
                            # Handle simple string format
                            result['products'] = [products_value]
                    except json.JSONDecodeError:
                        # If JSON parsing fails, treat as single item
                        result['products'] = [products_value]
                elif not isinstance(products_value, list):
                    # If it's not a list, make it a single-item list
                    result['products'] = [str(products_value)]
            else:
                result['products'] = []
                
            return result
            
        except Exception as e:
            print(f"Error in get_demo_by_id: {str(e)}")
            return None
    
    def get_demo_by_id_internal(self, demo_id: int) -> Optional[Dict]:
        """Get demo by ID for internal operations (includes all columns including all_info_md)"""
        try:
            query = f"SELECT * FROM hiroshi.ai_demo_hub.demos WHERE demo_id = {demo_id}"
            results = self.execute_query_api(query)
            
            if not results:
                return None
            
            result = results[0]
            
            # Convert demo_id to int if it's a string
            if 'demo_id' in result and isinstance(result['demo_id'], str):
                try:
                    result['demo_id'] = int(result['demo_id'])
                except ValueError:
                    pass
            
            # Handle products array - convert string representation to list
            if 'products' in result and result['products']:
                products_value = result['products']
                if isinstance(products_value, str):
                    try:
                        # Handle JSON string format
                        import json
                        if products_value.startswith('[') and products_value.endswith(']'):
                            result['products'] = json.loads(products_value)
                        else:
                            # Handle simple string format
                            result['products'] = [products_value]
                    except json.JSONDecodeError:
                        # If JSON parsing fails, treat as single item
                        result['products'] = [products_value]
                elif not isinstance(products_value, list):
                    # If it's not a list, make it a single-item list
                    result['products'] = [str(products_value)]
            else:
                result['products'] = []
                
            return result
            
        except Exception as e:
            print(f"Error in get_demo_by_id_internal: {str(e)}")
            return None
    
    def get_description_by_id(self, demo_id: int) -> Optional[str]:
        """Get description_md by demo_id"""
        try:
            if demo_id is None:
                return None
                
            query = f"SELECT description_md FROM hiroshi.ai_demo_hub.demos WHERE demo_id = {demo_id}"
            results = self.execute_query_api(query)
            
            if results and len(results) > 0:
                return results[0].get('description_md')
            return None
        except Exception as e:
            print(f"Error in get_description_by_id: {str(e)}")
            return None
    
    def escape_sql_string(self, value: str) -> str:
        """Escape SQL string to prevent injection"""
        if value is None:
            return 'NULL'
        return "'" + str(value).replace("'", "''") + "'"
    
    def generate_all_info_md(self, data: Dict) -> str:
        """Generate all_info_md content from demo data (includes ALL columns except all_info_md)"""
        # Handle products - could be list or string
        products = data.get('products', [])
        if isinstance(products, list):
            products_str = ", ".join(products) if products else "なし"
        else:
            products_str = str(products) if products else "なし"
        
        # Format timestamps if available
        created_at = data.get('created_at')
        updated_at = data.get('updated_at')
        if hasattr(created_at, 'strftime'):
            created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S JST')
        else:
            created_at_str = str(created_at) if created_at else "未設定"
        
        if hasattr(updated_at, 'strftime'):
            updated_at_str = updated_at.strftime('%Y-%m-%d %H:%M:%S JST')
        else:
            updated_at_str = str(updated_at) if updated_at else "未更新"
        
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
            import pytz
            from datetime import datetime
            JST = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(JST)
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Generate all_info_md content with temporary demo_id
            data_with_metadata = data.copy()
            data_with_metadata['demo_id'] = 'TBD'  # Will be updated after INSERT
            data_with_metadata['created_at'] = current_time
            data_with_metadata['updated_at'] = current_time
            all_info_md = self.generate_all_info_md(data_with_metadata)
                
            # Build query with escaped values (including timestamps and all_info_md)
            query = f"""
            INSERT INTO hiroshi.ai_demo_hub.demos 
            (title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products, confidentiality, remarks, created_at, updated_at, all_info_md)
            VALUES ({self.escape_sql_string(data['title'])}, {self.escape_sql_string(data['summary'])}, 
                    {self.escape_sql_string(data['description_md'])}, {self.escape_sql_string(data['owner_emp_id'])}, 
                    {self.escape_sql_string(data['status'])}, {self.escape_sql_string(data['demo_url'])}, 
                    {self.escape_sql_string(data['repo_url'])}, array({products_array_str}), 
                    {self.escape_sql_string(data['confidentiality'])}, {self.escape_sql_string(data['remarks'])},
                    '{current_time_str}', '{current_time_str}', {self.escape_sql_string(all_info_md)})
            """
            
            # Execute insert query
            self.execute_query_api(query)
            
            # Get the last inserted ID
            last_id_query = "SELECT MAX(demo_id) as last_id FROM hiroshi.ai_demo_hub.demos"
            result = self.execute_query_api(last_id_query)
            
            if result and len(result) > 0 and result[0].get('last_id'):
                new_demo_id = int(result[0]['last_id'])
                
                # Update all_info_md with correct demo_id
                data_with_metadata['demo_id'] = new_demo_id
                updated_all_info_md = self.generate_all_info_md(data_with_metadata)
                
                update_query = f"""
                UPDATE hiroshi.ai_demo_hub.demos 
                SET all_info_md = {self.escape_sql_string(updated_all_info_md)}
                WHERE demo_id = {new_demo_id}
                """
                self.execute_query_api(update_query)
                
                return new_demo_id
            else:
                return 0
                
        except Exception as e:
            raise Exception(f"Failed to insert demo: {str(e)}")
    
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
            
            # Generate current timestamp for updated_at
            import pytz
            from datetime import datetime
            JST = pytz.timezone('Asia/Tokyo')
            current_time = datetime.now(JST)
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Update metadata with current timestamp
            data_with_metadata['updated_at'] = current_time
            
            # Generate updated all_info_md content with complete metadata
            all_info_md = self.generate_all_info_md(data_with_metadata)
                
            # Build query with escaped values (including updated_at and all_info_md)
            query = f"""
            UPDATE hiroshi.ai_demo_hub.demos 
            SET title = {self.escape_sql_string(data['title'])}, 
                summary = {self.escape_sql_string(data['summary'])}, 
                description_md = {self.escape_sql_string(data['description_md'])}, 
                owner_emp_id = {self.escape_sql_string(data['owner_emp_id'])}, 
                status = {self.escape_sql_string(data['status'])}, 
                demo_url = {self.escape_sql_string(data['demo_url'])}, 
                repo_url = {self.escape_sql_string(data['repo_url'])}, 
                products = array({products_array_str}), 
                confidentiality = {self.escape_sql_string(data['confidentiality'])}, 
                remarks = {self.escape_sql_string(data['remarks'])},
                updated_at = '{current_time_str}',
                all_info_md = {self.escape_sql_string(all_info_md)}
            WHERE demo_id = {demo_id}
            """
            
            # Execute update query
            self.execute_query_api(query)
            return True
            
        except Exception as e:
            raise Exception(f"Failed to update demo: {str(e)}")
    
    def delete_demo(self, demo_id: int) -> bool:
        """Delete demo by ID"""
        try:
            # Validate demo_id
            if demo_id is None or demo_id <= 0:
                raise Exception("Invalid demo_id")
                
            # Build query
            query = f"DELETE FROM hiroshi.ai_demo_hub.demos WHERE demo_id = {demo_id}"
            
            # Execute delete query
            self.execute_query_api(query)
            return True
            
        except Exception as e:
            raise Exception(f"Failed to delete demo: {str(e)}")

# Test the API-based manager
if __name__ == "__main__":
    print("🔍 Testing API-based Database Manager")
    print("=" * 40)
    
    manager = APIBasedDatabaseManager()
    
    # Test connection
    print("1. Testing connection...")
    if manager.test_connection():
        print("✅ Connection test passed")
    else:
        print("❌ Connection test failed")
        exit(1)
    
    # Test get_demos
    print("\n2. Testing get_demos...")
    demos, total_count = manager.get_demos(1, "created_at", "ASC")
    print(f"✅ Retrieved {len(demos)} demos, total count: {total_count}")
    
    if demos:
        print("First demo:")
        print(f"  {demos[0]}")
    
    print("\n✅ All tests passed!") 
