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

# Disable SSL Warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 2. CORE LOGIC: DEEP COMPARISON FOR REPORT ---
def get_structural_diffs(d1, d2, path=""):
    """
    Recursively compares two dictionaries/lists and returns a list of text explanations.
    Used for the Detailed Text Report.
    """
    diffs = []
    
    # Compare Dictionaries
    if isinstance(d1, dict) and isinstance(d2, dict):
        all_keys = set(d1.keys()) | set(d2.keys())
        for key in sorted(all_keys):
            new_path = f"{path}.{key}" if path else key
            if key not in d1:
                diffs.append(f"[ADDED] {new_path}: {d2[key]}")
            elif key not in d2:
                diffs.append(f"[REMOVED] {new_path}")
            else:
                diffs.extend(get_structural_diffs(d1[key], d2[key], new_path))
    
    # Compare Lists (Naive comparison by index for simple reports)
    elif isinstance(d1, list) and isinstance(d2, list):
        if d1 != d2:
            # If lists are short, show them; if objects, dig deeper if lengths match
            if len(d1) == len(d2):
                for i, (item1, item2) in enumerate(zip(d1, d2)):
                    diffs.extend(get_structural_diffs(item1, item2, f"{path}[{i}]"))
            else:
                diffs.append(f"[MODIFIED LIST] {path}\n      Source: {d1}\n      Target: {d2}")
    
    # Compare Values
    else:
        if d1 != d2:
            diffs.append(f"[CHANGE] {path}\n      Source: {d1}\n      Target: {d2}")
            
    return diffs

def generate_detailed_report_text(resource_type, json1, json2):
    """Generates the content for the Downloadable TXT file"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("========================================================")
    lines.append(f" INFRA AUDIT REPORT - {resource_type}")
    lines.append(f" Date: {now}")
    lines.append("========================================================")
    lines.append("")
    
    # Get specific differences
    diffs = get_structural_diffs(json1, json2)
    
    if not diffs:
        lines.append("✅ STATUS: SYNCED. No configuration drift detected.")
    else:
        lines.append(f"❌ STATUS: DRIFT DETECTED ({len(diffs)} issues found)")
        lines.append("")
        lines.append("--- DETAILED CHANGES ---")
        for d in diffs:
            lines.append(d)
            lines.append("-" * 40)
            
    return "\n".join(lines)

# --- 3. CORE LOGIC: VISUAL DIFF (HTML) ---
def generate_visual_diff(json1, json2, name1="Source (Dev)", name2="Target (Stg/Local)"):
    """
    Generates a Side-by-Side HTML Diff with FORCED WHITE BACKGROUND
    so it looks good even in Dark Mode.
    """
    text1 = json.dumps(json1, indent=2, sort_keys=True).splitlines()
    text2 = json.dumps(json2, indent=2, sort_keys=True).splitlines()

    differ = difflib.HtmlDiff(wrapcolumn=90)
    html_table = differ.make_table(
        text1, text2, 
        fromdesc=name1, 
        todesc=name2,
        context=True, 
        numlines=3
    )
    
    # INJECT CSS TO FIX UGLY DARK MODE ISSUES
    # We wrap the table in a white container and force black text.
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; padding: 0; }}
            .diff-container {{
                background-color: #ffffff;
                color: #000000;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #ccc;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                overflow-x: auto;
            }}
            table.diff {{ width: 100%; border-collapse: collapse; }}
            table.diff th {{ background-color: #f0f0f0; color: #333; padding: 5px; border-bottom: 1px solid #ccc; }}
            table.diff td {{ padding: 2px 5px; }}
            /* Colors for Diff */
            .diff_header {{ background-color: #e0e0e0; color: #555; }}
            .diff_next {{ display: none; }}
            .diff_add {{ background-color: #d4edda; color: #155724; }} /* Light Green */
            .diff_chg {{ background-color: #fff3cd; color: #856404; }} /* Light Yellow */
            .diff_sub {{ background-color: #f8d7da; color: #721c24; }} /* Light Red */
        </style>
    </head>
    <body>
        <div class="diff-container">
            {html_table}
        </div>
    </body>
    </html>
    """
    return styled_html

# --- 4. CLEANERS ---
def clean_api_gateway(api_json):
    clean = json.loads(json.dumps(api_json))
    if 'servers' in clean: del clean['servers']
    return clean

def clean_ecs_definition(td_json):
    clean = json.loads(json.dumps(td_json))
    ignored = ['taskDefinitionArn', 'revision', 'status', 'registeredAt', 'registeredBy', 'compatibilities', 'requiresAttributes', 'tags']
    for field in ignored:
        if field in clean: del clean[field]
    if 'containerDefinitions' in clean:
        for container in clean['containerDefinitions']:
            # SORT ENV VARS so order doesn't matter
            if 'environment' in container:
                container['environment'] = sorted(container['environment'], key=lambda x: x['name'])
            if 'secrets' in container:
                container['secrets'] = sorted(container['secrets'], key=lambda x: x['name'])
    return clean

# --- 5. LIVE AWS CLIENT ---
def get_aws_client(service, ak, sk, stoken, region):
    return boto3.client(service, region_name=region, aws_access_key_id=ak, aws_secret_access_key=sk, aws_session_token=stoken, verify=False)

def fetch_live_swagger(client, api_id, stage='dev'):
    try:
        response = client.get_export(restApiId=api_id, stageName=stage, exportType='oas30', parameters={'extensions': 'integrations'})
        return json.loads(response['body'].read())
    except Exception:
        return None

# --- 6. UI ---
st.title("🛡️ InfraAudit Pro")

tab_api, tab_ecs, tab_live = st.tabs(["📂 API Gateway (File)", "📦 ECS Task Def (File)", "☁️ Live AWS Sync"])

# TAB 1: API GATEWAY
with tab_api:
    st.info("Upload 'OpenAPI 3 + Extensions' JSON files.")
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Dev JSON", type=['json'], key="api1")
    f2 = c2.file_uploader("Local JSON", type=['json'], key="api2")

    if f1 and f2:
        j1 = clean_api_gateway(json.load(f1))
        j2 = clean_api_gateway(json.load(f2))
        
        if j1 == j2:
            st.success("✅ Synced")
        else:
            st.error("⚠️ Differences Found")
            # Render Visual Diff
            html_view = generate_visual_diff(j1, j2)
            components.html(html_view, height=600, scrolling=True)
            
            # Generate Text Report
            report_txt = generate_detailed_report_text("API Gateway", j1, j2)
            st.download_button("📥 Download Detailed Report", report_txt, "api_audit.txt")

# TAB 2: ECS
with tab_ecs:
    st.info("Upload ECS Task Definition JSONs.")
    c1, c2 = st.columns(2)
    e1 = c1.file_uploader("Dev Task Def", type=['json'], key="ecs1")
    e2 = c2.file_uploader("Stg Task Def", type=['json'], key="ecs2")

    if e1 and e2:
        j1 = clean_ecs_definition(json.load(e1))
        j2 = clean_ecs_definition(json.load(e2))
        
        if j1 == j2:
            st.success("✅ Synced")
        else:
            st.error("⚠️ Differences Found")
            html_view = generate_visual_diff(j1, j2, "Dev ECS", "Stg ECS")
            components.html(html_view, height=600, scrolling=True)
            
            report_txt = generate_detailed_report_text("ECS Task Definition", j1, j2)
            st.download_button("📥 Download Detailed Report", report_txt, "ecs_audit.txt")

# TAB 3: LIVE
with tab_live:
    with st.sidebar:
        st.header("🔐 Credentials")
        with st.form("auth"):
            ak = st.text_input("Access Key", type="password")
            sk = st.text_input("Secret Key", type="password")
            stok = st.text_input("Session Token", type="password")
            reg = st.text_input("Region", value="us-east-1")
            submit = st.form_submit_button("Save")
        if submit: st.session_state['creds'] = {'ak': ak, 'sk': sk, 'stok': stok, 'reg': reg}

    if 'creds' in st.session_state:
        c1, c2 = st.columns(2)
        dev_id = c1.text_input("Source ID", value="am78gt7609")
        loc_id = c2.text_input("Target ID")
        if st.button("Scan"):
            creds = st.session_state['creds']
            client = get_aws_client('apigateway', creds['ak'], creds['sk'], creds['stok'], creds['reg'])
            d = fetch_live_swagger(client, dev_id)
            l = fetch_live_swagger(client, loc_id)
            if d and l:
                cd = clean_api_gateway(d)
                cl = clean_api_gateway(l)
                if cd == cl: st.success("✅ Synced")
                else:
                    st.error("⚠️ Drift Detected")
                    html_view = generate_visual_diff(cd, cl)
                    components.html(html_view, height=600, scrolling=True)
                    report_txt = generate_detailed_report_text("Live API Gateway", cd, cl)
                    st.download_button("📥 Download Report", report_txt, "live_audit.txt")
            else:
                st.error("Fetch Failed")
    else:
        st.info("Provide credentials in sidebar")
