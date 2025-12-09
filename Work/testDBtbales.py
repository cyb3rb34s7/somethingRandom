import os

# 1. Define your repositories root path
root_dir = "." 

# 2. List of tables to check (Case sensitive usually, but SQL is often case-insensitive)
tables_to_check = [
    "ITV.OLD_BATCH_HISTORY",
    "ITV.TEMP_USER_DATA",
    "ITV.LEGACY_LOGS"
]

# 3. Extensions to scan
extensions = ['.xml', '.java', '.sql']

def search_for_table(table_name):
    # Normalize to avoid case issues (optional, depending on your DB strictness)
    search_term = table_name.lower()
    
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(subdir, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        if search_term in content:
                            return filepath # Found it!
                except Exception as e:
                    print(f"Could not read {filepath}: {e}")
    return None

print("--- Starting Scan ---")
unused_tables = []

for table in tables_to_check:
    result = search_for_table(table)
    if result:
        print(f"[FOUND] {table} in {result}")
    else:
        print(f"[UNUSED?] {table} NOT found in codebase.")
        unused_tables.append(table)

print("\n--- Summary of Potentially Unused Tables ---")
for t in unused_tables:
    print(t)
