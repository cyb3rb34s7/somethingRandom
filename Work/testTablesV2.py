import os
import re

# ================= CONFIGURATION =================
# 1. Path to scan (Current directory by default)
ROOT_DIR = "." 

# 2. List of tables provided by your Infra guy
# (Paste the full list here, with or without schema prefix)
TABLES_TO_CHECK = [
    "ITV.BATCH_HISTORY",
    "ITV.USER_LOGS",
    "ITV.OLD_CONFIG_TABLE",
    # Add your 10-20 tables here...
]

# 3. File extensions to scan
EXTENSIONS = {'.xml', '.java', '.sql', '.properties'}
# =================================================

def get_clean_table_name(full_name):
    """Removes schema (e.g., 'ITV.TABLE' -> 'TABLE')"""
    if '.' in full_name:
        return full_name.split('.')[-1]
    return full_name

def scan_codebase():
    # Pre-process tables: Store as { "TABLE_NAME": { "original": "ITV.TABLE", "found": False, "locations": [] } }
    usage_report = {}
    
    for t in TABLES_TO_CHECK:
        clean_name = get_clean_table_name(t)
        usage_report[clean_name] = {
            "original": t,
            "found": False,
            "locations": []
        }

    print(f"--- Starting Scan of {ROOT_DIR} ---")
    print(f"--- Searching for {len(TABLES_TO_CHECK)} tables ---\n")

    files_scanned = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        # optimization: skip .git, node_modules, target folders
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'target', 'build']]
        
        for file in files:
            if os.path.splitext(file)[1] in EXTENSIONS:
                files_scanned += 1
                filepath = os.path.join(root, file)
                
                try:
                    # Try reading with utf-8, fallback to latin-1 (windows default)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        with open(filepath, 'r', encoding='latin-1') as f:
                            content = f.read()
                    
                    # Check against all tables
                    for clean_name, data in usage_report.items():
                        # REGEX: (?i) = case insensitive, \b = word boundary
                        # Matches " TABLE " or "table" but NOT "TABLE_BACKUP"
                        if re.search(r'(?i)\b' + re.escape(clean_name) + r'\b', content):
                            usage_report[clean_name]["found"] = True
                            # Record only the first 3 locations to keep output clean
                            if len(usage_report[clean_name]["locations"]) < 3:
                                usage_report[clean_name]["locations"].append(filepath)

                except Exception as e:
                    print(f"[ERROR] Could not read {filepath}: {e}")

    # ================= RESULTS =================
    print(f"\nScan complete. Checked {files_scanned} files.\n")
    
    unused_count = 0
    print("=== UNUSED TABLES (Candidates for Drop) ===")
    print(f"{'Table Name':<30} | {'Status'}")
    print("-" * 50)
    
    for clean_name, data in usage_report.items():
        if not data["found"]:
            print(f"{data['original']:<30} | ❌ NOT FOUND")
            unused_count += 1

    print("\n=== USED TABLES (Do Not Drop) ===")
    for clean_name, data in usage_report.items():
        if data["found"]:
            loc_str = ", ".join([os.path.basename(p) for p in data["locations"]])
            print(f"✅ {data['original']} found in: {loc_str}...")

    print(f"\nSummary: {unused_count} out of {len(TABLES_TO_CHECK)} tables appear unused.")

if __name__ == "__main__":
    scan_codebase()
