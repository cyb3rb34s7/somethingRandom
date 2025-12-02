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
    /* Fix for Tabs getting cut off */
    .block-container { padding-top: 3rem !important; }
    
    /* Card Styling - Fixed Text Color */
    .resource-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        color: #333333; /* FORCE BLACK TEXT */
    }
    
    /* Metrics Styling */
    div[data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    
    /* Status Badges */
    .badge-crit { background-color: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ef9a9a; }
    .badge-warn { background-color: #fff3e0; color: #ef6c00; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #ffe0b2; }
    .badge-pass { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em; border: 1px solid #a5d6a7; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADER (LOCKED)
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
                    with open(full_path, 'r') as f: content = json.load(f)
                    name = file.replace('.json', '')
                    parent = os.path.basename(root)
                    if "task_definitions" in root or "task_definitions" in parent:
                        if 'containerDefinitions' in content or 'taskDefinition' in content:
                            data["ecs_td"][name] = content
                    elif "s3_buckets" in root: data["s3"][name] = content
                    elif "api_gateway" in root: data["api_gw"][name] = content
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
# 3. ECS LOGIC (LOCKED - DO NOT TOUCH)
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

# ==========================================
# 4. S3 LOGIC (IMPROVED - SMART DIFF)
# ==========================================
def extract_conditions(condition_block):
    """Extracts critical values like SourceArn from conditions"""
    values = []
    if not condition_block: return []
    # Loop through operators (StringEquals, ArnLike, etc.)
    for operator, details in condition_block.items():
        for key, val in details.items():
            if isinstance(val, list): values.extend(val)
            else: values.append(val)
    return sorted(values)

def analyze_policy_statement(stmt):
    """Breaks a statement into components for fuzzy matching"""
    return {
        "Effect": stmt.get("Effect", "Allow"),
        "Action": sorted(stmt.get("Action", [])) if isinstance(stmt.get("Action"), list) else [stmt.get("Action")],
        "Principal": json.dumps(stmt.get("Principal", {}), sort_keys=True),
        "Condition": stmt.get("Condition", {})
    }

def render_s3_dashboard(d_json, s_json):
    report = {"Risks": [], "Info": []}
    
    # --- 1. CONFIGURATION CHECKS ---
    c1, c2, c3 = st.columns(3)
    e_d = d_json.get('Encryption', {})
    e_s = s_json.get('Encryption', {})
    enc_status = "badge-pass" if e_d == e_s else "badge-crit"
    c1.markdown(f"**Encryption** <span class='{enc_status}'>{'MATCH' if e_d == e_s else 'MISMATCH'}</span>", unsafe_allow_html=True)
    
    v_d = d_json.get('Versioning', 'Suspended')
    v_s = s_json.get('Versioning', 'Suspended')
    ver_status = "badge-pass" if v_d == v_s else "badge-warn"
    c2.markdown(f"**Versioning** <span class='{ver_status}'>{v_s}</span>", unsafe_allow_html=True)
    st.divider()

    # --- 2. SMART POLICY AUDIT ---
    st.subheader("🛡️ Permission Logic Audit")
    
    p_dev = d_json.get('Policy', {}).get('Statement', [])
    p_stg = s_json.get('Policy', {}).get('Statement', [])
    if isinstance(p_dev, dict): p_dev = [p_dev]
    if isinstance(p_stg, dict): p_stg = [p_stg]

    # Convert to Analyzable Objects
    dev_stmts = [analyze_policy_statement(s) for s in p_dev]
    stg_stmts = [analyze_policy_statement(s) for s in p_stg]

    # LOGIC: Find Missing or Drifted Permissions
    issues_found = False
    
    for d_s in dev_stmts:
        # Try to find a matching Action & Principal in Target
        match_found = False
        for s_s in stg_stmts:
            # Check if Actions overlap significantly
            common_actions = set(d_s['Action']).intersection(set(s_s['Action']))
            if common_actions and d_s['Principal'] == s_s['Principal']:
                # POTENTIAL MATCH FOUND - CHECK CONDITIONS
                match_found = True
                
                # Compare Conditions (The specific issue you had)
                d_conds = extract_conditions(d_s['Condition'])
                s_conds = extract_conditions(s_s['Condition'])
                
                missing_conds = [c for c in d_conds if c not in s_conds]
                
                if missing_conds:
                    issues_found = True
                    st.markdown(f"""
                    <div class='resource-card' style='border-left: 5px solid #ffa000;'>
                        <b>⚠️ Partial Match (Condition Drift)</b><br>
                        <b>Action:</b> {", ".join(d_s['Action'])}<br>
                        <b>Issue:</b> Target has fewer Allowed Sources.<br>
                        <hr style='margin:5px 0'>
                        <b>Missing Sources in Target:</b><br>
                        <code style='color: #d32f2f'>{"<br>".join(missing_conds)}</code>
                    </div>
                    """, unsafe_allow_html=True)
                    report["Risks"].append(f"Condition Drift: {d_s['Action']} missing {len(missing_conds)} source ARNs")
                break
        
        if not match_found:
            issues_found = True
            st.markdown(f"""
            <div class='resource-card' style='border-left: 5px solid #c62828;'>
                <b>❌ Completely Missing Permission</b><br>
                <b>Action:</b> {", ".join(d_s['Action'])}<br>
                <b>Principal:</b> {d_s['Principal']}<br>
                <span class='badge-crit'>Risk: Authorization Failure</span>
            </div>
            """, unsafe_allow_html=True)
            report["Risks"].append(f"Missing Action: {d_s['Action']}")

    if not issues_found:
        st.success("✅ Policies Match Logically (All Actions & Conditions Present)")
        
    return report

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
if not data_a["ecs_td"] and not data_a["s3"]: st.info("👈 Enter paths to begin."); st.stop()

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
    st.info("API Gateway Logic Placeholder (Reuse Logic from previous iterations if needed)")
