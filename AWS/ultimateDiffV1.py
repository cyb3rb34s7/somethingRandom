import streamlit as st
import boto3
import json
import difflib
import datetime
import urllib3
import streamlit.components.v1 as components
from botocore.exceptions import ClientError

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="InfraAudit Pro", page_icon="🛡️", layout="wide")

# Disable SSL Warnings for your Corporate Proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    h1 { color: #2C3E50; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; }
    
    /* Diff Table Styling */
    table.diff {
        font-family: 'Consolas', 'Monaco', monospace; 
        font-size: 12px; 
        width: 100%; 
        border-collapse: collapse; 
    }
    .diff th { background-color: #f8f9fa; padding: 8px; border-bottom: 2px solid #ddd; text-align: left; }
    .diff td { padding: 4px 8px; border-bottom: 1px solid #eee; word-break: break-all; }
    .diff_add { background-color: #e6ffec; color: #155724; } /* Green for Added */
    .diff_chg { background-color: #fff3cd; color: #856404; } /* Yellow for Changed */
    .diff_sub { background-color: #ffeef0; color: #721c24; } /* Red for Removed */
    .diff_header { color: #999; background-color: #f1f1f1; }
</style>
""", unsafe_allow_html=True)

# --- 2. CORE LOGIC ---

def clean_api_gateway(api_json):
    """Normalize API Gateway JSON for comparison"""
    clean = json.loads(json.dumps(api_json)) # Deep copy
    # Remove fields that are guaranteed to be different or irrelevant
    if 'servers' in clean: del clean['servers']
    return clean

def clean_ecs_definition(td_json):
    """Normalize ECS Task Defs (Sorts Env Vars to prevent false flags)"""
    clean = json.loads(json.dumps(td_json))
    
    # Remove noise fields
    ignored = ['taskDefinitionArn', 'revision', 'status', 'registeredAt', 'registeredBy', 'compatibilities', 'requiresAttributes', 'tags']
    for field in ignored:
        if field in clean: del clean[field]

    # Sort Lists (Environment Vars & Secrets)
    if 'containerDefinitions' in clean:
        for container in clean['containerDefinitions']:
            if 'environment' in container:
                # Sort by Name so order doesn't matter
                container['environment'] = sorted(container['environment'], key=lambda x: x['name'])
            if 'secrets' in container:
                container['secrets'] = sorted(container['secrets'], key=lambda x: x['name'])
    return clean

def generate_visual_diff(json1, json2, name1="Source (Dev)", name2="Target (Stg/Local)"):
    """Generates a Side-by-Side HTML Diff"""
    text1 = json.dumps(json1, indent=2, sort_keys=True).splitlines()
    text2 = json.dumps(json2, indent=2, sort_keys=True).splitlines()

    differ = difflib.HtmlDiff(wrapcolumn=90)
    html = differ.make_table(
        text1, text2, 
        fromdesc=name1, 
        todesc=name2,
        context=True, 
        numlines=2
    )
    return html

def generate_report(resource_type, differences_found):
    """Generates a Markdown text report"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    md = f"# 🛡️ InfraAudit Report\n"
    md += f"**Date:** {now}\n"
    md += f"**Type:** {resource_type}\n"
    md += f"**Status:** {'❌ Drift Detected' if differences_found else '✅ Synced'}\n\n"
    if differences_found:
        md += "## ⚠️ Differences Detected\n"
        md += "Please check the attached visual diff for line-by-line comparison.\n"
        md += "Check for:\n1. Typos in Integration URIs\n2. Mismatched Environment Variables\n3. Timeout settings\n"
    else:
        md += "## ✅ No Issues\nConfigurations are structurally identical.\n"
    return md

# --- 3. LIVE AWS CLIENT ---
def get_aws_client(service, ak, sk, stoken, region):
    return boto3.client(
        service, region_name=region,
        aws_access_key_id=ak, aws_secret_access_key=sk, aws_session_token=stoken,
        verify=False # SSL Fix
    )

def fetch_live_swagger(client, api_id, stage='dev'):
    try:
        response = client.get_export(
            restApiId=api_id, stageName=stage, exportType='oas30', parameters={'extensions': 'integrations'}
        )
        return json.loads(response['body'].read())
    except Exception as e:
        return None

# --- 4. UI LAYOUT ---

st.title("🛡️ InfraAudit Pro")
st.markdown("##### The Ultimate Configuration Drift Detector")

# TABS
tab_api, tab_ecs, tab_live = st.tabs(["📂 API Gateway (File)", "📦 ECS Task Def (File)", "☁️ Live AWS Sync"])

# ==========================================
# TAB 1: API GATEWAY (FILE UPLOAD)
# ==========================================
with tab_api:
    st.info("Compare API Gateway configurations using exported JSON files (Bypass IAM permissions).")
    
    with st.expander("📝 How to Export JSON from AWS Console"):
        st.markdown("""
        1. Go to **API Gateway** > **Stages**.
        2. Select your Stage (e.g., `dev`).
        3. Click **Export** tab (or 'Stage Actions' > 'Export' in newer console).
        4. Select **OpenAPI 3** + **JSON**.
        5. **Check 'Export with API Gateway Extensions'**.
        6. Download.
        """)

    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Upload Dev/Source JSON", type=['json'], key="api1")
    f2 = c2.file_uploader("Upload Local/Target JSON", type=['json'], key="api2")

    if f1 and f2:
        j1 = clean_api_gateway(json.load(f1))
        j2 = clean_api_gateway(json.load(f2))
        
        if j1 == j2:
            st.success("✅ Exact Match! No drift detected.")
        else:
            st.error("⚠️ Differences Found")
            html_diff = generate_visual_diff(j1, j2)
            components.html(html_diff, height=600, scrolling=True)
            
            # Download
            rpt = generate_report("API Gateway", True)
            st.download_button("📥 Download Report", rpt, "api_audit.md")

# ==========================================
# TAB 2: ECS TASK DEFINITION (FILE UPLOAD)
# ==========================================
with tab_ecs:
    st.info("Compare ECS Task Definitions. Automatically sorts environment variables for accuracy.")
    
    with st.expander("📝 How to Export JSON from ECS"):
        st.markdown("""
        1. Go to **ECS** > **Task Definitions**.
        2. Click the Definition Family.
        3. Click the Revision number.
        4. Click the **JSON** tab.
        5. Copy/Download.
        """)

    c1, c2 = st.columns(2)
    e1 = c1.file_uploader("Upload Dev Task Def", type=['json'], key="ecs1")
    e2 = c2.file_uploader("Upload Stg/Prod Task Def", type=['json'], key="ecs2")

    if e1 and e2:
        # CLEAN & SORT
        j1 = clean_ecs_definition(json.load(e1))
        j2 = clean_ecs_definition(json.load(e2))
        
        # IMAGE CHECK
        imgs1 = [c['image'] for c in j1.get('containerDefinitions', [])]
        imgs2 = [c['image'] for c in j2.get('containerDefinitions', [])]
        
        if imgs1 != imgs2:
            st.warning(f"🚨 Image Version Mismatch: {imgs1} vs {imgs2}")

        if j1 == j2:
            st.success("✅ Exact Match! configuration is identical.")
        else:
            st.error(f"⚠️ Configuration Drift Detected")
            html_diff = generate_visual_diff(j1, j2, "Dev ECS", "Stg ECS")
            components.html(html_diff, height=600, scrolling=True)
            
            rpt = generate_report("ECS Task Definition", True)
            st.download_button("📥 Download Report", rpt, "ecs_audit.md")

# ==========================================
# TAB 3: LIVE AWS CONNECT
# ==========================================
with tab_live:
    st.warning("⚠️ Requires AWS Credentials. Uses SSL verify=False for proxy compatibility.")
    
    # SIDEBAR AUTH (Only visible when needed, but placed here for logic flow)
    with st.sidebar:
        st.header("🔐 AWS Credentials")
        with st.form("auth"):
            ak = st.text_input("Access Key ID", type="password")
            sk = st.text_input("Secret Access Key", type="password")
            stok = st.text_input("Session Token", type="password")
            reg = st.text_input("Region", value="us-east-1")
            submit_auth = st.form_submit_button("Save Credentials")
        
        if submit_auth:
            st.session_state['creds'] = {'ak': ak, 'sk': sk, 'stok': stok, 'reg': reg}
            st.success("Credentials Temporarily Saved")

    # MAIN LIVE UI
    if 'creds' not in st.session_state:
        st.info("👈 Please enter your credentials in the Sidebar first.")
    else:
        c1, c2 = st.columns(2)
        dev_id = c1.text_input("Source API ID", value="am78gt7609")
        loc_id = c2.text_input("Target API ID")
        
        if st.button("🔴 Scan Live APIs"):
            with st.spinner("Connecting to AWS..."):
                creds = st.session_state['creds']
                client = get_aws_client('apigateway', creds['ak'], creds['sk'], creds['stok'], creds['reg'])
                
                d_json = fetch_live_swagger(client, dev_id)
                l_json = fetch_live_swagger(client, loc_id)
                
                if d_json and l_json:
                    clean_d = clean_api_gateway(d_json)
                    clean_l = clean_api_gateway(l_json)
                    
                    if clean_d == clean_l:
                         st.balloons()
                         st.success("✅ Live APIs are Synced!")
                    else:
                        st.error("⚠️ Live Drift Detected")
                        html_diff = generate_visual_diff(clean_d, clean_l)
                        components.html(html_diff, height=600, scrolling=True)
                else:
                    st.error("Failed to fetch APIs. Check IDs and Permissions.")
