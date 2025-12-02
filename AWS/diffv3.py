import streamlit as st
import boto3
import json
import pandas as pd
import datetime
import urllib3
import re
from botocore.exceptions import ClientError

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="InfraMatrix Auditor", page_icon="🕵️‍♀️", layout="wide")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    h1 { font-size: 2rem; margin-bottom: 0rem; }
    h3 { font-size: 1.2rem; margin-top: 1rem; color: #444; }
    
    /* Compliance Badges */
    .badge-pass { background-color: #d4edda; color: #155724; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-fail { background-color: #f8d7da; color: #721c24; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# --- 2. THE NEW CONTEXT LAYER ---
class ContextValidator:
    @staticmethod
    def validate_variable(key, value, region_context=None):
        """
        Runs logic checks on specific variables.
        Returns: (Passed_Boolean, Message)
        """
        issues = []
        val_str = str(value).lower()
        key_upper = key.upper()

        # RULE 1: Region Locking (The "US vs EU" Detector)
        # If we know the target region is 'eu-central-1', warn if we see 'us-east-1'
        if region_context and region_context in ['eu-central-1', 'eu-west-1']:
            if 'us-east-1' in val_str or 'us-west-2' in val_str:
                return False, f"🚨 **Cross-Region Risk**: Found US Endpoint in EU Config"
        
        # RULE 2: Protocol Checks
        if key_upper.endswith('_URL') or key_upper.endswith('_URI'):
            if not (val_str.startswith('http') or val_str.startswith('arn')):
                 return False, "⚠️ Invalid Format: Expected URL/ARN"
        
        # RULE 3: Secrets in Plain Text
        if any(x in key_upper for x in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
            if len(val_str) < 20 and not val_str.startswith('arn:aws:secretsmanager'):
                 return False, "⚠️ Potential Hardcoded Secret"

        # RULE 4: Port Validation
        if key_upper.endswith('_PORT'):
            if not str(value).isdigit():
                return False, "⚠️ Invalid Port (Not a number)"

        return True, "✅ Valid"

    @staticmethod
    def validate_iam_policy(policy_json):
        """
        Scans IAM Policy JSON for dangerous patterns.
        """
        issues = []
        statements = policy_json.get('Statement', [])
        if isinstance(statements, dict): statements = [statements] # Normalize

        for stmt in statements:
            effect = stmt.get('Effect', 'Allow')
            actions = stmt.get('Action', [])
            resource = stmt.get('Resource', [])
            
            if isinstance(actions, str): actions = [actions]
            if isinstance(resource, str): resource = [resource]

            # CHECK 1: Star * on Resource (The "Root Access" Bug)
            if effect == 'Allow' and '*' in resource:
                # Dangerous if combined with write permissions
                if '*' in actions or any('Delete' in a for a in actions) or any('Put' in a for a in actions):
                    issues.append("🚨 **Over-Permissive**: Full Write Access on '*' Resource")

            # CHECK 2: Hardcoded Users in Policy (Bad Practice)
            if 'Principal' in stmt:
                p = json.dumps(stmt['Principal'])
                if ':user/' in p:
                    issues.append("⚠️ **Fragile**: Hardcoded IAM User ARN (Use Roles instead)")

        return issues

# --- 3. LOGIC: PARSERS ---
def parse_ecs_container(container_def):
    vars_map = {}
    for item in container_def.get('environment', []):
        vars_map[item['name']] = {'value': item['value'], 'type': 'Plain'}
    for item in container_def.get('secrets', []):
        vars_map[item['name']] = {'value': item['valueFrom'], 'type': 'Secret'}
    return vars_map

def compare_ecs_logic(dev_json, stg_json, stg_region_context="eu-central-1"):
    rows = []
    c_dev = dev_json.get('containerDefinitions', [])[0]
    c_stg = stg_json.get('containerDefinitions', [])[0]
    
    map_dev = parse_ecs_container(c_dev)
    map_stg = parse_ecs_container(c_stg)
    
    all_keys = sorted(set(map_dev.keys()) | set(map_stg.keys()))
    
    for key in all_keys:
        d_val = map_dev.get(key, {}).get('value', '-')
        s_val = map_stg.get(key, {}).get('value', '-')
        
        # 1. Diff Status
        diff_status = "✅ Match"
        if d_val == '-': diff_status = "❌ Missing in Dev"
        elif s_val == '-': diff_status = "❌ Missing in Stg"
        elif d_val != s_val: diff_status = "⚠️ Changed"
        
        # 2. Context Compliance Check (The New Layer)
        is_valid, compliance_msg = ContextValidator.validate_variable(key, s_val, stg_region_context)
        
        rows.append({
            "Variable": key,
            "Dev Value": d_val,
            "Stg Value": s_val,
            "Diff Status": diff_status,
            "Compliance Check": compliance_msg # New Column
        })
        
    return pd.DataFrame(rows)

# --- 4. UI ---
st.title("🕵️‍♀️ InfraMatrix Auditor + Compliance")

tabs = st.tabs(["📦 ECS Matrix", "🛡️ IAM Policy Scanner"])

# TAB 1: ECS with Context Check
with tabs[0]:
    st.info("Compares ECS Definitions AND checks for Region Mismatches.")
    
    col_r, col_u = st.columns([1, 3])
    with col_r:
        # User defines the 'Expected' context
        target_region = st.selectbox("Target Region Context", ["us-east-1", "eu-central-1", "ap-south-1"])
    
    c1, c2 = st.columns(2)
    f1 = c1.file_uploader("Dev Task Def", type=['json'], key="e1")
    f2 = c2.file_uploader("Stg Task Def", type=['json'], key="e2")
    
    if f1 and f2:
        j1 = json.load(f1)
        j2 = json.load(f2)
        
        df = compare_ecs_logic(j1, j2, target_region)
        
        # COLORING LOGIC
        def color_map(row):
            styles = [''] * len(row)
            # Highlight Compliance Failures
            if '🚨' in row['Compliance Check']:
                styles[4] = 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            elif '⚠️' in row['Compliance Check']:
                styles[4] = 'color: #856404; font-weight: bold;'
                
            # Highlight Diffs
            if 'Missing' in row['Diff Status']:
                styles[3] = 'color: red;'
            return styles

        st.dataframe(df.style.apply(color_map, axis=1), use_container_width=True, height=600)

# TAB 2: IAM POLICY SCANNER (New Feature)
with tabs[1]:
    st.markdown("### 🛡️ Semantic IAM Policy Validator")
    st.info("Paste an IAM Policy JSON below. The tool will scan for 'Over-Permissive' risks.")
    
    policy_text = st.text_area("Paste IAM Policy JSON", height=300)
    
    if st.button("Scan Policy"):
        if policy_text:
            try:
                p_json = json.loads(policy_text)
                risks = ContextValidator.validate_iam_policy(p_json)
                
                if not risks:
                    st.success("✅ Policy looks secure (No obvious '*' writes detected).")
                else:
                    st.error(f"❌ Found {len(risks)} Security Risks")
                    for r in risks:
                        st.write(r)
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
