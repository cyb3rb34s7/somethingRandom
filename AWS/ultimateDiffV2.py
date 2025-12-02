import streamlit as st
import boto3
import json
import pandas as pd
import datetime
import urllib3
from botocore.exceptions import ClientError

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="InfraMatrix Auditor", page_icon="🕵️‍♀️", layout="wide")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Custom CSS for "Dense" dashboard feel
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    h1 { font-size: 2rem; margin-bottom: 0rem; }
    h3 { font-size: 1.2rem; margin-top: 1rem; color: #444; }
    .stAlert { padding: 0.5rem; }
    
    /* Table Styling helps visibility */
    table { width: 100%; font-size: 13px; }
    thead th { background-color: #f0f2f6; color: #31333F; }
    
    /* Status Badges */
    .status-match { color: green; font-weight: bold; }
    .status-error { color: #d9534f; font-weight: bold; }
    .status-warn { color: #f0ad4e; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGIC: ECS FLATTENER (The Magic Part) ---
def parse_ecs_container(container_def):
    """
    Converts a raw container definition into a Logical Map of variables.
    Merges 'environment' and 'secrets' into a single dictionary.
    """
    vars_map = {}
    
    # 1. Process Plain Environment Variables
    for item in container_def.get('environment', []):
        vars_map[item['name']] = {
            'value': item['value'],
            'type': 'Plain',
            'source': 'environment'
        }
        
    # 2. Process Secrets (Merge into same map)
    for item in container_def.get('secrets', []):
        vars_map[item['name']] = {
            'value': item['valueFrom'], # In secrets, the value is the ARN
            'type': 'Secret',
            'source': 'secrets'
        }
        
    return vars_map

def compare_ecs_logic(dev_json, stg_json):
    """
    Compares two ECS Task Definitions logically, not textually.
    Returns a DataFrame for the UI.
    """
    rows = []
    
    # Get Container Lists (Assuming single container for simplicity, or matching by name)
    # For robust matching, we assume the first container is the main app
    c_dev = dev_json.get('containerDefinitions', [])[0]
    c_stg = stg_json.get('containerDefinitions', [])[0]
    
    # Compare Images
    img_dev = c_dev.get('image', 'Unknown')
    img_stg = c_stg.get('image', 'Unknown')
    
    # Parse Variables
    map_dev = parse_ecs_container(c_dev)
    map_stg = parse_ecs_container(c_stg)
    
    all_keys = sorted(set(map_dev.keys()) | set(map_stg.keys()))
    
    for key in all_keys:
        d_data = map_dev.get(key, {'value': '-', 'type': '-', 'source': '-'})
        s_data = map_stg.get(key, {'value': '-', 'type': '-', 'source': '-'})
        
        status = "✅ Match"
        if key not in map_dev:
            status = "❌ Missing in Dev"
        elif key not in map_stg:
            status = "❌ Missing in Stg"
        elif d_data['type'] != s_data['type']:
            status = "⚠️ Type Mismatch" # Env vs Secret
        elif d_data['value'] != s_data['value']:
            status = "⚠️ Value Mismatch"
            
        rows.append({
            "Variable": key,
            "Dev Value": d_data['value'],
            "Dev Type": d_data['type'],
            "Stg Value": s_data['value'],
            "Stg Type": s_data['type'],
            "Status": status
        })
        
    return pd.DataFrame(rows), img_dev, img_stg

# --- 3. LOGIC: API GATEWAY FLATTENER ---
def normalize_api_integration(method_details):
    """Extracts critical integration info"""
    if 'x-amazon-apigateway-integration' in method_details:
        integ = method_details['x-amazon-apigateway-integration']
        return integ.get('uri'), integ.get('timeoutInMillis')
    return None, None

def compare_api_logic(dev_json, local_json):
    rows = []
    dev_paths = dev_json.get('paths', {})
    local_paths = local_json.get('paths', {})
    
    all_paths = sorted(set(dev_paths.keys()) | set(local_paths.keys()))
    
    for path in all_paths:
        # Check Path Existence
        if path not in local_paths:
            rows.append({"Endpoint": path, "Method": "ALL", "Status": "❌ Missing in Local", "Dev URI": "-", "Local URI": "-"})
            continue
        if path not in dev_paths:
            rows.append({"Endpoint": path, "Method": "ALL", "Status": "❌ Extra in Local", "Dev URI": "-", "Local URI": "-"})
            continue
            
        # Check Methods
        d_methods = dev_paths[path]
        l_methods = local_paths[path]
        all_methods = sorted(set(d_methods.keys()) | set(l_methods.keys()))
        
        for method in all_methods:
            if method not in l_methods:
                rows.append({"Endpoint": path, "Method": method.upper(), "Status": "❌ Missing Method", "Dev URI": "-", "Local URI": "-"})
            elif method not in d_methods:
                rows.append({"Endpoint": path, "Method": method.upper(), "Status": "❌ Extra Method", "Dev URI": "-", "Local URI": "-"})
            else:
                # Compare Logic
                d_uri, d_time = normalize_api_integration(d_methods[method])
                l_uri, l_time = normalize_api_integration(l_methods[method])
                
                status = "✅ Match"
                if d_uri != l_uri:
                    status = "⚠️ URI Mismatch"
                elif d_time != l_time:
                    status = "⚠️ Timeout Mismatch"
                
                rows.append({
                    "Endpoint": path,
                    "Method": method.upper(),
                    "Status": status,
                    "Dev URI": d_uri,
                    "Local URI": l_uri,
                    "Timeout Dev": d_time,
                    "Timeout Loc": l_time
                })
    return pd.DataFrame(rows)

# --- 4. REPORT GENERATOR ---
def generate_markdown_report(df, title):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Filter for problems only
    problems = df[~df['Status'].str.contains("Match")]
    
    md = f"# InfraMatrix Report - {title}\n"
    md += f"**Date:** {now}\n"
    md += f"**Total Items:** {len(df)}\n"
    md += f"**Issues Found:** {len(problems)}\n\n"
    
    if len(problems) > 0:
        md += "## ⚠️ Discrepancies Detected\n"
        md += problems.to_markdown(index=False)
    else:
        md += "## ✅ All Systems Synced\nNo configuration drift detected."
        
    return md

# --- 5. AWS CLIENT ---
def get_aws_client(service, ak, sk, stoken, region):
    return boto3.client(service, region_name=region, aws_access_key_id=ak, aws_secret_access_key=sk, aws_session_token=stoken, verify=False)

def fetch_swagger(client, api_id):
    try:
        response = client.get_export(restApiId=api_id, stageName='dev', exportType='oas30', parameters={'extensions': 'integrations'})
        return json.loads(response['body'].read())
    except Exception: return None

# --- 6. UI LAYOUT ---
st.title("🕵️‍♀️ InfraMatrix Auditor")

tabs = st.tabs(["📦 ECS Matrix (Smart)", "⚡ API Gateway Matrix", "☁️ AWS Live Connect"])

# === TAB 1: ECS ===
with tabs[0]:
    st.info("Upload ECS Task Definitions to see the 'Logical Matrix' comparison.")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Dev Task Def (JSON)", type=['json'], key="ecs1")
    f2 = c2.file_uploader("Stg/Prod Task Def (JSON)", type=['json'], key="ecs2")
    
    if f1 and f2:
        j1 = json.load(f1)
        j2 = json.load(f2)
        
        df, img1, img2 = compare_ecs_logic(j1, j2)
        
        # 1. High Level Checks
        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Variables Scanned", len(df))
        
        # Image Check
        if img1 == img2:
            k2.success(f"Images Match: {img1}")
        else:
            k2.error(f"🚨 IMAGE MISMATCH")
            st.warning(f"**Dev:** `{img1}` vs **Stg:** `{img2}`")
            
        # Issues Count
        issues = len(df[~df['Status'].str.contains("Match")])
        if issues > 0:
            k3.error(f"{issues} Config Issues")
        else:
            k3.success("Configs Synced")

        # 2. The Matrix Table
        st.subheader("Variable Matrix")
        
        # Coloring logic for the dataframe
        def color_status(val):
            color = 'black'
            if 'Missing' in val: color = 'red'
            elif 'Mismatch' in val: color = '#d9534f' # darker red/orange
            elif 'Match' in val: color = 'green'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df.style.applymap(color_status, subset=['Status']),
            use_container_width=True,
            height=600
        )
        
        # 3. Export
        report = generate_markdown_report(df, "ECS Task Definition")
        st.download_button("📥 Download Report (MD)", report, "ecs_audit.md")

# === TAB 2: API GATEWAY ===
with tabs[1]:
    st.info("Upload OpenAPI JSONs to detect Integration drift.")
    c1, c2 = st.columns(2)
    a1 = c1.file_uploader("Dev API (JSON)", type=['json'], key="api1")
    a2 = c2.file_uploader("Local/Stg API (JSON)", type=['json'], key="api2")
    
    if a1 and a2:
        j1 = json.load(a1)
        j2 = json.load(a2)
        
        df_api = compare_api_logic(j1, j2)
        
        # Summary Metrics
        st.divider()
        issues_api = len(df_api[~df_api['Status'].str.contains("Match")])
        
        if issues_api == 0:
            st.success("✅ All Endpoints Synced")
        else:
            st.error(f"⚠️ {issues_api} Issues Detected")
            
        # Filter Toggle
        show_all = st.checkbox("Show All Endpoints (Uncheck to see only errors)", value=False)
        if not show_all:
            display_df = df_api[~df_api['Status'].str.contains("Match")]
        else:
            display_df = df_api
            
        st.dataframe(display_df, use_container_width=True)
        
        report_api = generate_markdown_report(df_api, "API Gateway")
        st.download_button("📥 Download Report (MD)", report_api, "api_audit.md")

# === TAB 3: LIVE CONNECT ===
with tabs[2]:
    st.markdown("##### ☁️ Scan AWS Directly")
    with st.expander("🔐 Credentials Setup"):
        with st.form("auth"):
            ak = st.text_input("Access Key", type="password")
            sk = st.text_input("Secret Key", type="password")
            stok = st.text_input("Session Token", type="password")
            reg = st.text_input("Region", value="us-east-1")
            sub = st.form_submit_button("Connect")
            if sub: st.session_state['creds'] = {'ak': ak, 'sk': sk, 'stok': stok, 'reg': reg}
            
    if 'creds' in st.session_state:
        c1, c2 = st.columns(2)
        dev_id = c1.text_input("Dev API ID", value="am78gt7609")
        loc_id = c2.text_input("Local API ID")
        
        if st.button("Run Live Scan"):
            creds = st.session_state['creds']
            client = get_aws_client('apigateway', creds['ak'], creds['sk'], creds['stok'], creds['reg'])
            
            d = fetch_swagger(client, dev_id)
            l = fetch_swagger(client, loc_id)
            
            if d and l:
                df_live = compare_api_logic(d, l)
                st.dataframe(df_live, use_container_width=True)
                r_live = generate_markdown_report(df_live, "Live API Gateway")
                st.download_button("Download Live Report", r_live, "live_audit.md")
            else:
                st.error("Could not fetch APIs. Check IDs and Permissions.")
