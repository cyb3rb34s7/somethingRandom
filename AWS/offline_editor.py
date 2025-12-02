import streamlit as st
import json
import os
import pandas as pd
import re
import glob
import difflib
import datetime

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS (The "Beautiful" Look)
# ==========================================
st.set_page_config(page_title="Infra Auditor Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    /* General Spacing */
    .block-container { padding-top: 1.5rem; }
    
    /* Card Styling */
    .resource-card {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
    }
    
    /* Status Badges */
    .badge-crit { background-color: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; border: 1px solid #ef9a9a; }
    .badge-warn { background-color: #fff3e0; color: #ef6c00; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; border: 1px solid #ffe0b2; }
    .badge-pass { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; border: 1px solid #a5d6a7; }
    .badge-info { background-color: #e3f2fd; color: #1565c0; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; border: 1px solid #90caf9; }

    /* Metrics */
    div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. INTELLIGENT DATA LOADER
# ==========================================
@st.cache_data
def load_data_recursively(folder_path):
    """
    Scans deeply nested folders to find resources.
    Identifies resource type based on directory names.
    """
    data = {
        "ecs_td": {},
        "s3": {},
        "api_gw": {},
        "sqs": {},
        "lambda": {}
    }
    
    if not folder_path or not os.path.exists(folder_path):
        return data

    # Walk through every file in the directory
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json") and not file.startswith("metadata"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r') as f:
                        content = json.load(f)
                    
                    # Heuristic: Determine Type based on Folder Name
                    # The collector uses specific folder names like 'task_definitions', 's3_buckets'
                    parent_folder = os.path.basename(root)
                    name = file.replace('.json', '')

                    if "task_definitions" in root or "task_definitions" in parent_folder:
                        data["ecs_td"][name] = content
                    elif "s3_buckets" in root:
                        data["s3"][name] = content
                    elif "api_gateway" in root:
                        data["api_gw"][name] = content
                    elif "sqs_queues" in root:
                        data["sqs"][name] = content
                    elif "lambdas" in root:
                        data["lambda"][name] = content
                        
                except Exception as e:
                    pass # Skip unreadable files
    return data

def find_best_match(source_name, target_keys):
    """
    Auto-Suggest Logic: Finds the most similar string in the target list.
    Returns: Best Match Name (or None if similarity < 0.6)
    """
    if not target_keys: return None
    
    # Check for exact suffix variations (dev->stg, us->eu)
    replacements = [('dev', 'stg'), ('dev', 'prod'), ('us', 'eu'), ('west', 'central')]
    prediction = source_name
    for old, new in replacements:
        prediction = prediction.replace(old, new)
    
    # 1. Try Exact "Predicted" Match
    if prediction in target_keys:
        return prediction

    # 2. Fuzzy Match
    matches = difflib.get_close_matches(source_name, target_keys, n=1, cutoff=0.6)
    return matches[0] if matches else None

# ==========================================
# 3. LOGIC: NORMALIZERS & COMPARATORS
# ==========================================
def parse_ecs_env(container_def):
    """Flattens ECS Env Vars & Secrets into a single map"""
    vars_map = {}
    for item in container_def.get('environment', []):
        vars_map[item['name']] = {'value': item['value'], 'type': 'Plain'}
    for item in container_def.get('secrets', []):
        vars_map[item['name']] = {'value': item['valueFrom'], 'type': 'Secret'}
    return vars_map

def normalize_policy_logic(policy_json):
    """Masks ARNs/Accounts for logic comparison"""
    if not policy_json: return []
    s_str = json.dumps(policy_json, sort_keys=True)
    s_str = re.sub(r'\d{12}', '{{ACCOUNT_ID}}', s_str)
    s_str = re.sub(r'arn:aws:[a-z0-9-:]+:[a-z0-9-_\./]+', '{{ARN_MASKED}}', s_str)
    
    clean_pol = json.loads(s_str)
    stmts = clean_pol.get('Statement', [])
    if isinstance(stmts, dict): stmts = [stmts]
    return stmts

def generate_markdown(title, sections):
    """Generates a formatted MD string for download"""
    md = f"# Infra Auditor Report: {title}\n"
    md += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    for section_title, items in sections.items():
        if items:
            md += f"## {section_title}\n"
            if isinstance(items, list):
                for i in items: md += f"- {i}\n"
            elif isinstance(items, str):
                md += items + "\n"
            md += "\n"
    return md

# ==========================================
# 4. UI: COMPONENT RENDERERS
# ==========================================
def render_ecs_dashboard(d_json, s_json, region_context):
    report_data = {"Critical": [], "Suspicious": [], "Info": []}
    
    # --- A. Header Metrics (Image & Resources) ---
    c_dev = d_json['taskDefinition']['containerDefinitions'][0]
    c_stg = s_json['taskDefinition']['containerDefinitions'][0]
    
    col1, col2, col3 = st.columns(3)
    
    # Image Check
    img_d, img_s = c_dev.get('image'), c_stg.get('image')
    if img_d == img_s:
        col1.markdown(f"**Image Version**<br><span class='badge-pass'>MATCH</span> `{img_d.split(':')[-1]}`", unsafe_allow_html=True)
    else:
        col1.markdown(f"**Image Version**<br><span class='badge-warn'>DRIFT</span>", unsafe_allow_html=True)
        col1.caption(f"Src: {img_d.split(':')[-1]}\nTgt: {img_s.split(':')[-1]}")
        report_data["Critical"].append(f"Image Mismatch: {img_d} vs {img_s}")

    # CPU Check
    cpu_d, cpu_s = c_dev.get('cpu', '0'), c_stg.get('cpu', '0')
    cpu_match = "badge-pass" if cpu_d == cpu_s else "badge-info"
    col2.markdown(f"**CPU Units**<br><span class='{cpu_match}'>{cpu_d} ➝ {cpu_s}</span>", unsafe_allow_html=True)

    # Memory Check
    mem_d, mem_s = c_dev.get('memory', '0'), c_stg.get('memory', '0')
    mem_match = "badge-pass" if mem_d == mem_s else "badge-info"
    col3.markdown(f"**Memory**<br><span class='{mem_match}'>{mem_d} ➝ {mem_s}</span>", unsafe_allow_html=True)

    st.divider()

    # --- B. The Traffic Light Matrix ---
    map_d = parse_ecs_env(c_dev)
    map_s = parse_ecs_env(c_stg)
    all_keys = sorted(set(map_d.keys()) | set(map_s.keys()))

    rows = []
    for k in all_keys:
        val_d = map_d.get(k, {}).get('value', '-')
        val_s = map_s.get(k, {}).get('value', '-')
        
        status = "✅ Match"
        category = "Expected"
        
        # 1. CRITICAL
        if val_d == '-': 
            status = "❌ Missing in Source"; category = "Critical"
        elif val_s == '-': 
            status = "❌ Missing in Target"; category = "Critical"
        elif region_context == "EU (Ireland)" and ("us-east-1" in val_s or "us-west-2" in val_s):
             status = "🌍 Region Violation"; category = "Critical"
        elif "SECRET" in k and map_d.get(k, {}).get('type') != map_s.get(k, {}).get('type'):
             status = "🔓 Type Risk"; category = "Critical"
        
        # 2. SUSPICIOUS
        elif val_d != val_s:
            if any(x in k for x in ['_HOST', '_URL', '_URI', '_ARN', '_DB', '_BUCKET']):
                status = "🔄 Config Diff"; category = "Expected"
            else:
                status = "⚠️ Value Drift"; category = "Suspicious"

        if category != "Match":
            rows.append({"Category": category, "Variable": k, "Status": status, "Source": val_d, "Target": val_s})
            if category != "Expected":
                report_data[category].append(f"{k}: {status} (Src: {val_d} | Tgt: {val_s})")

    df = pd.DataFrame(rows)
    if not df.empty:
        # Render Categories
        crit = df[df['Category'] == "Critical"]
        susp = df[df['Category'] == "Suspicious"]
        exp = df[df['Category'] == "Expected"]

        if not crit.empty:
            st.error(f"🔴 {len(crit)} Critical Issues Found")
            st.dataframe(crit[['Variable', 'Status', 'Source', 'Target']], use_container_width=True, hide_index=True)
        
        if not susp.empty:
            st.warning(f"🟡 {len(susp)} Suspicious Drifts")
            st.dataframe(susp[['Variable', 'Status', 'Source', 'Target']], use_container_width=True, hide_index=True)
            
        with st.expander(f"🟢 {len(exp)} Expected Config Differences (Hidden)"):
            st.dataframe(exp[['Variable', 'Source', 'Target']], use_container_width=True, hide_index=True)
    else:
        st.success("✅ Perfect Configuration Match!")

    return report_data

def render_s3_dashboard(d_json, s_json):
    report = {"Risks": [], "Info": []}
    
    # 1. Attributes Row
    c1, c2, c3 = st.columns(3)
    
    # Encryption
    e_d = d_json.get('Encryption', {})
    e_s = s_json.get('Encryption', {})
    if e_d == e_s:
        c1.markdown("**Encryption**<br><span class='badge-pass'>MATCH</span>", unsafe_allow_html=True)
    else:
        c1.markdown("**Encryption**<br><span class='badge-crit'>MISMATCH</span>", unsafe_allow_html=True)
        report["Risks"].append("Encryption Configuration differs.")

    # Versioning
    v_d = d_json.get('Versioning', 'Suspended')
    v_s = s_json.get('Versioning', 'Suspended')
    if v_d == v_s:
        c2.markdown(f"**Versioning**<br><span class='badge-pass'>{v_s}</span>", unsafe_allow_html=True)
    else:
        c2.markdown(f"**Versioning**<br><span class='badge-warn'>{v_d} ➝ {v_s}</span>", unsafe_allow_html=True)
        report["Risks"].append(f"Versioning drift: {v_d} -> {v_s}")

    # Region
    r_d = d_json.get('Region', 'us-east-1')
    c3.markdown(f"**Source Region**<br><span class='badge-info'>{r_d}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # 2. Semantic Policy Check
    st.subheader("🛡️ Permission Logic")
    p_d = normalize_policy_logic(d_json.get('Policy'))
    p_s = normalize_policy_logic(s_json.get('Policy'))
    
    missing = [p for p in p_d if p not in p_s]
    
    if not missing:
        st.success("✅ Policy Logic Matches (Account IDs & ARNs ignored)")
    else:
        st.error(f"❌ Found {len(missing)} Permissions MISSING in Target")
        for m in missing:
            with st.container():
                st.markdown(f"""
                <div class='resource-card' style='border-left: 5px solid #c62828;'>
                    <b>Missing Action:</b> {m.get('Action')}<br>
                    <b>Principal:</b> {m.get('Principal')}<br>
                    <span class='badge-crit'>Risk: Authorization Failure</span>
                </div>
                """, unsafe_allow_html=True)
                report["Risks"].append(f"Missing Policy Statement: {m.get('Action')}")
    
    return report

# ==========================================
# 5. MAIN APP LAYOUT
# ==========================================
st.sidebar.header("📂 Data Sources")
path_a = st.sidebar.text_input("Source Folder (Dev/US)", value="aws_dump_us")
path_b = st.sidebar.text_input("Target Folder (Stg/EU)", value="aws_dump_eu")

if st.sidebar.button("Load Dumps"):
    st.cache_data.clear()

# Load Data
data_a = load_data_recursively(path_a)
data_b = load_data_recursively(path_b)

if not data_a["ecs_td"] and not data_a["s3"]:
    st.info("👈 Please enter valid dump folder paths in the sidebar to start.")
    st.stop()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📦 ECS Task Definitions", "🪣 S3 Buckets", "⚡ API Gateway"])

# === TAB 1: ECS ===
with tab1:
    col_sel_1, col_sel_2 = st.columns(2)
    
    # Source Selector
    src_list = sorted(list(data_a["ecs_td"].keys()))
    sel_src = col_sel_1.selectbox("Select Source Task Def", src_list, key="ecs_src")
    
    # Auto-Predict Target
    tgt_list = sorted(list(data_b["ecs_td"].keys()))
    predicted_tgt = find_best_match(sel_src, tgt_list)
    
    # Target Selector (With default index set to prediction)
    try:
        idx = tgt_list.index(predicted_tgt) if predicted_tgt else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Select Target Task Def", tgt_list, index=idx, key="ecs_tgt")
    
    # Context Selector
    region_ctx = st.radio("Target Region Context", ["Generic", "EU (Ireland)", "US (Oregon)"], horizontal=True)

    # Render Dashboard
    if sel_src and sel_tgt:
        report = render_ecs_dashboard(data_a["ecs_td"][sel_src], data_b["ecs_td"][sel_tgt], region_ctx)
        
        # Download Button
        md_text = generate_markdown(f"ECS Audit {sel_src} vs {sel_tgt}", report)
        st.download_button("📥 Download ECS Report", md_text, "ecs_report.md")

# === TAB 2: S3 ===
with tab2:
    col_sel_1, col_sel_2 = st.columns(2)
    
    src_list = sorted(list(data_a["s3"].keys()))
    sel_src = col_sel_1.selectbox("Select Source Bucket", src_list, key="s3_src")
    
    tgt_list = sorted(list(data_b["s3"].keys()))
    predicted_tgt = find_best_match(sel_src, tgt_list)
    
    try: idx = tgt_list.index(predicted_tgt) if predicted_tgt else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Select Target Bucket", tgt_list, index=idx, key="s3_tgt")
    
    if sel_src and sel_tgt:
        report = render_s3_dashboard(data_a["s3"][sel_src], data_b["s3"][sel_tgt])
        
        md_text = generate_markdown(f"S3 Audit {sel_src} vs {sel_tgt}", report)
        st.download_button("📥 Download S3 Report", md_text, "s3_report.md")

# === TAB 3: API GATEWAY ===
with tab3:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["api_gw"].keys()))
    sel_src = col_sel_1.selectbox("Select Source API", src_list, key="api_src")
    
    tgt_list = sorted(list(data_b["api_gw"].keys()))
    predicted_tgt = find_best_match(sel_src, tgt_list)
    
    try: idx = tgt_list.index(predicted_tgt) if predicted_tgt else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Select Target API", tgt_list, index=idx, key="api_tgt")

    if sel_src and sel_tgt:
        # Simple Logic for API GW (reusing logic from our previous discussions)
        # Assuming the collector saved OAS3 JSON structure
        j_a = data_a["api_gw"][sel_src]
        j_b = data_b["api_gw"][sel_tgt]
        
        st.subheader("Route & Integration Check")
        # Extract paths
        paths_a = j_a.get('paths', {}).keys()
        paths_b = j_b.get('paths', {}).keys()
        
        missing = [p for p in paths_a if p not in paths_b]
        
        if missing:
            st.error(f"❌ {len(missing)} Missing Routes in Target")
            for m in missing: st.text(f"- {m}")
        else:
            st.success("✅ All Routes Present")
            
        md_text = generate_markdown(f"API Audit {sel_src}", {"Missing Routes": missing})
        st.download_button("📥 Download API Report", md_text, "api_report.md")
