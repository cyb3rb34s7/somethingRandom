import streamlit as st
import boto3
import json
import urllib3
import datetime
from botocore.exceptions import ClientError

# --- CONFIGURATION ---
st.set_page_config(page_title="AWS Gateway Ops", page_icon="⚡", layout="wide")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- BACKEND LOGIC (Cached for performance) ---
def get_aws_client(ak, sk, stoken, region):
    return boto3.client(
        'apigateway',
        region_name=region,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        aws_session_token=stoken,
        verify=False
    )

def fetch_swagger(client, api_id, stage='dev'):
    try:
        response = client.get_export(
            restApiId=api_id,
            stageName=stage,
            exportType='oas30',
            parameters={'extensions': 'integrations'}
        )
        return json.loads(response['body'].read())
    except Exception as e:
        return None

def normalize_integration(method_data):
    """Extracts the fields most likely to have typos"""
    if 'x-amazon-apigateway-integration' in method_data:
        integ = method_data['x-amazon-apigateway-integration']
        return {
            'uri': integ.get('uri'),
            'type': integ.get('type'),
            'timeout': integ.get('timeoutInMillis')
        }
    return {}

def run_comparison(dev_data, local_data):
    logs = []
    
    dev_paths = dev_data.get('paths', {})
    local_paths = local_data.get('paths', {})
    
    # 1. Check Missing Paths
    for path in dev_paths:
        if path not in local_paths:
            logs.append({"type": "CRITICAL", "msg": f"Missing Endpoint: {path}", "detail": "Entire path missing in Local"})
            continue
        
        # 2. Check Methods & Integrations
        for method, dev_details in dev_paths[path].items():
            if method not in local_paths[path]:
                logs.append({"type": "ERROR", "msg": f"Missing Method: {method.upper()} {path}", "detail": "Path exists, but method is missing"})
            else:
                # 3. Deep Check for Typos
                local_details = local_paths[path][method]
                d_int = normalize_integration(dev_details)
                l_int = normalize_integration(local_details)
                
                if d_int.get('uri') != l_int.get('uri'):
                     logs.append({
                         "type": "WARN", 
                         "msg": f"Mismatch: {method.upper()} {path}", 
                         "detail": f"URI Differs.\nDev: {d_int.get('uri')}\nLocal: {l_int.get('uri')}"
                     })
                
                if d_int.get('timeout') != l_int.get('timeout'):
                     logs.append({
                         "type": "WARN", 
                         "msg": f"Timeout Diff: {method.upper()} {path}", 
                         "detail": f"Dev: {d_int.get('timeout')}ms | Local: {l_int.get('timeout')}ms"
                     })
    return logs

# --- UI FRONTEND ---

# 1. Sidebar for Credentials (SSO Friendly)
with st.sidebar:
    st.header("🔐 AWS Authentication")
    st.info("Since you use Keycloak, paste temp creds here.")
    aws_access_key = st.text_input("AWS_ACCESS_KEY_ID", type="password")
    aws_secret_key = st.text_input("AWS_SECRET_ACCESS_KEY", type="password")
    aws_session_token = st.text_input("AWS_SESSION_TOKEN", type="password")
    aws_region = st.text_input("Region", value="us-east-1")
    
    auth_ready = aws_access_key and aws_secret_key and aws_session_token

# 2. Main Layout
st.title("⚡ AWS API Gateway Ops")
st.markdown("Compare environments, audit logs, and fix configuration drift.")

# Tabs act as your "Tiles" for future features
tab1, tab2, tab3 = st.tabs(["🔍 Diff Checker", "📜 Logs (Future)", "🚀 Deploy (Future)"])

with tab1:
    st.subheader("Gateway Config Comparator (Same Env)")
    
    col1, col2 = st.columns(2)
    with col1:
        dev_id = st.text_input("Source API ID (Dev/Master)", value="am78gt7609")
    with col2:
        local_id = st.text_input("Target API ID (Local/Proxy)")

    if st.button("Run Comparison", type="primary"):
        if not auth_ready:
            st.error("Please provide AWS Credentials in the sidebar first.")
        else:
            with st.spinner("Connecting to AWS and scanning APIs..."):
                try:
                    client = get_aws_client(aws_access_key, aws_secret_key, aws_session_token, aws_region)
                    dev_json = fetch_swagger(client, dev_id)
                    local_json = fetch_swagger(client, local_id)

                    if not dev_json or not local_json:
                        st.error("Could not fetch API definitions. Check IDs and Permissions.")
                    else:
                        # Run Logic
                        diffs = run_comparison(dev_json, local_json)
                        
                        if not diffs:
                            st.balloons()
                            st.success("✅ Perfect Match! Both Gateways are identical.")
                        else:
                            st.write("### ⚠️ Differences Found")
                            
                            # Create a text report for download
                            report_text = f"AUDIT REPORT - {datetime.datetime.now()}\n\n"
                            
                            for item in diffs:
                                # Visual Display
                                if item['type'] == 'CRITICAL':
                                    st.error(f"**{item['msg']}**\n\n{item['detail']}")
                                elif item['type'] == 'ERROR':
                                    st.warning(f"**{item['msg']}**\n\n{item['detail']}")
                                else:
                                    st.info(f"**{item['msg']}**\n\n{item['detail']}")
                                
                                # Add to text report
                                report_text += f"[{item['type']}] {item['msg']}\n   {item['detail']}\n-------------------\n"

                            # Download Button
                            st.download_button(
                                label="📥 Download Audit Report (.txt)",
                                data=report_text,
                                file_name="api_gateway_diff.txt",
                                mime="text/plain"
                            )

                except Exception as e:
                    st.error(f"System Error: {str(e)}")
