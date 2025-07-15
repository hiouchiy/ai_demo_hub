#!/usr/bin/env python3
"""
Enhanced startup script for AI Demo Hub with environment variable management
"""
import os
import sys
import subprocess

def set_default_environment_variables():
    """Set default environment variables if not already set"""
    # Database connection settings
    env_defaults = {
        'DATABRICKS_TOKEN': None,  # Required - no default
        'DATABRICKS_SERVER_HOSTNAME': 'adb-984752964297111.11.azuredatabricks.net',
        'DATABRICKS_WAREHOUSE_ID': '148ccb90800933a1',
        'RAG_ENDPOINT': None,  # Required - no default
    }
    
    missing_required = []
    
    for key, default_value in env_defaults.items():
        if not os.getenv(key):
            if default_value is None:
                missing_required.append(key)
            else:
                os.environ[key] = default_value
                print(f"✅ Set default {key}={default_value}")
        else:
            print(f"✅ Found {key}={os.getenv(key)}")
    
    if missing_required:
        print("\n❌ Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        print("\nPlease set these environment variables and try again.")
        print("Example:")
        print("export DATABRICKS_TOKEN=your_token_here")
        print("export RAG_ENDPOINT=your_rag_endpoint_here")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🚀 AI Demo Hub Startup Script")
    print("=" * 40)
    
    # Check and set environment variables
    print("\n1. Checking environment variables...")
    if not set_default_environment_variables():
        sys.exit(1)
    
    # Activate virtual environment if exists
    print("\n2. Activating virtual environment...")
    venv_path = ".venv/bin/activate"
    if os.path.exists(venv_path):
        print("✅ Virtual environment found")
        # Note: subprocess will use the current environment
    else:
        print("⚠️  Virtual environment not found, using system Python")
    
    # Launch the application
    print("\n3. Starting AI Demo Hub...")
    print("=" * 40)
    
    try:
        # Run the app with the current environment
        result = subprocess.run([sys.executable, "app.py"], 
                              env=os.environ.copy(),
                              check=False)
        
        if result.returncode != 0:
            print(f"\n❌ Application exited with code {result.returncode}")
            sys.exit(result.returncode)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 