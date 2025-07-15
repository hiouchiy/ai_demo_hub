#!/bin/bash

# AI Demo Hub - Enhanced Startup Script
# This script sets up the environment and starts the AI Demo Hub application

set -e  # Exit on any error

echo "🚀 AI Demo Hub - Enhanced Startup Script"
echo "======================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.py first."
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check required environment variables
echo "🔍 Checking environment variables..."

# Required variables
if [ -z "$DATABRICKS_TOKEN" ]; then
    echo "❌ DATABRICKS_TOKEN is not set"
    echo "Please set it with: export DATABRICKS_TOKEN=your_token_here"
    exit 1
fi

if [ -z "$RAG_ENDPOINT" ]; then
    echo "❌ RAG_ENDPOINT is not set"
    echo "Please set it with: export RAG_ENDPOINT=your_rag_endpoint_here"
    exit 1
fi

# Optional variables with defaults
if [ -z "$DATABRICKS_SERVER_HOSTNAME" ]; then
    echo "✅ Using default DATABRICKS_SERVER_HOSTNAME"
    export DATABRICKS_SERVER_HOSTNAME="adb-984752964297111.11.azuredatabricks.net"
else
    echo "✅ Found DATABRICKS_SERVER_HOSTNAME=$DATABRICKS_SERVER_HOSTNAME"
fi

if [ -z "$DATABRICKS_WAREHOUSE_ID" ]; then
    echo "✅ Using default DATABRICKS_WAREHOUSE_ID"
    export DATABRICKS_WAREHOUSE_ID="148ccb90800933a1"
else
    echo "✅ Found DATABRICKS_WAREHOUSE_ID=$DATABRICKS_WAREHOUSE_ID"
fi

echo "✅ Found DATABRICKS_TOKEN=***"
echo "✅ Found RAG_ENDPOINT=$RAG_ENDPOINT"

# Start the application
echo ""
echo "🚀 Starting AI Demo Hub..."
echo "======================================="
echo "📍 The application will be available at a shareable URL"
echo "⏳ Please wait for the server to start..."
echo ""

# Run the application
python app.py 