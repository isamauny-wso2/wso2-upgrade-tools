#!/bin/bash
"""
Setup script for TOML security pre-commit hooks.
Run this once to set up automatic TOML redaction checking before commits.
"""

echo "🔧 Setting up TOML security pre-commit hooks..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment and install pre-commit
echo "📥 Installing pre-commit..."
source .venv/bin/activate && pip install pre-commit

# Install the hooks
echo "🪝 Installing pre-commit hooks..."
source .venv/bin/activate && pre-commit install

echo "✅ Setup complete!"
echo
echo "📋 What this does:"
echo "  • Checks all TOML files for sensitive data before each commit"
echo "  • Blocks commits if unredacted secrets are found"
echo "  • Provides commands to redact files when needed"
echo
echo "🔧 Usage:"
echo "  • Normal commits will automatically check TOML files"
echo "  • If blocked, run: ./redact-all-toml.sh"
echo "  • Or redact specific files: python3 /Volumes/DATA/Support/toml_redactor.py <file> -o <file>"
echo
echo "🧪 Test the setup:"
echo "  source .venv/bin/activate && pre-commit run --all-files"