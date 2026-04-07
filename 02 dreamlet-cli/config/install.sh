#!/bin/bash
# Dreamlet Educational Video Production System - Installation Script

echo "🎬 Installing Dreamlet Educational Video Production System..."

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "📦 Installing with uv (recommended)..."
    uv sync
elif command -v pip &> /dev/null; then
    echo "📦 Installing with pip..."
    pip install -e .
else
    echo "❌ Neither uv nor pip found. Please install Python package manager first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p input output

echo "✅ Installation complete!"
echo "🚀 Run the application with: streamlit run app.py --server.port 5000"