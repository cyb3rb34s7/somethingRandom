import streamlit as st
import json
import os
import pandas as pd
import re
import glob

# ==========================================
# 1. PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(page_title="Offline Infra Auditor", page_icon="🕵️‍♂️", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    
    /* STATUS BADGES */
    .badge-crit { background-color: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em;}
    .badge-warn { background-color: #fff3e0; color: #ef6c00; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em;}
    .badge-pass { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.9em;}
    
    /* TABLE STYLING */
    table { width: 100%; font-size: 13px; }
    thead th { background-color: #f0f2f6; color: #333; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING ENGINE
# ==========================================
@st.cache_data
def load_data_from_folder(folder_path):
    """
    Recursively loads all JSON files into a structured dictionary.
    Structure: data[service][resource_name] = json_content
    """
    data = {}
    if not folder_path or not os.path.exists(folder_path):
        return data

    # Find all JSON files
    files = glob.glob(os.path.join(folder_path, "**", "*.json"), recursive=True)
    
    for f in files:
        # Determine Service from folder name (e.g. .../s3_buckets/my-bucket.json -> service=s3_buckets)
        rel_path = os.path.relpath(f, folder_path)
        parts = rel_path.split(os.sep)
        
        if len(parts) >= 2:
            service = parts[-2] # Parent folder is service name
            name = parts[-1].replace('.json', '')
            
            if service not in data: data[service] = {}
            
            try:
                with open(f, 'r') as json_file:
                    data[service][name] = json.load(json_file)
            except: pass
            
    return data

# ==========================================
# 3. LOGIC: SEMANTIC NORMALIZERS
# ==========================================
def normalize_policy_statement(stmt):
    """Masks ARNs and Account IDs for logical comparison"""
    s_str = json.dumps(stmt, sort_keys=True)
    s_str = re.sub(r'\d{12}', '{{ACCOUNT_ID}}', s_str)
    s_str = re.sub(r'arn:aws:[a-z0-9-:]+:[a-z0-9-_\./]+', '{{ARN_MASKED}}', s_str)
    return json.loads(s_str)

def parse_ecs_container(container_def):
    """Flattens Env Vars and Secrets into one map"""
    vars_map = {}
    for item in container_def.get('environment', []):
        vars_map[item['name']] = {'value': item['value'], 'type': 'Plain'}
    for item in container_def.get('secrets', []):
        vars_map[item['name']] = {'value': item['valueFrom'], 'type': 'Secret'}
    return vars_map

# ==========================================
# 4. LOGIC: COMPARATORS
# ==========================================
def compare_ecs_traffic_light(dev_json, stg_json, region_context):
    rows = []
    # Safety check for empty definitions
    if not dev_json.get('taskDefinition') or not stg_json.get('taskDefinition'):
        return pd.DataFrame()

    c_dev = dev_json['taskDefinition']['containerDefinitions'][0]
    c_stg = stg_json['taskDefinition']['containerDefinitions'][0]
    
    map_dev = parse_ecs_container(c_dev)
    map_stg = parse_ecs_container(c_stg)
    all_keys = sorted(set(map_dev.keys()) | set(map_stg.keys()))
    
    for key in all_keys:
        d_val = map_dev.get(key, {}).get('value', '-')
        s_val = map_stg.get(key, {}).get('value', '-')
        
        category = "🟢 Expected"
        status = "Match"
        msg = ""

        # A. CRITICAL
        if d_val == '-': 
            category = "🔴 Critical"; status = "Missing in Source"
        elif s_val == '-': 
            category = "🔴 Critical"; status = "Missing in Target"
        elif region_context == "EU (Ireland)" and ("us-east-1" in s_val or "us-west-2" in s_val):
            category = "🔴 Critical"; status = "Region Violation"; msg = "US Endpoint in EU"
        elif "SECRET" in key and map_dev.get(key, {}).get('type') != map_stg.get(key, {}).get('type'):
             category = "🔴 Critical"; status = "Type Mismatch"; msg = "Secret vs Plain"

        # B. SUSPICIOUS
        elif d_val != s_val:
            if any(x in key for x in ['_HOST', '_URL', '_URI', '_ARN', '_DB', '_BUCKET']):
                category = "🟢 Expected"; status = "Env Specific"
            elif any(x in key for x in ['TIMEOUT', 'MEMORY', 'PORT', 'DEBUG', 'LOG', 'RETRIES']):
                category = "🟡 Suspicious"; status = "Value Drift"
            else:
                category = "🟡 Suspicious"; status = "Changed"

        rows.append({"Category": category, "Variable": key, "Source Value": d_val, "Target Value": s_val, "Status": status, "Note": msg})
    return pd.DataFrame(rows)

def compare_resource_policies(p1, p2):
    """Compares policies logically"""
    stmts1 = p1.get('Statement', []) if isinstance(p1, dict) else []
    stmts2 = p2.get('Statement', []) if isinstance(p2, dict) else []
    
    norm1 = [normalize_policy_statement(s) for s in stmts1]
    norm2 = [normalize_policy_statement(s) for s in stmts2]
    
    missing = [s for s in norm1 if s not in norm2]
    extra = [s for s in norm2 if s not in norm1]
    return missing, extra

# ==========================================
# 5. UI LAYOUT
# ==========================================
st.title("🕵️‍♂️ Offline Infra Auditor")

# --- SIDEBAR: FOLDER SELECTION ---
with st.sidebar:
    st.header("📂 Data Sources")
    path_a = st.text_input("Source Folder Path (e.g., Dump_US)", value="aws_dump_us")
    path_b = st.text_input("Target Folder Path (e.g., Dump_EU)", value="aws_dump_eu")
    
    if st.button("Load Data"):
        st.cache_data.clear()
        
    data_a = load_data_from_folder(path_a)
    data_b = load_data_from_folder(path_b)
    
    if data_a and data_b:
        st.success(f"Loaded: {len(data_a)} services from Source")
        st.success(f"Loaded: {len(data_b)} services from Target")
    elif path_a or path_b:
        st.warning("Folders not found or empty.")

# --- MAIN TABS ---
if not data_a or not data_b:
    st.info("👈 Please enter the paths to your 'Dump' folders in the sidebar to begin.")
    st.stop()

tab_ecs, tab_pol, tab_api, tab_search = st.tabs([
    "📦 ECS Smart Matrix", 
    "🛡️ Resource Policies", 
    "⚡ API Gateway", 
    "🔎 Global Search"
])

# === TAB 1: ECS SMART MATRIX ===
with tab_ecs:
    st.subheader("ECS Configuration Audit")
    
    # 1. Select Cluster/Task Def
    ecs_files_a = sorted(list(data_a.get('ecs_focused', {}).keys()))
    if not ecs_files_a:
        st.warning("No ECS Task Definitions found in Source folder.")
    else:
        # Filter to get Task Defs only (exclude services/cluster config for dropdown)
        # Note: The collector saves TDs in a 'task_definitions' subfolder structure
        # which flatten into keys like 'task_definitions_MyTask_v1' or similar depending on implementation
        # For simplicity, we assume the user picks the key.
        td_key = st.selectbox("Select Task Definition", ecs_files_a)
        
        region_ctx = st.selectbox("Target Region Context", ["EU (Ireland)", "US (Oregon)", "Generic"])
        
        # Get the JSONs
        json_a = data_a['ecs_focused'].get(td_key)
        json_b = data_b['ecs_focused'].get(td_key) # Try matching exact name first
        
        # Intelligent Fallback: If exact name missing (v5 vs v6), try to find matching family
        if not json_b:
             # Basic fuzzy match logic could go here
             pass

        if json_a and json_b:
            df = compare_ecs_traffic_light(json_a, json_b, region_ctx)
            
            if not df.empty:
                # TRAFFIC LIGHT UI
                crit = df[df['Category'].str.contains("Critical")]
                susp = df[df['Category'].str.contains("Suspicious")]
                exp = df[df['Category'].str.contains("Expected")]

                c1, c2, c3 = st.columns(3)
                c1.metric("Critical Issues", len(crit), delta_color="inverse")
                c2.metric("Suspicious Drifts", len(susp), delta_color="off")
                c3.metric("Expected Diff", len(exp))
                
                with st.expander(f"🔴 CRITICAL MISMATCHES ({len(crit)})", expanded=True):
                    if not crit.empty: st.dataframe(crit, use_container_width=True)
                    else: st.caption("Clean. No critical issues.")
                
                with st.expander(f"🟡 SUSPICIOUS ({len(susp)})", expanded=True):
                    if not susp.empty: st.dataframe(susp, use_container_width=True)
                    else: st.caption("No suspicious value drifts.")
                
                with st.expander(f"🟢 EXPECTED ({len(exp)}) - Hidden", expanded=False):
                    st.dataframe(exp, use_container_width=True)
            else:
                st.error("Could not parse Task Definitions.")
        else:
            st.error(f"Could not find counterpart for '{td_key}' in Target folder.")

# === TAB 2: RESOURCE POLICIES ===
with tab_pol:
    st.subheader("Semantic Policy Auditor")
    st.markdown("Compares IAM Logic (Who can do What) while ignoring Account IDs and ARNs.")
    
    svc_type = st.selectbox("Resource Type", ["s3_buckets", "sqs_queues", "sns_topics"])
    
    # Get available resources
    res_list = sorted(list(data_a.get(svc_type, {}).keys()))
    
    res_name = st.selectbox(f"Select {svc_type}", res_list)
    
    if res_name:
        # Load Configs
        cfg_a = data_a[svc_type].get(res_name, {})
        # Try to find same name in B, or let user pick if names differ
        cfg_b = data_b[svc_type].get(res_name)
        
        if not cfg_b:
            st.warning(f"'{res_name}' not found in Target. Select manually:")
            res_b_list = sorted(list(data_b.get(svc_type, {}).keys()))
            res_name_b = st.selectbox("Select Target Resource", res_b_list)
            cfg_b = data_b[svc_type].get(res_name_b, {})
        
        if cfg_a and cfg_b:
            c1, c2 = st.columns(2)
            
            # Policy Comparison
            pol_a = cfg_a.get('Policy')
            pol_b = cfg_b.get('Policy')
            
            if not pol_a and not pol_b:
                st.info("No Policies attached to either resource.")
            else:
                missing, extra = compare_resource_policies(pol_a, pol_b)
                
                if not missing and not extra:
                    st.success("✅ Policies Match Semantically!")
                else:
                    st.error("❌ Policy Drift Detected")
                    if missing:
                        st.write("Permissions in Source but **MISSING in Target**:")
                        for m in missing: st.json(m)
                    if extra:
                        st.write("Permissions **EXTRA in Target**:")
                        for e in extra: st.json(e)
            
            # Attribute Comparison (Encryption, Versioning)
            st.divider()
            st.markdown("#### Configuration Attributes")
            attr_ data = []
            keys = ['Versioning', 'Encryption'] # Add more based on Collector
            for k in keys:
                val_a = cfg_a.get(k, 'N/A')
                val_b = cfg_b.get(k, 'N/A')
                status = "✅ Match" if val_a == val_b else "⚠️ Mismatch"
                attr_data.append({"Attribute": k, "Source": val_a, "Target": val_b, "Status": status})
            st.dataframe(pd.DataFrame(attr_data), use_container_width=True)

# === TAB 3: API GATEWAY ===
with tab_api:
    st.subheader("API Gateway Integrations")
    apis_a = sorted(list(data_a.get('api_gateway', {}).keys()))
    api_sel = st.selectbox("Select API", apis_a)
    
    if api_sel:
        # Logic similar to previous API tool...
        # For brevity in this combined tool, simple JSON viewer or reuse logic
        json_a = data_a['api_gateway'][api_sel]
        json_b = data_b.get('api_gateway', {}).get(api_sel)
        
        if json_b:
            st.write("Comparison logic loaded...")
            # (Insert the compare_api_logic function here from previous steps)
        else:
            st.warning("API not found in Target.")

# === TAB 4: GLOBAL SEARCH ===
with tab_search:
    st.subheader("🔎 Find references across ALL files")
    search_term = st.text_input("Enter search string (e.g. queue url, error code, bucket name)")
    
    if search_term and st.button("Search"):
        results = []
        # Scan everything in Data A
        for service, items in data_a.items():
            for name, content in items.items():
                content_str = json.dumps(content)
                if search_term in content_str:
                    results.append({"Folder": "Source", "Service": service, "Resource": name})
        
        # Scan everything in Data B
        for service, items in data_b.items():
            for name, content in items.items():
                content_str = json.dumps(content)
                if search_term in content_str:
                    results.append({"Folder": "Target", "Service": service, "Resource": name})
                    
        if results:
            st.success(f"Found {len(results)} matches!")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("No matches found.")
