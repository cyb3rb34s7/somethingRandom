def render_api_dashboard(json_a, json_b):
    report_data = {"Missing Routes": [], "Integration Drift": [], "Config": []}
    
    # 1. Parse Paths
    paths_a = json_a.get('paths', {})
    paths_b = json_b.get('paths', {})
    
    all_paths = sorted(set(paths_a.keys()) | set(paths_b.keys()))
    
    # --- METRICS ROW ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Routes (Dev)", len(paths_a))
    c2.metric("Total Routes (Stg)", len(paths_b))
    
    # Calculate Missing
    missing_in_stg = set(paths_a.keys()) - set(paths_b.keys())
    if missing_in_stg:
        c3.markdown(f"**Missing Routes**<br><span class='badge-crit'>{len(missing_in_stg)} DETECTED</span>", unsafe_allow_html=True)
    else:
        c3.markdown(f"**Missing Routes**<br><span class='badge-pass'>NONE</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # --- DRIFT ANALYSIS ---
    rows = []
    
    for path in all_paths:
        # Check Path Existence
        if path not in paths_b:
            rows.append({"Type": "🔴 Route", "Path": path, "Method": "*", "Issue": "Missing in Target", "Dev Value": "Exists", "Stg Value": "Missing"})
            report_data["Missing Routes"].append(path)
            continue
        if path not in paths_a:
            continue
            
        # Check Methods (GET/POST/PUT)
        methods_a = paths_a[path]
        methods_b = paths_b[path]
        
        for method in methods_a:
            if method not in methods_b:
                rows.append({"Type": "🔴 Method", "Path": path, "Method": method.upper(), "Issue": "Method Missing", "Dev Value": "Exists", "Stg Value": "Missing"})
                report_data["Missing Routes"].append(f"{method.upper()} {path}")
            else:
                # DEEP INTEGRATION CHECK
                int_a = normalize_api_integration(methods_a[method])
                int_b = normalize_api_integration(methods_b[method])
                
                # Check Timeout
                if int_a['timeout'] != int_b['timeout']:
                    rows.append({
                        "Type": "🟡 Timeout", 
                        "Path": path, 
                        "Method": method.upper(), 
                        "Issue": "Timeout Drift", 
                        "Dev Value": f"{int_a['timeout']}ms", 
                        "Stg Value": f"{int_b['timeout']}ms"
                    })
                    report_data["Integration Drift"].append(f"{method.upper()} {path}: Timeout {int_a['timeout']}->{int_b['timeout']}")

                # Check Integration Type
                if int_a['type'] != int_b['type']:
                    rows.append({
                        "Type": "🔴 Config", 
                        "Path": path, 
                        "Method": method.upper(), 
                        "Issue": "Integration Type Mismatch", 
                        "Dev Value": int_a['type'], 
                        "Stg Value": int_b['type']
                    })
                    report_data["Integration Drift"].append(f"{method.upper()} {path}: Type {int_a['type']}->{int_b['type']}")

    # DISPLAY TABLE
    if rows:
        df = pd.DataFrame(rows)
        
        # --- THE FIX IS HERE ---
        # We explicitly set 'color: black' to override Streamlit's dark mode text
        def color_api_rows(row):
            if "🔴" in row['Type']: 
                return ['background-color: #ffebee; color: black; font-weight: 500'] * len(row)
            if "🟡" in row['Type']: 
                return ['background-color: #fff3e0; color: black; font-weight: 500'] * len(row)
            return ['color: black'] * len(row) # Default black text for readability

        st.subheader("⚠️ Detected Differences")
        # Apply the style
        st.dataframe(df.style.apply(color_api_rows, axis=1), use_container_width=True, hide_index=True)
    else:
        st.success("✅ All Routes, Methods, and Integration Types match perfectly.")

    # Show URIs in Expander
    with st.expander("🔎 View Integration URIs (Expected Differences)"):
        uri_rows = []
        for path in all_paths:
            if path in paths_a and path in paths_b:
                for method in paths_a[path]:
                    if method in paths_b[path]:
                        ua = normalize_api_integration(paths_a[path][method])['uri']
                        ub = normalize_api_integration(paths_b[path][method])['uri']
                        uri_rows.append({"Path": path, "Method": method.upper(), "Dev URI": ua, "Stg URI": ub})
        st.dataframe(pd.DataFrame(uri_rows), use_container_width=True)

    return report_data
