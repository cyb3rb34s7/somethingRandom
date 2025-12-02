import streamlit as st
import json
import os
import pandas as pd
import re
import glob
import difflib
import datetime

# ==========================================
# 1. PAGE CONFIG & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Infra Auditor Pro", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 3rem !important; }
    
    .resource-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        color: #333333;
    }
    
    div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    
    /* Status Badges */
    .badge-crit { background-color: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ef9a9a; }
    .badge-warn { background-color: #fff3e0; color: #ef6c00; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ffe0b2; }
    .badge-pass { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #a5d6a7; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. INTELLIGENT DATA LOADER (LOCKED)
# ==========================================
@st.cache_data
def load_data_recursively(folder_path):
    data = {"ecs_td": {}, "s3": {}, "api_gw": {}, "sqs": {}, "lambda": {}}
    if not folder_path or not os.path.exists(folder_path): return data

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json") and not file.startswith("metadata"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r') as f:
                        content = json.load(f)
                    name = file.replace('.json', '')
                    parent = os.path.basename(root)

                    if "task_definitions" in root or "task_definitions" in parent:
                        if 'containerDefinitions' in content or 'taskDefinition' in content:
                            data["ecs_td"][name] = content
                    elif "s3_buckets" in root:
                        data["s3"][name] = content
                    elif "api_gateway" in root:
                        data["api_gw"][name] = content
                except: pass 
    return data

def find_best_match(source_name, target_keys):
    if not target_keys or not source_name: return None
    replacements = [('dev', 'stg'), ('dev', 'prod'), ('us', 'eu'), ('west', 'central'), ('v1', 'v2')]
    prediction = source_name.lower()
    for old, new in replacements: prediction = prediction.replace(old, new)
    for key in target_keys:
        if prediction in key.lower(): return key
    matches = difflib.get_close_matches(source_name, target_keys, n=1, cutoff=0.5)
    return matches[0] if matches else None

# ==========================================
# 3. ECS & S3 LOGIC (LOCKED)
# ==========================================
def parse_ecs_env(container_def):
    vars_map = {}
    for item in container_def.get('environment', []):
        vars_map[item['name']] = {'value': item['value'], 'type': 'Plain'}
    for item in container_def.get('secrets', []):
        vars_map[item['name']] = {'value': item['valueFrom'], 'type': 'Secret'}
    return vars_map

def get_container_def(json_data):
    if 'containerDefinitions' in json_data: return json_data['containerDefinitions'][0]
    elif 'taskDefinition' in json_data: return json_data['taskDefinition']['containerDefinitions'][0]
    else: raise ValueError("Invalid Task Definition Format")

def normalize_policy_logic(policy_json):
    if not policy_json: return []
    s_str = json.dumps(policy_json, sort_keys=True)
    s_str = re.sub(r'\d{12}', '{{ACCOUNT_ID}}', s_str)
    s_str = re.sub(r'arn:aws:[a-z0-9-:]+:[a-z0-9-_\./]+', '{{ARN_MASKED}}', s_str)
    clean_pol = json.loads(s_str)
    stmts = clean_pol.get('Statement', [])
    if isinstance(stmts, dict): stmts = [stmts]
    return stmts

def render_ecs_dashboard(d_json, s_json, region_context):
    try:
        report_data = {"Critical": [], "Suspicious": [], "Info": []}
        c_dev = get_container_def(d_json)
        c_stg = get_container_def(s_json)
        col1, col2, col3 = st.columns(3)
        img_d, img_s = c_dev.get('image', 'N/A'), c_stg.get('image', 'N/A')
        img_short_d, img_short_s = img_d.split('/')[-1], img_s.split('/')[-1]
        
        if img_d == img_s: col1.markdown(f"**Image** <span class='badge-pass'>MATCH</span><br>`{img_short_d}`", unsafe_allow_html=True)
        else: 
            col1.markdown(f"**Image** <span class='badge-warn'>DRIFT</span><br>Src: `{img_short_d}`<br>Tgt: `{img_short_s}`", unsafe_allow_html=True)
            report_data["Critical"].append(f"Image Mismatch: {img_d} vs {img_s}")
        
        cpu_d, cpu_s = c_dev.get('cpu', '0'), c_stg.get('cpu', '0')
        mem_d, mem_s = c_dev.get('memory', '0'), c_stg.get('memory', '0')
        col2.metric("CPU Units", f"{cpu_s}", delta=None if cpu_d == cpu_s else "Changed")
        col3.metric("Memory", f"{mem_s}", delta=None if mem_d == mem_s else "Changed")
        st.divider()

        map_d = parse_ecs_env(c_dev)
        map_s = parse_ecs_env(c_stg)
        all_keys = sorted(set(map_d.keys()) | set(map_s.keys()))
        rows = []
        for k in all_keys:
            val_d = map_d.get(k, {}).get('value', '-')
            val_s = map_s.get(k, {}).get('value', '-')
            status = "✅ Match"; category = "Expected"
            if val_d == '-': status = "❌ Missing in Source"; category = "Critical"
            elif val_s == '-': status = "❌ Missing in Target"; category = "Critical"
            elif region_context == "EU (Ireland)" and ("us-east-1" in str(val_s) or "us-west-2" in str(val_s)): status = "🌍 Region Violation"; category = "Critical"
            elif "SECRET" in k and map_d.get(k, {}).get('type') != map_s.get(k, {}).get('type'): status = "🔓 Type Risk"; category = "Critical"
            elif val_d != val_s:
                if any(x in k for x in ['_HOST', '_URL', '_URI', '_ARN', '_DB', '_BUCKET']): status = "🔄 Config Diff"; category = "Expected"
                else: status = "⚠️ Value Drift"; category = "Suspicious"
            if category != "Match":
                rows.append({"Variable": k, "Status": status, "Source Value": val_d, "Target Value": val_s, "Category": category})
                if category != "Expected": report_data[category].append(f"{k}: {status} ({val_d} -> {val_s})")
        df = pd.DataFrame(rows)
        if not df.empty:
            crit = df[df['Category'] == "Critical"]
            susp = df[df['Category'] == "Suspicious"]
            exp = df[df['Category'] == "Expected"]
            if not crit.empty: st.error(f"🔴 {len(crit)} Critical Issues Found"); st.dataframe(crit.drop(columns=['Category']), use_container_width=True, hide_index=True)
            if not susp.empty: st.warning(f"🟡 {len(susp)} Suspicious Drifts"); st.dataframe(susp.drop(columns=['Category']), use_container_width=True, hide_index=True)
            with st.expander(f"🟢 {len(exp)} Expected Config Differences (Hidden)"): st.dataframe(exp.drop(columns=['Category']), use_container_width=True, hide_index=True)
        else: st.success("✅ Configuration Logic is Identical!")
        return report_data
    except Exception as e: st.error(f"Error parsing Task Definition: {str(e)}"); return {}

def render_s3_dashboard(d_json, s_json):
    report = {"Risks": []}
    c1, c2 = st.columns(2)
    e_d = d_json.get('Encryption', {})
    e_s = s_json.get('Encryption', {})
    enc_status = "badge-pass" if e_d == e_s else "badge-crit"
    c1.markdown(f"**Encryption** <span class='{enc_status}'>{'MATCH' if e_d == e_s else 'MISMATCH'}</span>", unsafe_allow_html=True)
    
    v_d = d_json.get('Versioning', 'Suspended')
    v_s = s_json.get('Versioning', 'Suspended')
    ver_status = "badge-pass" if v_d == v_s else "badge-warn"
    c2.markdown(f"**Versioning** <span class='{ver_status}'>{v_s}</span>", unsafe_allow_html=True)
    st.divider()

    p_dev = normalize_policy_logic(d_json.get('Policy'))
    p_stg = normalize_policy_logic(s_json.get('Policy'))
    missing = [p for p in p_dev if p not in p_stg]
    
    if not missing:
        st.success("✅ Policies Match Semantically")
    else:
        st.error(f"❌ Found {len(missing)} Permissions MISSING in Target")
        for m in missing:
            st.markdown(f"<div class='resource-card'><b>Missing:</b> {m.get('Action')}</div>", unsafe_allow_html=True)
            report["Risks"].append(f"Missing Policy: {m.get('Action')}")
    return report

# ==========================================
# 4. API GATEWAY LOGIC (STRICT REFERENCE IMPLEMENTATION)
# ==========================================

# --- EXACT COPIES OF YOUR REFERENCE SCRIPT FUNCTIONS ---
def compare_dicts(d1, d2, path=""):
    """Recursively compares two dictionaries and returns a list of difference strings."""
    differences = []
    
    # Keys in d1 but not d2
    for key in d1:
        if key not in d2:
            differences.append(f"MISSING KEY at {path}->{key}: Present in Dev, Missing in Local")
    
    # Keys in d2 but not d1
    for key in d2:
        if key not in d1:
            differences.append(f"EXTRA KEY at {path}->{key}: Missing in Dev, Present in Local")

    # Compare values for common keys
    for key in d1:
        if key in d2:
            val1 = d1[key]
            val2 = d2[key]
            current_path = f"{path}->{key}"

            # IGNORE LOGIC (From reference script)
            if key in ['uri', 'credentials', 'passthroughBehavior']: 
                pass 
            elif isinstance(val1, dict) and isinstance(val2, dict):
                differences.extend(compare_dicts(val1, val2, current_path))
            elif isinstance(val1, list) and isinstance(val2, list):
                if val1 != val2:
                     differences.append(f"LIST MISMATCH at {current_path}\n      Dev:   {val1}\n      Local: {val2}")
            else:
                if val1 != val2:
                    differences.append(f"VALUE MISMATCH at {current_path}\n      Dev:   {val1}\n      Local: {val2}")
    return differences

def normalize_integration(method_data):
    """Extracts integration details often responsible for 'typos'"""
    if 'x-amazon-apigateway-integration' in method_data:
        integ = method_data['x-amazon-apigateway-integration']
        return {
            'type': integ.get('type'),
            'uri': integ.get('uri'),
            'httpMethod': integ.get('httpMethod'),
            'timeoutInMillis': integ.get('timeoutInMillis'),
            'requestParameters': integ.get('requestParameters')
        }
    return {}

def render_api_dashboard_strict(dev_json, local_json):
    """
    Implements the EXACT logic from the reference script.
    Generates a full text report string AND a UI summary.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Initialize Report String
    report_lines = []
    report_lines.append("========================================================")
    report_lines.append(f" AWS API GATEWAY AUDIT REPORT")
    report_lines.append(f" Generated: {timestamp}")
    report_lines.append("========================================================\n")

    issues_found = 0
    ui_rows = []

    dev_paths = dev_json.get('paths', {})
    local_paths = local_json.get('paths', {})
    all_paths = sorted(dev_paths.keys())

    for path in all_paths:
        # 1. Missing Path Check
        if path not in local_paths:
            report_lines.append(f"🔴 [MISSING PATH] {path}")
            report_lines.append(f"   Action: This entire endpoint is missing in Local.\n")
            ui_rows.append({"Path": path, "Issue": "🔴 Entire Path Missing", "Detail": "Missing in Target"})
            issues_found += 1
            continue

        # 2. Method Checks
        dev_methods = dev_paths[path]
        local_methods = local_paths[path]

        for method, dev_details in dev_methods.items():
            if method not in local_methods:
                report_lines.append(f"🟠 [MISSING METHOD] {path} [{method.upper()}]")
                report_lines.append(f"   Action: The path exists, but {method.upper()} is missing.\n")
                ui_rows.append({"Path": path, "Issue": f"🟠 Method {method.upper()} Missing", "Detail": "Method missing in Target"})
                issues_found += 1
                continue

            # 3. Deep Recursive Compare (The "Reference" Logic)
            local_details = local_methods[method]
            dev_integ = normalize_integration(dev_details)
            local_integ = normalize_integration(local_details)

            diffs = compare_dicts(dev_integ, local_integ, path="Integration")

            if diffs:
                report_lines.append(f"⚠️  [MISMATCH] {path} [{method.upper()}]")
                for d in diffs:
                    report_lines.append(f"   - {d}")
                report_lines.append("")
                
                # Add to UI (First diff only to keep UI clean)
                first_diff_clean = diffs[0].split('\n')[0] # Keep it one line
                ui_rows.append({"Path": path, "Issue": f"⚠️ {method.upper()} Mismatch", "Detail": first_diff_clean})
                issues_found += 1

    if issues_found == 0:
        report_lines.append("\n✅ RESULT: Perfect Match! No configuration differences found.")
    else:
        report_lines.append(f"\n❌ RESULT: Found {issues_found} issues that need attention.")

    return ui_rows, "\n".join(report_lines)

# ==========================================
# 5. MAIN APP LAYOUT
# ==========================================
st.title("🕵️‍♂️ Infra Auditor Pro")
st.sidebar.header("📂 Data Sources")
path_a = st.sidebar.text_input("Source Folder (Dev/US)", value="aws_dump_us")
path_b = st.sidebar.text_input("Target Folder (Stg/EU)", value="aws_dump_eu")

if st.sidebar.button("Load Dumps"): st.cache_data.clear()

data_a = load_data_recursively(path_a)
data_b = load_data_recursively(path_b)

if not data_a["ecs_td"] and not data_a["s3"] and not data_a["api_gw"]:
    st.info("👈 Enter paths to begin.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📦 ECS Task Definitions", "🪣 S3 Buckets", "⚡ API Gateway"])

with tab1:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["ecs_td"].keys()))
    sel_src = col_sel_1.selectbox("Source TD", src_list)
    tgt_list = sorted(list(data_b["ecs_td"].keys()))
    predicted = find_best_match(sel_src, tgt_list)
    try: idx = tgt_list.index(predicted) if predicted else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Target TD", tgt_list, index=idx)
    ctx = st.radio("Region Context", ["Generic", "EU (Ireland)", "US (Oregon)"], horizontal=True)
    
    if sel_src and sel_tgt:
        rpt = render_ecs_dashboard(data_a["ecs_td"][sel_src], data_b["ecs_td"][sel_tgt], ctx)
        md = f"# ECS Report: {sel_src} vs {sel_tgt}\n\n"
        for k, v in rpt.items():
            if v: md += f"## {k}\n" + "\n".join([f"- {i}" for i in v]) + "\n\n"
        st.download_button("📥 Download ECS Report", md, "ecs_report.md")

with tab2:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["s3"].keys()))
    sel_src = col_sel_1.selectbox("Source Bucket", src_list)
    tgt_list = sorted(list(data_b["s3"].keys()))
    predicted = find_best_match(sel_src, tgt_list)
    try: idx = tgt_list.index(predicted) if predicted else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Target Bucket", tgt_list, index=idx)
    
    if sel_src and sel_tgt:
        rpt = render_s3_dashboard(data_a["s3"][sel_src], data_b["s3"][sel_tgt])
        md = f"# S3 Report: {sel_src} vs {sel_tgt}\n\n"
        for i in rpt["Risks"]: md += f"- [RISK] {i}\n"
        st.download_button("📥 Download S3 Report", md, "s3_report.md")

with tab3:
    st.subheader("⚡ API Gateway Strict Audit")
    
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["api_gw"].keys()))
    sel_src = col_sel_1.selectbox("Source API", src_list, key="api_src")
    
    tgt_list = sorted(list(data_b["api_gw"].keys()))
    predicted_tgt = find_best_match(sel_src, tgt_list)
    
    try: idx = tgt_list.index(predicted_tgt) if predicted_tgt else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Target API", tgt_list, index=idx, key="api_tgt")

    if sel_src and sel_tgt:
        j_a = data_a["api_gw"][sel_src]
        j_b = data_b["api_gw"][sel_tgt]
        
        # USE THE REFERENCE SCRIPT LOGIC
        ui_rows, txt_report = render_api_dashboard_strict(j_a, j_b)
        
        if ui_rows:
            st.error(f"❌ Found {len(ui_rows)} Differences")
            
            # CSS hack for black text on styled rows
            def color_api_rows(row):
                if "🔴" in row['Issue']: return ['background-color: #ffebee; color: black'] * len(row)
                if "🟠" in row['Issue']: return ['background-color: #fff3e0; color: black'] * len(row)
                if "⚠️" in row['Issue']: return ['background-color: #fff8e1; color: black'] * len(row)
                return ['color: black'] * len(row)

            df = pd.DataFrame(ui_rows)
            st.dataframe(df.style.apply(color_api_rows, axis=1), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Perfect Match!")

        st.download_button("📥 Download Full Text Report", txt_report, "api_audit.txt")
