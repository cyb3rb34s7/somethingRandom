# ==========================================
# COMPLETE TAB IMPLEMENTATIONS
# Replace your existing tab definitions with these
# ==========================================

# Update the tab creation line to include all tabs:
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📦 ECS Task Definitions", 
    "🪣 S3 Buckets", 
    "⚡ API Gateway",
    "🔧 Lambda Functions",
    "📬 SQS & SNS",
    "⚖️ Load Balancers",
    "🔒 Security Groups",
    "🔐 IAM Roles",
    "📄 S3 Files"
])

# TAB 1: ECS (Existing - Keep as is)
with tab1:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["ecs_td"].keys()))
    if not src_list:
        st.info("No ECS Task Definitions found"); st.stop()
    sel_src = col_sel_1.selectbox("Source TD", src_list)
    tgt_list = sorted(list(data_b["ecs_td"].keys()))
    predicted = find_best_match(sel_src, tgt_list)
    try: idx = tgt_list.index(predicted) if predicted else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Target TD", tgt_list, index=idx)
    ctx = st.radio("Region Context", ["Generic", "EU (Ireland)", "US (Oregon)"], horizontal=True)
    
    if sel_src and sel_tgt:
        rpt = render_ecs_dashboard(data_a["ecs_td"][sel_src], data_b["ecs_td"][sel_tgt], ctx)
        md = f"# ECS Report: {sel_src} vs {sel_tgt}\n\n"
        for k, v in rpt.items():
            if v: md += f"## {k}\n" + "\n".join([f"- {i}" for i in v]) + "\n\n"
        st.download_button("📥 Download ECS Report", md, "ecs_report.md")

# TAB 2: S3 Buckets (Existing - Keep as is)
with tab2:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["s3"].keys()))
    if not src_list:
        st.info("No S3 Buckets found"); st.stop()
    sel_src = col_sel_1.selectbox("Source Bucket", src_list)
    tgt_list = sorted(list(data_b["s3"].keys()))
    predicted = find_best_match(sel_src, tgt_list)
    try: idx = tgt_list.index(predicted) if predicted else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Target Bucket", tgt_list, index=idx)
    
    if sel_src and sel_tgt:
        rpt = render_s3_dashboard(data_a["s3"][sel_src], data_b["s3"][sel_tgt])
        md = f"# S3 Report: {sel_src} vs {sel_tgt}\n\n"
        for i in rpt["Risks"]: md += f"- [RISK] {i}\n"
        st.download_button("📥 Download S3 Report", md, "s3_report.md")

# TAB 3: API Gateway (Existing - Keep as is)
with tab3:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a["api_gw"].keys()))
    if not src_list:
        st.info("No API Gateway exports found"); st.stop()
    tgt_list = sorted(list(data_b["api_gw"].keys()))
    sel_src = col_sel_1.selectbox("Source API", src_list, key="api_src")
    predicted = find_best_match(sel_src, tgt_list)
    try: idx = tgt_list.index(predicted) if predicted else 0
    except: idx = 0
    sel_tgt = col_sel_2.selectbox("Target API", tgt_list, index=idx, key="api_tgt")
    
    if sel_src and sel_tgt:
        st.subheader(f"Comparing: {sel_src} → {sel_tgt}")
        rpt = render_api_gateway_dashboard(data_a["api_gw"][sel_src], data_b["api_gw"][sel_tgt])
        md = f"# API Gateway Report: {sel_src} vs {sel_tgt}\n\n"
        for category, items in rpt.items():
            if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
        st.download_button("📥 Download API Gateway Report", md, "api_gateway_report.md", key="dl_api")

# TAB 4: Lambda Functions (NEW)
with tab4:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a.get("lambda", {}).keys()))
    
    if not src_list:
        st.info("No Lambda functions found in source dump.")
    else:
        sel_src = col_sel_1.selectbox("Source Lambda", src_list, key="lambda_src")
        tgt_list = sorted(list(data_b.get("lambda", {}).keys()))
        
        if not tgt_list:
            st.info("No Lambda functions found in target dump.")
        else:
            predicted = find_best_match(sel_src, tgt_list)
            try: idx = tgt_list.index(predicted) if predicted else 0
            except: idx = 0
            sel_tgt = col_sel_2.selectbox("Target Lambda", tgt_list, index=idx, key="lambda_tgt")
            
            if sel_src and sel_tgt:
                st.subheader(f"⚡ Comparing: {sel_src} → {sel_tgt}")
                rpt = render_lambda_dashboard(data_a["lambda"][sel_src], data_b["lambda"][sel_tgt])
                
                md = f"# Lambda Report: {sel_src} vs {sel_tgt}\n\n"
                for category, items in rpt.items():
                    if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
                st.download_button("📥 Download Lambda Report", md, "lambda_report.md", key="dl_lambda")

# TAB 5: SQS & SNS (NEW)
with tab5:
    sub_tab1, sub_tab2 = st.tabs(["📬 SQS Queues", "📢 SNS Topics"])
    
    # SQS Sub-tab
    with sub_tab1:
        col_sel_1, col_sel_2 = st.columns(2)
        src_list = sorted(list(data_a.get("sqs", {}).keys()))
        
        if not src_list:
            st.info("No SQS queues found in source dump.")
        else:
            sel_src = col_sel_1.selectbox("Source Queue", src_list, key="sqs_src")
            tgt_list = sorted(list(data_b.get("sqs", {}).keys()))
            
            if not tgt_list:
                st.info("No SQS queues found in target dump.")
            else:
                predicted = find_best_match(sel_src, tgt_list)
                try: idx = tgt_list.index(predicted) if predicted else 0
                except: idx = 0
                sel_tgt = col_sel_2.selectbox("Target Queue", tgt_list, index=idx, key="sqs_tgt")
                
                if sel_src and sel_tgt:
                    rpt = render_sqs_dashboard(data_a["sqs"][sel_src], data_b["sqs"][sel_tgt])
                    
                    md = f"# SQS Report: {sel_src} vs {sel_tgt}\n\n"
                    for category, items in rpt.items():
                        if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
                    st.download_button("📥 Download SQS Report", md, "sqs_report.md", key="dl_sqs")
    
    # SNS Sub-tab
    with sub_tab2:
        col_sel_1, col_sel_2 = st.columns(2)
        src_list = sorted(list(data_a.get("sns", {}).keys()))
        
        if not src_list:
            st.info("No SNS topics found in source dump.")
        else:
            sel_src = col_sel_1.selectbox("Source Topic", src_list, key="sns_src")
            tgt_list = sorted(list(data_b.get("sns", {}).keys()))
            
            if not tgt_list:
                st.info("No SNS topics found in target dump.")
            else:
                predicted = find_best_match(sel_src, tgt_list)
                try: idx = tgt_list.index(predicted) if predicted else 0
                except: idx = 0
                sel_tgt = col_sel_2.selectbox("Target Topic", tgt_list, index=idx, key="sns_tgt")
                
                if sel_src and sel_tgt:
                    rpt = render_sns_dashboard(data_a["sns"][sel_src], data_b["sns"][sel_tgt])
                    
                    md = f"# SNS Report: {sel_src} vs {sel_tgt}\n\n"
                    for category, items in rpt.items():
                        if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
                    st.download_button("📥 Download SNS Report", md, "sns_report.md", key="dl_sns")

# TAB 6: Load Balancers (NEW)
with tab6:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a.get("lb", {}).keys()))
    
    if not src_list:
        st.info("No Load Balancers found in source dump.")
    else:
        sel_src = col_sel_1.selectbox("Source LB", src_list, key="lb_src")
        tgt_list = sorted(list(data_b.get("lb", {}).keys()))
        
        if not tgt_list:
            st.info("No Load Balancers found in target dump.")
        else:
            predicted = find_best_match(sel_src, tgt_list)
            try: idx = tgt_list.index(predicted) if predicted else 0
            except: idx = 0
            sel_tgt = col_sel_2.selectbox("Target LB", tgt_list, index=idx, key="lb_tgt")
            
            if sel_src and sel_tgt:
                rpt = render_load_balancer_dashboard(data_a["lb"][sel_src], data_b["lb"][sel_tgt])
                
                md = f"# Load Balancer Report: {sel_src} vs {sel_tgt}\n\n"
                for category, items in rpt.items():
                    if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
                st.download_button("📥 Download LB Report", md, "lb_report.md", key="dl_lb")

# TAB 7: Security Groups (NEW)
with tab7:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a.get("sg", {}).keys()))
    
    if not src_list:
        st.info("No Security Groups found in source dump.")
    else:
        sel_src = col_sel_1.selectbox("Source SG", src_list, key="sg_src")
        tgt_list = sorted(list(data_b.get("sg", {}).keys()))
        
        if not tgt_list:
            st.info("No Security Groups found in target dump.")
        else:
            predicted = find_best_match(sel_src, tgt_list)
            try: idx = tgt_list.index(predicted) if predicted else 0
            except: idx = 0
            sel_tgt = col_sel_2.selectbox("Target SG", tgt_list, index=idx, key="sg_tgt")
            
            if sel_src and sel_tgt:
                rpt = render_security_group_dashboard(data_a["sg"][sel_src], data_b["sg"][sel_tgt])
                
                md = f"# Security Group Report: {sel_src} vs {sel_tgt}\n\n"
                for category, items in rpt.items():
                    if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
                st.download_button("📥 Download SG Report", md, "sg_report.md", key="dl_sg")

# TAB 8: IAM Roles (NEW)
with tab8:
    col_sel_1, col_sel_2 = st.columns(2)
    src_list = sorted(list(data_a.get("iam", {}).keys()))
    
    if not src_list:
        st.info("No IAM Roles found in source dump.")
    else:
        sel_src = col_sel_1.selectbox("Source Role", src_list, key="iam_src")
        tgt_list = sorted(list(data_b.get("iam", {}).keys()))
        
        if not tgt_list:
            st.info("No IAM Roles found in target dump.")
        else:
            predicted = find_best_match(sel_src, tgt_list)
            try: idx = tgt_list.index(predicted) if predicted else 0
            except: idx = 0
            sel_tgt = col_sel_2.selectbox("Target Role", tgt_list, index=idx, key="iam_tgt")
            
            if sel_src and sel_tgt:
                rpt = render_iam_role_dashboard(data_a["iam"][sel_src], data_b["iam"][sel_tgt])
                
                md = f"# IAM Role Report: {sel_src} vs {sel_tgt}\n\n"
                for category, items in rpt.items():
                    if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
                st.download_button("📥 Download IAM Report", md, "iam_report.md", key="dl_iam")

# TAB 9: S3 Files (NEW)
with tab9:
    st.markdown("### 📄 S3 Configuration Files Comparison")
    
    # Find S3 file content folders
    src_folders = [k for k in os.listdir(path_a) if k.startswith("s3_file_contents")] if os.path.exists(path_a) else []
    tgt_folders = [k for k in os.listdir(path_b) if k.startswith("s3_file_contents")] if os.path.exists(path_b) else []
    
    if not src_folders:
        st.info("No S3 file contents found in source dump. Run collector with --s3-files-config option.")
    elif not tgt_folders:
        st.info("No S3 file contents found in target dump. Run collector with --s3-files-config option.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Source Environment**")
            sel_src_folder = st.selectbox("Select Folder", src_folders, key="s3files_src")
        
        with col2:
            st.markdown("**Target Environment**")
            # Try to auto-match
            predicted = find_best_match(sel_src_folder, tgt_folders)
            try: idx = tgt_folders.index(predicted) if predicted else 0
            except: idx = 0
            sel_tgt_folder = st.selectbox("Select Folder", tgt_folders, index=idx, key="s3files_tgt")
        
        if st.button("🔍 Compare Files", type="primary"):
            src_folder_path = os.path.join(path_a, sel_src_folder)
            tgt_folder_path = os.path.join(path_b, sel_tgt_folder)
            
            rpt = render_s3_files_comparison(src_folder_path, tgt_folder_path)
            
            md = f"# S3 Files Report: {sel_src_folder} vs {sel_tgt_folder}\n\n"
            for category, items in rpt.items():
                if items: md += f"## {category}\n" + "\n".join([f"- {i}" for i in items]) + "\n\n"
            st.download_button("📥 Download S3 Files Report", md, "s3_files_report.md", key="dl_s3files")
