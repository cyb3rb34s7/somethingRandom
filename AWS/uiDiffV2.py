import streamlit as st
import boto3
import json
import urllib3
import datetime
from botocore.exceptions import ClientError

# --- CONFIGURATION ---
st.set_page_config(page_title="AWS Gateway Ops", page_icon="⚡", layout="wide")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- BACKEND LOGIC ---
def get_aws_client(service, ak, sk, stoken, region):
    """Generic client creator that handles the SSL verify=False requirement"""
    return boto3.client(
        service,
        region_name=region,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        aws_session_token=stoken,
        verify=False 
    )

def verify_credentials(ak, sk, stoken, region):
    """Checks if credentials are valid using STS GetCallerIdentity"""
    try:
        sts = get_aws_client('sts', ak, sk, stoken, region)
        identity = sts.get_caller_identity()
        return True, identity['Arn']
    except Exception as e:
        return False, str(e)

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
                         "detail": f"URI Differs.\nDev:   {d_int.get('uri')}\nLocal: {l_int.get('uri')}"
                     })
                
                if d_int.get('timeout') != l_int.get('timeout'):
                     logs.append({
                         "type": "WARN", 
                         "msg": f"Timeout Diff: {method.upper()} {path}", 
                         "detail": f"Dev: {d_int.get('timeout')}ms | Local: {l_int.get('timeout')}ms"
                     })
    return logs

# --- SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_arn' not in st.session_state:
    st.session_state['user_arn'] = ""

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("🔐 AWS Authentication")
    st.info("Enter temporary Keycloak/SSO credentials.")
    
    # Using 'key' in text_input ensures values persist during re-runs
    aws_access_key = st.text_input("AWS_ACCESS_KEY_ID", type="password", key="ak")
    aws_secret_key = st.text_input("AWS_SECRET_ACCESS_KEY", type="password", key="sk")
    aws_session_token = st.text_input("AWS_SESSION_TOKEN", type="password", key="token")
    aws_region = st.text_input("Region", value="us-east-1", key="region")
    
    # VERIFY BUTTON
    if st.button("Verify Credentials", type="primary"):
        if not (aws_access_key and aws_secret_key and aws_session_token):
            st.error("Please fill in all fields.")
        else:
            with st.spinner("Checking with AWS STS..."):
                is_valid, message = verify_credentials(aws_access_key, aws_secret_key, aws_session_token, aws_region)
                
                if is_valid:
                    st.session_state['authenticated'] = True
                    st.session_state['user_arn'] = message
                    st.success("✅ Authorized!")
                else:
                    st.session_state['authenticated'] = False
                    st.error(f"❌ Failed: {message}")

    # Show status in sidebar
    if st.session_state['authenticated']:
        st.success(f"Logged in as:\n{st.session_state['user_arn'].split('/')[-1]}")
    else:
        st.warning("Not Authenticated")

# --- MAIN PAGE ---
st.title("⚡ AWS Gateway Ops Dashboard")

if not st.session_state['authenticated']:
    st.info("👈 Please enter your AWS credentials in the sidebar and click 'Verify' to unlock the dashboard.")
    st.stop() # Stops the rest of the app from loading until verified

# --- APP CONTENT (Only shows if Authenticated) ---
tab1, tab2, tab3 = st.tabs(["🔍 Diff Checker", "📜 Logs (Future)", "🚀 Deploy (Future)"])

with tab1:
    st.subheader("Gateway Config Comparator")
    st.markdown("Compare the **Dev** Gateway against your **Local Proxy** to find drift and typos.")
    
    col1, col2 = st.columns(2)
    with col1:
        dev_id = st.text_input("Source API ID (Dev/Master)", value="am78gt7609")
    with col2:
        local_id = st.text_input("Target API ID (Local/Proxy)")

    if st.button("Run Comparison", type="primary"):
        with st.spinner("Scanning API Definitions..."):
            try:
                # Use the helper to get client (it handles verify=False)
                client = get_aws_client('apigateway', aws_access_key, aws_secret_key, aws_session_token, aws_region)
                
                dev_json = fetch_swagger(client, dev_id)
                local_json = fetch_swagger(client, local_id)

                if not dev_json:
                    st.error(f"❌ Could not fetch Source API ({dev_id}). Check ID and Permissions.")
                elif not local_json:
                    st.error(f"❌ Could not fetch Target API ({local_id}). Check ID and Permissions.")
                else:
                    # Run Logic
                    diffs = run_comparison(dev_json, local_json)
                    
                    if not diffs:
                        st.balloons()
                        st.success("✅ Perfect Match! Both Gateways are identical.")
                    else:
                        st.write(f"### ⚠️ Found {len(diffs)} Differences")
                        
                        # Prepare Text Report
                        report_text = f"AWS GATEWAY AUDIT REPORT\nGenerated: {datetime.datetime.now()}\n\n"
                        
                        for item in diffs:
                            # UI Card
                            if item['type'] == 'CRITICAL':
                                st.error(f"**{item['msg']}**\n\n{item['detail']}")
                            elif item['type'] == 'ERROR':
                                st.warning(f"**{item['msg']}**\n\n{item['detail']}")
                            else:
                                st.info(f"**{item['msg']}**\n\n{item['detail']}")
                            
                            # Text Report Append
                            report_text += f"[{item['type']}] {item['msg']}\n   {item['detail']}\n-------------------\n"

                        # Download Button
                        st.download_button(
                            label="📥 Download Audit Report (.txt)",
                            data=report_text,
                            file_name=f"gateway_diff_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain"
                        )

            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
