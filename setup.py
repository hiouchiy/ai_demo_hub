#!/usr/bin/env python3
"""
Setup script for AI Demo Hub
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required dependencies using uv"""
    print("Installing dependencies...")
    try:
        subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ 'uv' command not found. Please install uv first.")
        sys.exit(1)

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ["DATABRICKS_TOKEN", "RAG_ENDPOINT"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the application.")
        print("Example:")
        print("export DATABRICKS_TOKEN=your_token_here")
        print("export RAG_ENDPOINT=your_rag_endpoint_here")
        return False
    
    print("✅ All environment variables are set!")
    return True

def main():
    print("🚀 AI Demo Hub Setup")
    print("=" * 50)
    
    # Install dependencies
    install_dependencies()
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    print("\n🎉 Setup complete!")
    print("To start the application, run:")
    print("python app.py")

if __name__ == "__main__":
    main() 