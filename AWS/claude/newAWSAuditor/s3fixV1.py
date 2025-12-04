# ==========================================
# FIX 1: API Gateway - Keep Original Behavior
# Replace the scan_api_gateway function in collector.py
# ==========================================

def scan_api_gateway():
    print(f"\n🌐 SCANNING API GATEWAY")
    apig = boto3.client('apigateway', region_name=CURRENT_REGION)
    try:
        apis = apig.get_rest_apis()['items']
        for api in apis:
            api_id = api['id']
            name = api['name']
            
            # Get all stages
            stages = apig.get_stages(restApiId=api_id)
            if not stages['item']:
                print(f"   ⚠️ Skipping {name}: No deployed stages found.")
                continue
                
            # Export ALL stages (usually just one per environment)
            for stage_info in stages['item']:
                stage_name = stage_info['stageName']
                print(f"   ... Exporting {name} (Stage: {stage_name})")

                try:
                    export = apig.get_export(
                        restApiId=api_id,
                        stageName=stage_name,
                        exportType='oas30',
                        parameters={'extensions': 'integrations'}
                    )
                    body = json.loads(export['body'].read())
                    # Save with stage name included to avoid overwrites
                    save_json("api_gateway", f"{name}_{stage_name}", body)
                except Exception as e:
                    print(f"   ❌ Export Failed for {name} [{stage_name}]: {e}")

    except Exception as e: 
        print(f"API GW Error: {e}")


# ==========================================
# FIX 2: S3 Files Tab - Corrected Implementation
# Replace the entire Tab 9 section in your dashboard
# ==========================================

# TAB 9: S3 Files (FIXED)
with tab9:
    st.markdown("### 📄 S3 Configuration Files Comparison")
    
    # Look for s3_file_contents folder within the dump directories
    src_s3_base = os.path.join(path_a, "s3_file_contents") if path_a else None
    tgt_s3_base = os.path.join(path_b, "s3_file_contents") if path_b else None
    
    # Get subfolders within s3_file_contents
    src_folders = []
    tgt_folders = []
    
    if src_s3_base and os.path.exists(src_s3_base):
        src_folders = [f for f in os.listdir(src_s3_base) if os.path.isdir(os.path.join(src_s3_base, f))]
    
    if tgt_s3_base and os.path.exists(tgt_s3_base):
        tgt_folders = [f for f in os.listdir(tgt_s3_base) if os.path.isdir(os.path.join(tgt_s3_base, f))]
    
    if not src_folders:
        st.info("No S3 file contents found in source dump. Run collector with --s3-files-config option.")
    elif not tgt_folders:
        st.info("No S3 file contents found in target dump. Run collector with --s3-files-config option.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Source Environment**")
            sel_src_folder = st.selectbox("Select Folder", src_folders, key="s3files_src")
            if sel_src_folder:
                src_index_path = os.path.join(src_s3_base, sel_src_folder, "_index.json")
                if os.path.exists(src_index_path):
                    with open(src_index_path, 'r') as f:
                        src_idx = json.load(f)
                    st.caption(f"📦 Bucket: {src_idx.get('bucket', 'N/A')}")
                    st.caption(f"📁 Prefix: {src_idx.get('prefix', 'N/A')}")
                    st.caption(f"📊 Files: {src_idx.get('total_files', 0)} total, {src_idx.get('downloaded_files', 0)} downloaded")
        
        with col2:
            st.markdown("**Target Environment**")
            # Try to auto-match
            predicted = find_best_match(sel_src_folder, tgt_folders)
            try: 
                idx = tgt_folders.index(predicted) if predicted else 0
            except: 
                idx = 0
            sel_tgt_folder = st.selectbox("Select Folder", tgt_folders, index=idx, key="s3files_tgt")
            if sel_tgt_folder:
                tgt_index_path = os.path.join(tgt_s3_base, sel_tgt_folder, "_index.json")
                if os.path.exists(tgt_index_path):
                    with open(tgt_index_path, 'r') as f:
                        tgt_idx = json.load(f)
                    st.caption(f"📦 Bucket: {tgt_idx.get('bucket', 'N/A')}")
                    st.caption(f"📁 Prefix: {tgt_idx.get('prefix', 'N/A')}")
                    st.caption(f"📊 Files: {tgt_idx.get('total_files', 0)} total, {tgt_idx.get('downloaded_files', 0)} downloaded")
        
        st.divider()
        
        if st.button("🔍 Compare Files", type="primary"):
            src_folder_path = os.path.join(src_s3_base, sel_src_folder)
            tgt_folder_path = os.path.join(tgt_s3_base, sel_tgt_folder)
            
            rpt = render_s3_files_comparison(src_folder_path, tgt_folder_path)
            
            # Download report
            if rpt:
                md = f"# S3 Files Report\n\n"
                md += f"**Source:** {sel_src_folder}\n"
                md += f"**Target:** {sel_tgt_folder}\n\n"
                
                for category, items in rpt.items():
                    if items: 
                        md += f"## {category}\n"
                        for item in items:
                            md += f"- {item}\n"
                        md += "\n"
                
                st.download_button(
                    "📥 Download S3 Files Report", 
                    md, 
                    "s3_files_report.md", 
                    key="dl_s3files"
                )


# ==========================================
# FIX 3: Add missing import at top of dashboard
# Add this with your other imports
# ==========================================

import os  # Make sure this is imported at the top
