# ==========================================
# API GATEWAY HELPER FUNCTIONS (Add after S3 logic, before main app)
# ==========================================

def normalize_integration(method_data):
    """Extracts integration details for comparison"""
    if 'x-amazon-apigateway-integration' not in method_data:
        return None
    
    integ = method_data['x-amazon-apigateway-integration']
    return {
        'type': integ.get('type'),
        'uri': integ.get('uri', ''),
        'httpMethod': integ.get('httpMethod'),
        'timeoutInMillis': integ.get('timeoutInMillis'),
        'passthroughBehavior': integ.get('passthroughBehavior'),
        'requestParameters': integ.get('requestParameters', {}),
        'responses': integ.get('responses', {})
    }

def extract_lambda_function(uri):
    """Extracts just the function name from Lambda ARN for comparison"""
    if not uri or 'lambda' not in uri.lower():
        return uri
    # arn:aws:lambda:us-east-1:123456:function/my-function-name
    parts = uri.split(':function/')
    if len(parts) > 1:
        return parts[1].split('/')[0]  # Get function name
    return uri

def render_api_gateway_dashboard(src_json, tgt_json):
    """Compares two API Gateway exports"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    src_paths = src_json.get('paths', {})
    tgt_paths = tgt_json.get('paths', {})
    
    # Metrics
    total_paths_src = len(src_paths)
    total_paths_tgt = len(tgt_paths)
    missing_paths = []
    extra_paths = []
    method_issues = []
    integration_issues = []
    
    # --- PATH ANALYSIS ---
    all_paths = sorted(set(src_paths.keys()) | set(tgt_paths.keys()))
    
    for path in all_paths:
        # Missing in target
        if path not in tgt_paths:
            missing_paths.append(path)
            report["Critical"].append(f"Missing Path: {path}")
            continue
        
        # Extra in target (exists in target but not source)
        if path not in src_paths:
            extra_paths.append(path)
            report["Info"].append(f"Extra Path in Target: {path}")
            continue
        
        # Path exists in both - compare methods
        src_methods = src_paths[path]
        tgt_methods = tgt_paths[path]
        
        all_methods = set(src_methods.keys()) | set(tgt_methods.keys())
        
        for method in all_methods:
            if method in ['parameters', 'x-amazon-apigateway-any-method']:
                continue  # Skip metadata
            
            method_upper = method.upper()
            
            # Missing method in target
            if method not in tgt_methods:
                method_issues.append((path, method_upper, "Missing in Target"))
                report["Critical"].append(f"Missing Method: {path} [{method_upper}]")
                continue
            
            # Extra method in target
            if method not in src_methods:
                method_issues.append((path, method_upper, "Extra in Target"))
                report["Info"].append(f"Extra Method in Target: {path} [{method_upper}]")
                continue
            
            # Compare integrations
            src_integ = normalize_integration(src_methods[method])
            tgt_integ = normalize_integration(tgt_methods[method])
            
            if not src_integ or not tgt_integ:
                continue
            
            issues = []
            
            # Type mismatch
            if src_integ['type'] != tgt_integ['type']:
                issues.append(f"Type: {src_integ['type']} → {tgt_integ['type']}")
                report["Critical"].append(f"{path} [{method_upper}] Integration Type Mismatch")
            
            # URI comparison (smart Lambda comparison)
            src_uri = src_integ['uri']
            tgt_uri = tgt_integ['uri']
            src_func = extract_lambda_function(src_uri)
            tgt_func = extract_lambda_function(tgt_uri)
            
            if src_func != tgt_func:
                issues.append(f"URI: {src_func} → {tgt_func}")
                report["Critical"].append(f"{path} [{method_upper}] Lambda Function Mismatch")
            
            # Timeout comparison
            src_timeout = src_integ.get('timeoutInMillis', 29000)
            tgt_timeout = tgt_integ.get('timeoutInMillis', 29000)
            if src_timeout != tgt_timeout:
                issues.append(f"Timeout: {src_timeout}ms → {tgt_timeout}ms")
                report["Warnings"].append(f"{path} [{method_upper}] Timeout Difference")
            
            # HTTP Method mismatch
            if src_integ['httpMethod'] != tgt_integ['httpMethod']:
                issues.append(f"HTTP Method: {src_integ['httpMethod']} → {tgt_integ['httpMethod']}")
                report["Critical"].append(f"{path} [{method_upper}] HTTP Method Mismatch")
            
            if issues:
                integration_issues.append((path, method_upper, issues))
    
    # --- RENDER UI ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Paths", f"{total_paths_tgt}", delta=f"{total_paths_tgt - total_paths_src}" if total_paths_src != total_paths_tgt else None)
    col2.metric("Missing Paths", len(missing_paths))
    col3.metric("Method Issues", len(method_issues))
    col4.metric("Integration Issues", len(integration_issues))
    
    st.divider()
    
    # Critical Issues
    if missing_paths or any(issue[2] == "Missing in Target" for issue in method_issues) or integration_issues:
        st.error(f"🔴 Critical Issues Found")
        
        # Missing Paths
        if missing_paths:
            st.markdown("### Missing Endpoints")
            for path in missing_paths:
                st.markdown(f"""
                <div class='resource-card' style='border-left: 5px solid #c62828;'>
                    <b>❌ Missing Path</b><br>
                    <code>{path}</code><br>
                    <span class='badge-crit'>This entire endpoint is missing in Target</span>
                </div>
                """, unsafe_allow_html=True)
        
        # Missing Methods
        missing_methods = [m for m in method_issues if m[2] == "Missing in Target"]
        if missing_methods:
            st.markdown("### Missing Methods")
            for path, method, _ in missing_methods:
                st.markdown(f"""
                <div class='resource-card' style='border-left: 5px solid #d32f2f;'>
                    <b>⚠️ Missing Method</b><br>
                    <code>{path}</code> <span class='badge-crit'>[{method}]</span><br>
                    Path exists but this HTTP method is not configured
                </div>
                """, unsafe_allow_html=True)
        
        # Integration Issues
        if integration_issues:
            st.markdown("### Integration Configuration Issues")
            for path, method, issues_list in integration_issues:
                issues_html = "<br>".join([f"• {i}" for i in issues_list])
                st.markdown(f"""
                <div class='resource-card' style='border-left: 5px solid #f57c00;'>
                    <b>🔧 Configuration Drift</b><br>
                    <code>{path}</code> <span class='badge-warn'>[{method}]</span><br>
                    <hr style='margin: 8px 0'>
                    {issues_html}
                </div>
                """, unsafe_allow_html=True)
    
    # Info - Extra paths/methods
    if extra_paths or any(issue[2] == "Extra in Target" for issue in method_issues):
        with st.expander(f"ℹ️ Extra Resources in Target ({len(extra_paths)} paths, {len([m for m in method_issues if m[2] == 'Extra in Target'])} methods)"):
            if extra_paths:
                st.markdown("**Extra Paths:**")
                for path in extra_paths:
                    st.code(path)
            extra_methods = [m for m in method_issues if m[2] == "Extra in Target"]
            if extra_methods:
                st.markdown("**Extra Methods:**")
                for path, method, _ in extra_methods:
                    st.code(f"{path} [{method}]")
    
    # Success state
    if not missing_paths and not method_issues and not integration_issues:
        st.success("✅ API Gateway Configurations Match Perfectly!")
    
    return report


# ==========================================
# REPLACE YOUR EXISTING "with tab3:" SECTION WITH THIS
# ==========================================

with tab3:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["api_gw"].keys()))
    
    if not src_list:
        st.info("No API Gateway exports found in source dump.")
        st.stop()
    
    sel_src = col_sel_1.selectbox("Source API", src_list, key="api_src")
    tgt_list = sorted(list(data_b["api_gw"].keys()))
    
    if not tgt_list:
        st.info("No API Gateway exports found in target dump.")
        st.stop()
    
    predicted = find_best_match(sel_src, tgt_list)
    try: 
        idx = tgt_list.index(predicted) if predicted else 0
    except: 
        idx = 0
    
    sel_tgt = col_sel_2.selectbox("Target API", tgt_list, index=idx, key="api_tgt")
    
    if sel_src and sel_tgt:
        st.subheader(f"Comparing: {sel_src} → {sel_tgt}")
        rpt = render_api_gateway_dashboard(data_a["api_gw"][sel_src], data_b["api_gw"][sel_tgt])
        
        # Download Report
        md = f"# API Gateway Report: {sel_src} vs {sel_tgt}\n\n"
        for category, items in rpt.items():
            if items:
                md += f"## {category}\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"
        
        st.download_button("📥 Download API Gateway Report", md, "api_gateway_report.md", key="dl_api")
