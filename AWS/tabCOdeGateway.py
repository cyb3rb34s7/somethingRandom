# === TAB 3: API GATEWAY ===
with tab3:
    st.subheader("⚡ API Gateway Audit")
    st.info("Compares Routes, HTTP Methods, and Integration Settings (Timeouts/Types).")
    
    col_sel_1, col_sel_2 = st.columns(2)
    
    # 1. Source Selector
    src_list = sorted(list(data_a["api_gw"].keys()))
    sel_src = col_sel_1.selectbox("Select Source API", src_list, key="api_src")
    
    # 2. Auto-Predict Target
    tgt_list = sorted(list(data_b["api_gw"].keys()))
    predicted_tgt = find_best_match(sel_src, tgt_list)
    
    # 3. Target Selector
    try: idx = tgt_list.index(predicted_tgt) if predicted_tgt else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Select Target API", tgt_list, index=idx, key="api_tgt")
    
    if predicted_tgt and predicted_tgt == sel_tgt:
        col_sel_2.caption(f"✨ Auto-matched: {predicted_tgt}")

    # 4. Render Dashboard
    if sel_src and sel_tgt:
        j_a = data_a["api_gw"][sel_src]
        j_b = data_b["api_gw"][sel_tgt]
        
        report = render_api_dashboard(j_a, j_b)
        
        # Download Report
        md_text = f"# API Gateway Audit: {sel_src} vs {sel_tgt}\n\n"
        if report["Missing Routes"]:
            md_text += "## 🔴 Missing Routes\n" + "\n".join([f"- {r}" for r in report["Missing Routes"]]) + "\n\n"
        if report["Integration Drift"]:
            md_text += "## 🟡 Configuration Drift\n" + "\n".join([f"- {r}" for r in report["Integration Drift"]]) + "\n\n"
            
        st.download_button("📥 Download API Report", md_text, "api_report.md")
