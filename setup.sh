#!/bin/bash

# Nostr Simulator Setup Script
# This script sets up a Python virtual environment and installs all dependencies

set -e  # Exit on any error

echo "🚀 Setting up Nostr Simulator development environment..."

# Check if Python 3.8+ is available
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "❌ Error: Python 3.8 or higher is required. Found Python $python_version"
    exit 1
fi

echo "✅ Python version: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip to latest version
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the simulator:"
echo "  python -m src.main"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To run tests with coverage:"
echo "  pytest --cov=src --cov-report=html --cov-report=term"
echo ""
echo "To run code quality checks:"
echo "  pre-commit run --all-files"
