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
            ITEMS_PER_PAGE = 20
            
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
        """Get demo by ID"""
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
            print(f"Error in get_demo_by_id: {str(e)}")
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
    
    def insert_demo(self, data: Dict) -> int:
        """Insert new demo"""
        try:
            # Convert products list to array format for Databricks
            products_list = [p.strip() for p in data['products'] if p.strip()]
            if products_list:
                products_array_str = ', '.join([f"'{p}'" for p in products_list])
            else:
                products_array_str = ""
                
            # Build query with escaped values
            query = f"""
            INSERT INTO hiroshi.ai_demo_hub.demos 
            (title, summary, description_md, owner_emp_id, status, demo_url, repo_url, products, confidentiality, remarks)
            VALUES ({self.escape_sql_string(data['title'])}, {self.escape_sql_string(data['summary'])}, 
                    {self.escape_sql_string(data['description_md'])}, {self.escape_sql_string(data['owner_emp_id'])}, 
                    {self.escape_sql_string(data['status'])}, {self.escape_sql_string(data['demo_url'])}, 
                    {self.escape_sql_string(data['repo_url'])}, array({products_array_str}), 
                    {self.escape_sql_string(data['confidentiality'])}, {self.escape_sql_string(data['remarks'])})
            """
            
            # Execute insert query
            self.execute_query_api(query)
            
            # Get the last inserted ID
            last_id_query = "SELECT MAX(demo_id) as last_id FROM hiroshi.ai_demo_hub.demos"
            result = self.execute_query_api(last_id_query)
            
            if result and len(result) > 0 and result[0].get('last_id'):
                return int(result[0]['last_id'])
            else:
                return 0
                
        except Exception as e:
            raise Exception(f"Failed to insert demo: {str(e)}")
    
    def update_demo(self, demo_id: int, data: Dict) -> bool:
        """Update existing demo"""
        try:
            # Convert products list to array format for Databricks
            products_list = [p.strip() for p in data['products'] if p.strip()]
            if products_list:
                products_array_str = ', '.join([f"'{p}'" for p in products_list])
            else:
                products_array_str = ""
                
            # Build query with escaped values
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
                remarks = {self.escape_sql_string(data['remarks'])}
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