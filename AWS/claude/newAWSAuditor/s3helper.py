# ==========================================
# S3 FILES COMPARISON HELPERS
# Add these after the IAM helpers
# ==========================================

def find_matching_file_fuzzy(source_filename, target_files_dict, has_version=False):
    """
    Fuzzy match files, handling version patterns
    Returns: (matched_filename, match_type) or (None, None)
    """
    if not has_version:
        # Exact match
        if source_filename in target_files_dict:
            return source_filename, "exact"
        return None, None
    
    # Extract base name (remove version pattern)
    base_src = re.sub(r'_v?\d+\.\d+\.\d+', '', source_filename)
    
    # Find files matching the pattern
    for target_file in target_files_dict.keys():
        base_tgt = re.sub(r'_v?\d+\.\d+\.\d+', '', target_file)
        if base_src == base_tgt:
            return target_file, "version_pattern"
    
    # Fallback to similarity
    from difflib import get_close_matches
    matches = get_close_matches(source_filename, target_files_dict.keys(), n=1, cutoff=0.8)
    if matches:
        return matches[0], "fuzzy"
    
    return None, None


def compare_json_deep(src_json, tgt_json, path=""):
    """Deep comparison of two JSON objects"""
    diffs = {
        "missing": [],
        "extra": [],
        "changed": []
    }
    
    # Keys in source but not target
    for key in src_json:
        if key not in tgt_json:
            full_path = f"{path}.{key}" if path else key
            diffs["missing"].append(full_path)
    
    # Keys in target but not source
    for key in tgt_json:
        if key not in src_json:
            full_path = f"{path}.{key}" if path else key
            diffs["extra"].append(full_path)
    
    # Compare values for common keys
    for key in src_json:
        if key in tgt_json:
            val_src = src_json[key]
            val_tgt = tgt_json[key]
            full_path = f"{path}.{key}" if path else key
            
            if isinstance(val_src, dict) and isinstance(val_tgt, dict):
                nested = compare_json_deep(val_src, val_tgt, full_path)
                diffs["missing"].extend(nested["missing"])
                diffs["extra"].extend(nested["extra"])
                diffs["changed"].extend(nested["changed"])
            elif val_src != val_tgt:
                diffs["changed"].append({
                    "key": full_path,
                    "source": val_src,
                    "target": val_tgt
                })
    
    return diffs


def load_s3_folder_data(data_dict, folder_key):
    """Load S3 folder scan data"""
    # data_dict is the loaded dump data
    # folder_key is like "s3_file_contents_xyz_dev_content_dev_"
    
    for key in data_dict.keys():
        if key.startswith("s3_file_contents"):
            # This is an S3 folder scan
            return data_dict[key]
    return None


def render_s3_files_comparison(src_folder_path, tgt_folder_path):
    """
    Compare S3 files from two folder scans
    src_folder_path and tgt_folder_path are paths to the actual folders
    """
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    # Load _index.json files
    src_index_path = os.path.join(src_folder_path, "_index.json")
    tgt_index_path = os.path.join(tgt_folder_path, "_index.json")
    
    if not os.path.exists(src_index_path):
        st.error(f"❌ Source index not found: {src_index_path}")
        return report
    
    if not os.path.exists(tgt_index_path):
        st.error(f"❌ Target index not found: {tgt_index_path}")
        return report
    
    with open(src_index_path, 'r') as f:
        src_index = json.load(f)
    
    with open(tgt_index_path, 'r') as f:
        tgt_index = json.load(f)
    
    # Build file dictionaries
    src_files = {f['filename']: f for f in src_index['files']}
    tgt_files = {f['filename']: f for f in tgt_index['files']}
    
    # Summary metrics
    st.subheader("📊 Comparison Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    matched_count = 0
    differ_count = 0
    missing_count = 0
    
    # Quick scan for counts
    for src_file in src_files.keys():
        if src_file in tgt_files:
            src_hash = src_files[src_file].get('content_hash')
            tgt_hash = tgt_files[src_file].get('content_hash')
            if src_hash and tgt_hash:
                if src_hash == tgt_hash:
                    matched_count += 1
                else:
                    differ_count += 1
        else:
            # Try fuzzy match for version patterns
            has_version = bool(src_files[src_file].get('version_detected'))
            matched, _ = find_matching_file_fuzzy(src_file, tgt_files, has_version)
            if not matched:
                missing_count += 1
    
    col1.metric("Total Files", len(src_files))
    col2.metric("Identical", matched_count, delta=None)
    col3.metric("Different", differ_count, delta=None)
    col4.metric("Missing", missing_count, delta=None)
    
    st.divider()
    
    # Detailed comparison
    identical_files = []
    different_files = []
    missing_files = []
    
    for src_filename, src_file in src_files.items():
        # Try to find matching file
        has_version = bool(src_file.get('version_detected'))
        tgt_filename, match_type = find_matching_file_fuzzy(src_filename, tgt_files, has_version)
        
        if not tgt_filename:
            # File missing in target
            missing_files.append(src_filename)
            continue
        
        tgt_file = tgt_files[tgt_filename]
        
        # Compare hashes
        src_hash = src_file.get('content_hash')
        tgt_hash = tgt_file.get('content_hash')
        
        if src_hash and tgt_hash and src_hash == tgt_hash:
            identical_files.append((src_filename, tgt_filename, src_file, tgt_file))
        else:
            different_files.append((src_filename, tgt_filename, src_file, tgt_file, match_type))
    
    # Render Missing Files (CRITICAL)
    if missing_files:
        st.error(f"🔴 Missing Files in Target ({len(missing_files)})")
        for filename in missing_files:
            src_file = src_files[filename]
            st.markdown(f"""
            <div class='resource-card' style='border-left: 5px solid #c62828;'>
                <b>❌ {filename}</b><br>
                <b>Status:</b> MISSING IN TARGET<br>
                <b>Size:</b> {src_file['size']} bytes<br>
                <b>Last Modified:</b> {src_file['last_modified']}<br>
                <span class='badge-crit'>CRITICAL: Required file not found</span>
            </div>
            """, unsafe_allow_html=True)
            report["Critical"].append(f"Missing file: {filename}")
    
    # Render Different Files
    if different_files:
        st.warning(f"⚠️ Files with Differences ({len(different_files)})")
        
        for src_filename, tgt_filename, src_file, tgt_file, match_type in different_files:
            with st.expander(f"📄 {src_filename} {'[Version Match]' if match_type == 'version_pattern' else ''}"):
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.markdown("**Source (Dev)**")
                    st.caption(f"Size: {src_file['size']} bytes")
                    st.caption(f"Modified: {src_file['last_modified']}")
                    if 'version_detected' in src_file:
                        st.caption(f"Version: {src_file['version_detected']}")
                
                with col_info2:
                    st.markdown("**Target (STG)**")
                    st.caption(f"Size: {tgt_file['size']} bytes")
                    st.caption(f"Modified: {tgt_file['last_modified']}")
                    if 'version_detected' in tgt_file:
                        st.caption(f"Version: {tgt_file['version_detected']}")
                
                # For JSON files, show deep diff
                if src_filename.endswith('.json') and src_file.get('downloaded') and tgt_file.get('downloaded'):
                    src_content_path = os.path.join(src_folder_path, src_filename)
                    tgt_content_path = os.path.join(tgt_folder_path, tgt_filename)
                    
                    try:
                        with open(src_content_path, 'r') as f:
                            src_json = json.load(f)
                        with open(tgt_content_path, 'r') as f:
                            tgt_json = json.load(f)
                        
                        diffs = compare_json_deep(src_json, tgt_json)
                        
                        if diffs['missing']:
                            st.markdown("**🔴 Missing Keys in Target:**")
                            for key in diffs['missing'][:10]:  # Show max 10
                                st.code(f"- {key}")
                            if len(diffs['missing']) > 10:
                                st.caption(f"... and {len(diffs['missing']) - 10} more")
                            report["Critical"].append(f"{src_filename}: {len(diffs['missing'])} missing keys")
                        
                        if diffs['extra']:
                            st.markdown("**🟢 Extra Keys in Target:**")
                            for key in diffs['extra'][:5]:
                                st.code(f"+ {key}")
                            if len(diffs['extra']) > 5:
                                st.caption(f"... and {len(diffs['extra']) - 5} more")
                        
                        if diffs['changed']:
                            st.markdown("**🟡 Value Differences:**")
                            for diff in diffs['changed'][:5]:
                                st.markdown(f"**`{diff['key']}`**")
                                col_a, col_b = st.columns(2)
                                col_a.code(f"Src: {diff['source']}")
                                col_b.code(f"Tgt: {diff['target']}")
                            if len(diffs['changed']) > 5:
                                st.caption(f"... and {len(diffs['changed']) - 5} more")
                            report["Warnings"].append(f"{src_filename}: {len(diffs['changed'])} value differences")
                        
                        # Download buttons
                        col_dl1, col_dl2 = st.columns(2)
                        col_dl1.download_button(
                            "📥 Download Source",
                            data=json.dumps(src_json, indent=2),
                            file_name=f"source_{src_filename}",
                            key=f"dl_src_{src_filename}"
                        )
                        col_dl2.download_button(
                            "📥 Download Target",
                            data=json.dumps(tgt_json, indent=2),
                            file_name=f"target_{tgt_filename}",
                            key=f"dl_tgt_{tgt_filename}"
                        )
                        
                    except Exception as e:
                        st.error(f"Could not compare JSON: {e}")
                
                # For DOCX files, show version comparison
                elif src_filename.endswith('.docx'):
                    src_ver = src_file.get('version_detected', 'unknown')
                    tgt_ver = tgt_file.get('version_detected', 'unknown')
                    
                    if src_ver != 'unknown' and tgt_ver != 'unknown':
                        try:
                            from packaging import version
                            if version.parse(src_ver) > version.parse(tgt_ver):
                                st.warning(f"⚠️ Target has OLDER version ({tgt_ver} < {src_ver})")
                                report["Warnings"].append(f"{src_filename}: Target version older")
                            elif version.parse(src_ver) < version.parse(tgt_ver):
                                st.info(f"ℹ️ Target has NEWER version ({tgt_ver} > {src_ver})")
                                report["Info"].append(f"{src_filename}: Target version newer")
                            else:
                                st.success(f"✅ Same version: {src_ver}")
                        except:
                            st.info(f"Versions: Source={src_ver}, Target={tgt_ver}")
                    else:
                        st.info("Version comparison not available")
                
                report["Info"].append(f"Compared: {src_filename}")
    
    # Render Identical Files (Collapsed)
    if identical_files:
        with st.expander(f"🟢 Identical Files ({len(identical_files)})"):
            for src_filename, tgt_filename, src_file, tgt_file in identical_files:
                st.markdown(f"""
                <div class='resource-card'>
                    <b>✅ {src_filename}</b><br>
                    Size: {src_file['size']} bytes | Hash: {src_file['content_hash'][:16]}...
                </div>
                """, unsafe_allow_html=True)
    
    return report
