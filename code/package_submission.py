import os
import sys
import zipfile
import pandas as pd

def validate_output_csv(filepath="output.csv"):
    if not os.path.exists(filepath):
        print(f"[-] Output file {filepath} not found!")
        return False
        
    df = pd.read_csv(filepath)
    expected_cols = ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
    if list(df.columns) != expected_cols:
        print(f"[-] Invalid columns: {list(df.columns)} != {expected_cols}")
        return False
        
    valid_actions = {"notify", "digest", "mute"}
    if not set(df["action"].dropna().unique()).issubset(valid_actions):
        print("[-] Invalid action values found!")
        return False
        
    if df["reason"].isnull().any() or (df["reason"] == "").any():
        print("[-] Null or empty reasons found!")
        return False
        
    print(f"[+] output.csv validation PASSED ({len(df)} rows verified).")
    return True

def create_code_zip(zip_path="code.zip"):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    exclude_dirs = {"__pycache__", ".git", ".venv", "venv", "dataset", ".pytest_cache", ".idea", ".vscode"}
    exclude_files = {".env", "code.zip", "output.csv", "dataset.zip"}
    
    zip_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file in exclude_files or file.endswith(".pyc") or file.endswith(".zip"):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                zf.write(full_path, rel_path)
                zip_count += 1
                
    print(f"[+] Created {zip_path} containing {zip_count} files.")
    return True

if __name__ == "__main__":
    print("=== SUBMISSION PACKAGER & VALIDATOR ===")
    valid = validate_output_csv()
    if valid:
        create_code_zip()
