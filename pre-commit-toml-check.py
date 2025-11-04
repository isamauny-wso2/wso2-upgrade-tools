#!/usr/bin/env python3
"""
Pre-commit hook to check for sensitive data in TOML files.
Prevents commits if unredacted sensitive data is found.
Uses the published wso2-tools repository.
"""

import sys
import subprocess
import tempfile
import os
from pathlib import Path

def download_redactor():
    """Download the redactor script from GitHub."""
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        script_path = os.path.join(temp_dir, "toml_redactor.py")

        # Download the script using curl
        result = subprocess.run([
            "curl", "-s", "-o", script_path,
            "https://raw.githubusercontent.com/isamauny-wso2/wso2-tools/main/tomlTools/toml_redactor.py"
        ], capture_output=True)

        if result.returncode == 0 and os.path.exists(script_path):
            return script_path
        else:
            return None
    except Exception:
        return None

def main():
    """Check TOML files for sensitive data before commit."""
    if len(sys.argv) < 2:
        print("No files to check")
        return 0

    files_to_check = sys.argv[1:]
    toml_files = [f for f in files_to_check if f.endswith('.toml')]

    if not toml_files:
        return 0

    # Download the redactor script
    redactor_script = download_redactor()
    if not redactor_script:
        print("❌ Failed to download TOML redactor script")
        print("Please check your internet connection or install manually:")
        print("https://github.com/isamauny-wso2/wso2-tools/blob/main/tomlTools/toml_redactor.py")
        return 1

    failed_files = []

    try:
        for toml_file in toml_files:
            # Run the redactor in report mode (no file changes)
            try:
                result = subprocess.run([
                    "python3", redactor_script, toml_file, "--report"
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    # Check if any redactions would be made
                    if "Redacted 0 sensitive fields" not in result.stderr:
                        failed_files.append(toml_file)
                        print(f"❌ {toml_file}: Contains sensitive data that needs redaction")
                        print(result.stderr.strip())
                    else:
                        print(f"✅ {toml_file}: No sensitive data found")
                else:
                    failed_files.append(toml_file)
                    print(f"❌ Error checking {toml_file}: {result.stderr}")
            except Exception as e:
                print(f"❌ Error checking {toml_file}: {e}")
                failed_files.append(toml_file)

    finally:
        # Clean up temporary file
        try:
            if redactor_script and os.path.exists(redactor_script):
                os.remove(redactor_script)
                os.rmdir(os.path.dirname(redactor_script))
        except Exception:
            pass

    if failed_files:
        print(f"\n🚫 Commit blocked! {len(failed_files)} file(s) contain sensitive data.")
        print("Please redact sensitive data before committing:")
        print("\nOptions:")
        print("1. Use the redact-all-toml.sh script:")
        print("   ./redact-all-toml.sh")
        print("\n2. Or manually redact individual files:")
        print(f"   # Download the redactor and run it on each file:")
        print(f"   curl -s https://raw.githubusercontent.com/isamauny-wso2/wso2-tools/main/tomlTools/toml_redactor.py -o toml_redactor.py")
        for file in failed_files:
            print(f"   python3 toml_redactor.py {file} -o {file}")
        return 1

    print(f"\n✅ All {len(toml_files)} TOML file(s) are clean!")
    return 0

if __name__ == "__main__":
    sys.exit(main())