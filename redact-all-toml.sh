#!/bin/bash
# Script to redact all TOML files in the current directory.
# Creates backups before redacting.
# Uses the published wso2-tools repository.

# Download the redactor script if not present locally
REDACTOR_SCRIPT="./toml_redactor.py"

if [ ! -f "$REDACTOR_SCRIPT" ]; then
    echo "📥 Downloading TOML redactor script..."
    curl -s -o "$REDACTOR_SCRIPT" "https://raw.githubusercontent.com/isamauny-wso2/wso2-tools/main/tomlTools/toml_redactor.py"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to download redactor script"
        exit 1
    fi
    chmod +x "$REDACTOR_SCRIPT"
    echo "✅ Downloaded redactor script"
fi

echo "🔍 Finding TOML files..."
TOML_FILES=$(find . -name "*.toml" -not -path "./.git/*" -not -name "*.backup_*")

if [ -z "$TOML_FILES" ]; then
    echo "No TOML files found."
    exit 0
fi

echo "Found TOML files:"
echo "$TOML_FILES"
echo

read -p "Do you want to create backups before redacting? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BACKUP_SUFFIX=".backup_$(date +%Y%m%d_%H%M%S)"
    echo "📋 Creating backups with suffix: $BACKUP_SUFFIX"

    while IFS= read -r file; do
        if [ -f "$file" ]; then
            cp "$file" "${file}${BACKUP_SUFFIX}"
            echo "  ✅ Backed up: $file → ${file}${BACKUP_SUFFIX}"
        fi
    done <<< "$TOML_FILES"
    echo
fi

echo "🔒 Redacting TOML files..."
while IFS= read -r file; do
    if [ -f "$file" ]; then
        echo "Processing: $file"
        python3 "$REDACTOR_SCRIPT" "$file" -o "$file" --report
        echo
    fi
done <<< "$TOML_FILES"

echo "✅ All TOML files have been redacted!"
echo "💡 You can now safely commit your files."