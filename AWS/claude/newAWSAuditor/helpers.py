# ==========================================
# HELPER FUNCTIONS FOR NEW TABS
# Add these AFTER the existing S3 render function and BEFORE "# 5. MAIN APP LAYOUT"
# ==========================================

import hashlib
import re

# ==========================================
# LAMBDA FUNCTIONS HELPERS
# ==========================================

def parse_lambda_env(lambda_config):
    """Parse Lambda environment variables"""
    vars_map = {}
    env = lambda_config.get('Environment', {})
    if 'Variables' in env:
        for key, value in env['Variables'].items():
            vars_map[key] = {'value': value, 'type': 'Plain'}
    return vars_map

def render_lambda_dashboard(src_lambda, tgt_lambda):
    """Compare two Lambda function configurations"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    # Basic config comparison
    col1, col2, col3 = st.columns(3)
    
    # Runtime
    runtime_src = src_lambda.get('Runtime', 'N/A')
    runtime_tgt = tgt_lambda.get('Runtime', 'N/A')
    if runtime_src == runtime_tgt:
        col1.markdown(f"**Runtime** <span class='badge-pass'>MATCH</span><br>`{runtime_src}`", unsafe_allow_html=True)
    else:
        col1.markdown(f"**Runtime** <span class='badge-warn'>DRIFT</span><br>Src: `{runtime_src}`<br>Tgt: `{runtime_tgt}`", unsafe_allow_html=True)
        report["Warnings"].append(f"Runtime mismatch: {runtime_src} vs {runtime_tgt}")
    
    # Timeout
    timeout_src = src_lambda.get('Timeout', 0)
    timeout_tgt = tgt_lambda.get('Timeout', 0)
    col2.metric("Timeout", f"{timeout_tgt}s", delta=None if timeout_src == timeout_tgt else f"{timeout_tgt - timeout_src}s")
    if timeout_src != timeout_tgt:
        if timeout_tgt < timeout_src:
            report["Critical"].append(f"Timeout reduced: {timeout_src}s → {timeout_tgt}s (may cause timeouts)")
        else:
            report["Warnings"].append(f"Timeout increased: {timeout_src}s → {timeout_tgt}s")
    
    # Memory
    mem_src = src_lambda.get('MemorySize', 0)
    mem_tgt = tgt_lambda.get('MemorySize', 0)
    col3.metric("Memory", f"{mem_tgt}MB", delta=None if mem_src == mem_tgt else f"{mem_tgt - mem_src}MB")
    if mem_src != mem_tgt:
        if mem_tgt < mem_src:
            report["Warnings"].append(f"Memory reduced: {mem_src}MB → {mem_tgt}MB (may cause OOM)")
        else:
            report["Info"].append(f"Memory increased: {mem_src}MB → {mem_tgt}MB")
    
    st.divider()
    
    # DLQ Check
    dlq_src = src_lambda.get('DeadLetterConfig', {}).get('TargetArn')
    dlq_tgt = tgt_lambda.get('DeadLetterConfig', {}).get('TargetArn')
    
    if dlq_src and not dlq_tgt:
        st.error("🔴 Dead Letter Queue: Configured in Source but MISSING in Target")
        report["Critical"].append("DLQ not configured in target")
    elif not dlq_src and not dlq_tgt:
        st.warning("⚠️ Dead Letter Queue: Not configured in either environment")
        report["Warnings"].append("No DLQ configured")
    elif dlq_src == dlq_tgt:
        st.success("✅ Dead Letter Queue: Configured and matching")
    else:
        st.info(f"ℹ️ Dead Letter Queue: Different ARNs (expected for different environments)")
        report["Info"].append("DLQ ARNs differ (expected)")
    
    # VPC Configuration
    vpc_src = src_lambda.get('VpcConfig', {})
    vpc_tgt = tgt_lambda.get('VpcConfig', {})
    
    if vpc_src.get('SubnetIds') and not vpc_tgt.get('SubnetIds'):
        st.error("🔴 VPC: Source has VPC config but Target does not")
        report["Critical"].append("VPC configuration missing in target")
    elif vpc_src.get('SubnetIds') and vpc_tgt.get('SubnetIds'):
        st.success(f"✅ VPC: Both configured ({len(vpc_tgt['SubnetIds'])} subnets)")
    
    # Layers
    layers_src = src_lambda.get('Layers', [])
    layers_tgt = tgt_lambda.get('Layers', [])
    
    if len(layers_src) != len(layers_tgt):
        st.warning(f"⚠️ Layers: Count mismatch (Source: {len(layers_src)}, Target: {len(layers_tgt)})")
        report["Warnings"].append(f"Layer count mismatch: {len(layers_src)} vs {len(layers_tgt)}")
    
    st.divider()
    
    # Environment Variables (reuse ECS logic)
    st.subheader("Environment Variables")
    map_src = parse_lambda_env(src_lambda)
    map_tgt = parse_lambda_env(tgt_lambda)
    all_keys = sorted(set(map_src.keys()) | set(map_tgt.keys()))
    rows = []
    
    for k in all_keys:
        val_src = map_src.get(k, {}).get('value', '-')
        val_tgt = map_tgt.get(k, {}).get('value', '-')
        status = "✅ Match"; category = "Expected"
        
        if val_src == '-':
            status = "❌ Missing in Source"; category = "Critical"
        elif val_tgt == '-':
            status = "❌ Missing in Target"; category = "Critical"
        elif val_src != val_tgt:
            if any(x in k for x in ['_HOST', '_URL', '_URI', '_ARN', '_DB', '_BUCKET']):
                status = "🔄 Config Diff"; category = "Expected"
            else:
                status = "⚠️ Value Drift"; category = "Warnings"
        
        if category != "Expected":
            rows.append({"Variable": k, "Status": status, "Source Value": val_src, "Target Value": val_tgt, "Category": category})
            if category != "Expected":
                report[category].append(f"{k}: {status}")
    
    df = pd.DataFrame(rows)
    if not df.empty:
        crit = df[df['Category'] == "Critical"]
        warn = df[df['Category'] == "Warnings"]
        exp = df[df['Category'] == "Expected"]
        
        if not crit.empty:
            st.error(f"🔴 {len(crit)} Critical Issues")
            st.dataframe(crit.drop(columns=['Category']), use_container_width=True, hide_index=True)
        if not warn.empty:
            st.warning(f"🟡 {len(warn)} Warnings")
            st.dataframe(warn.drop(columns=['Category']), use_container_width=True, hide_index=True)
        with st.expander(f"🟢 {len(exp)} Expected Differences"):
            st.dataframe(exp.drop(columns=['Category']), use_container_width=True, hide_index=True)
    else:
        st.success("✅ All environment variables match!")
    
    return report


# ==========================================
# SQS/SNS HELPERS
# ==========================================

def render_sqs_dashboard(src_queue, tgt_queue):
    """Compare SQS queue configurations"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    st.subheader(f"📬 Queue: {src_queue['QueueName']}")
    
    col1, col2, col3 = st.columns(3)
    
    # Visibility Timeout
    vis_src = src_queue.get('VisibilityTimeout', '30')
    vis_tgt = tgt_queue.get('VisibilityTimeout', '30')
    col1.metric("Visibility Timeout", f"{vis_tgt}s", delta=None if vis_src == vis_tgt else "Changed")
    
    # Message Retention
    ret_src = src_queue.get('MessageRetentionPeriod', '345600')
    ret_tgt = tgt_queue.get('MessageRetentionPeriod', '345600')
    col2.metric("Retention Period", f"{int(ret_tgt)//86400} days")
    
    # DLQ Check (Critical)
    dlq_src = src_queue.get('RedrivePolicy')
    dlq_tgt = tgt_queue.get('RedrivePolicy')
    
    st.divider()
    
    if dlq_src and not dlq_tgt:
        st.error("🔴 Dead Letter Queue: Configured in Source but MISSING in Target")
        col3.markdown("<span class='badge-crit'>NO DLQ</span>", unsafe_allow_html=True)
        report["Critical"].append("DLQ not configured")
    elif not dlq_src and not dlq_tgt:
        st.warning("⚠️ Dead Letter Queue: Not configured in either environment")
        col3.markdown("<span class='badge-warn'>NO DLQ</span>", unsafe_allow_html=True)
        report["Warnings"].append("No DLQ configured")
    else:
        st.success("✅ Dead Letter Queue: Configured")
        col3.markdown("<span class='badge-pass'>DLQ ✓</span>", unsafe_allow_html=True)
    
    # Encryption
    kms_src = src_queue.get('KmsMasterKeyId')
    kms_tgt = tgt_queue.get('KmsMasterKeyId')
    
    if kms_src and not kms_tgt:
        st.warning("⚠️ Encryption: Enabled in Source but disabled in Target")
        report["Warnings"].append("Encryption disabled in target")
    
    return report


def render_sns_dashboard(src_topic, tgt_topic):
    """Compare SNS topic configurations"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    st.subheader(f"📢 Topic: {src_topic['TopicName']}")
    
    # Subscriptions
    subs_src = src_topic.get('Subscriptions', [])
    subs_tgt = tgt_topic.get('Subscriptions', [])
    
    col1, col2 = st.columns(2)
    col1.metric("Source Subscriptions", len(subs_src))
    col2.metric("Target Subscriptions", len(subs_tgt))
    
    st.divider()
    
    if len(subs_src) > 0 and len(subs_tgt) == 0:
        st.error("🔴 No subscriptions in Target (alerts will not be sent!)")
        report["Critical"].append("No subscriptions in target")
    elif len(subs_src) != len(subs_tgt):
        st.warning(f"⚠️ Subscription count mismatch")
        report["Warnings"].append(f"Subscription count: {len(subs_src)} vs {len(subs_tgt)}")
    else:
        st.success("✅ Subscription count matches")
    
    # Show subscriptions
    if subs_src:
        with st.expander("View Source Subscriptions"):
            for sub in subs_src:
                st.text(f"{sub['Protocol']}: {sub['Endpoint']}")
    
    if subs_tgt:
        with st.expander("View Target Subscriptions"):
            for sub in subs_tgt:
                st.text(f"{sub['Protocol']}: {sub['Endpoint']}")
    
    return report


# ==========================================
# LOAD BALANCER HELPERS
# ==========================================

def render_load_balancer_dashboard(src_lb, tgt_lb):
    """Compare Load Balancer configurations"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    st.subheader(f"⚖️ {src_lb['Type']}: {src_lb['LoadBalancerName']}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Type", src_lb['Type'])
    col2.metric("Scheme", src_lb['Scheme'])
    
    # Security Groups
    sgs_src = src_lb.get('SecurityGroups', [])
    sgs_tgt = tgt_lb.get('SecurityGroups', [])
    
    if len(sgs_src) > 0 and len(sgs_tgt) == 0:
        col3.markdown("<span class='badge-crit'>NO SGs</span>", unsafe_allow_html=True)
        report["Critical"].append("No security groups attached to target LB")
    elif len(sgs_src) != len(sgs_tgt):
        col3.markdown(f"<span class='badge-warn'>SG Count: {len(sgs_tgt)}</span>", unsafe_allow_html=True)
        report["Warnings"].append(f"Security group count mismatch: {len(sgs_src)} vs {len(sgs_tgt)}")
    else:
        col3.markdown(f"<span class='badge-pass'>SGs: {len(sgs_tgt)}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # Target Groups Health Checks
    st.markdown("**Target Groups & Health Checks:**")
    
    tgs_src = src_lb.get('TargetGroups', [])
    tgs_tgt = tgt_lb.get('TargetGroups', [])
    
    for tg_src in tgs_src:
        tg_name = tg_src['TargetGroupName']
        
        # Find matching target group
        tg_tgt = next((tg for tg in tgs_tgt if tg['TargetGroupName'] == tg_name), None)
        
        if not tg_tgt:
            st.error(f"❌ Target Group '{tg_name}' missing in target")
            report["Critical"].append(f"Target group {tg_name} missing")
            continue
        
        # Compare health check settings
        hc_src_path = tg_src.get('HealthCheckPath', '/')
        hc_tgt_path = tg_tgt.get('HealthCheckPath', '/')
        
        hc_src_interval = tg_src.get('HealthCheckIntervalSeconds', 30)
        hc_tgt_interval = tg_tgt.get('HealthCheckIntervalSeconds', 30)
        
        hc_src_threshold = tg_src.get('HealthyThresholdCount', 2)
        hc_tgt_threshold = tg_tgt.get('HealthyThresholdCount', 2)
        
        issues = []
        if hc_src_path != hc_tgt_path:
            issues.append(f"Health Check Path: {hc_src_path} → {hc_tgt_path}")
            report["Critical"].append(f"{tg_name}: Health check path mismatch")
        
        if hc_src_interval != hc_tgt_interval:
            issues.append(f"Interval: {hc_src_interval}s → {hc_tgt_interval}s")
            report["Warnings"].append(f"{tg_name}: Health check interval differs")
        
        if hc_src_threshold != hc_tgt_threshold:
            issues.append(f"Threshold: {hc_src_threshold} → {hc_tgt_threshold}")
            report["Warnings"].append(f"{tg_name}: Health check threshold differs")
        
        if issues:
            st.markdown(f"""
            <div class='resource-card' style='border-left: 5px solid #ffa000;'>
                <b>⚠️ {tg_name}</b><br>
                {' • '.join(issues)}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"✅ {tg_name}: Health check settings match")
    
    return report


# ==========================================
# SECURITY GROUPS HELPERS
# ==========================================

def render_security_group_dashboard(src_sg, tgt_sg):
    """Compare Security Group configurations"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    sg_id = src_sg['GroupId']
    sg_name = src_sg.get('GroupName', 'N/A')
    
    st.subheader(f"🔒 {sg_name} ({sg_id})")
    
    # Usage comparison
    used_by_src = src_sg.get('UsedBy', [])
    used_by_tgt = tgt_sg.get('UsedBy', [])
    
    st.markdown("**Attached To:**")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Source:**")
        if used_by_src:
            for resource in used_by_src:
                st.text(f"• {resource}")
        else:
            st.text("(none)")
    
    with col2:
        st.markdown("**Target:**")
        if used_by_tgt:
            for resource in used_by_tgt:
                st.text(f"• {resource}")
        else:
            st.text("(none)")
    
    # Check for missing attachments
    if len(used_by_src) > len(used_by_tgt):
        st.warning("⚠️ Fewer attachments in target")
        report["Warnings"].append(f"Missing {len(used_by_src) - len(used_by_tgt)} resource attachments")
    
    st.divider()
    
    # Inbound Rules
    st.markdown("**Inbound Rules:**")
    
    rules_src = src_sg.get('IpPermissions', [])
    rules_tgt = tgt_sg.get('IpPermissions', [])
    
    # Simple comparison - count
    if len(rules_src) != len(rules_tgt):
        st.warning(f"⚠️ Rule count mismatch: Source has {len(rules_src)}, Target has {len(rules_tgt)}")
        report["Warnings"].append(f"Inbound rule count: {len(rules_src)} vs {len(rules_tgt)}")
    else:
        st.success(f"✅ Both have {len(rules_src)} inbound rules")
    
    # Show rules side by side
    col_src, col_tgt = st.columns(2)
    
    with col_src:
        st.markdown("**Source Rules:**")
        for rule in rules_src:
            port = rule.get('FromPort', 'All')
            protocol = rule.get('IpProtocol', 'All')
            st.code(f"Port {port} ({protocol})")
    
    with col_tgt:
        st.markdown("**Target Rules:**")
        for rule in rules_tgt:
            port = rule.get('FromPort', 'All')
            protocol = rule.get('IpProtocol', 'All')
            st.code(f"Port {port} ({protocol})")
    
    return report


# ==========================================
# IAM ROLES HELPERS
# ==========================================

def extract_permissions_from_policies(role_config):
    """Extract all permissions from a role's policies"""
    permissions = {}
    
    # From inline policies
    for policy_name, policy_doc in role_config.get('InlinePolicies', {}).items():
        for statement in policy_doc.get('Statement', []):
            actions = statement.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                service = action.split(':')[0] if ':' in action else 'unknown'
                if service not in permissions:
                    permissions[service] = set()
                permissions[service].add(action)
    
    # From managed policies
    for policy in role_config.get('ManagedPolicyDocuments', []):
        for statement in policy.get('Document', {}).get('Statement', []):
            actions = statement.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                service = action.split(':')[0] if ':' in action else 'unknown'
                if service not in permissions:
                    permissions[service] = set()
                permissions[service].add(action)
    
    return permissions

def render_iam_role_dashboard(src_role, tgt_role):
    """Compare IAM Role configurations"""
    report = {"Critical": [], "Warnings": [], "Info": []}
    
    role_name = src_role['RoleName']
    st.subheader(f"🔐 Role: {role_name}")
    
    # Usage
    used_by_src = src_role.get('UsedBy', [])
    used_by_tgt = tgt_role.get('UsedBy', [])
    
    st.markdown("**Used By:**")
    col1, col2 = st.columns(2)
    col1.write(", ".join(used_by_src) if used_by_src else "(none)")
    col2.write(", ".join(used_by_tgt) if used_by_tgt else "(none)")
    
    st.divider()
    
    # Extract permissions
    perms_src = extract_permissions_from_policies(src_role)
    perms_tgt = extract_permissions_from_policies(tgt_role)
    
    st.markdown("**Permission Analysis:**")
    
    all_services = sorted(set(perms_src.keys()) | set(perms_tgt.keys()))
    
    for service in all_services:
        actions_src = perms_src.get(service, set())
        actions_tgt = perms_tgt.get(service, set())
        
        missing_in_tgt = actions_src - actions_tgt
        extra_in_tgt = actions_tgt - actions_src
        
        if missing_in_tgt:
            st.markdown(f"""
            <div class='resource-card' style='border-left: 5px solid #c62828;'>
                <b>❌ {service.upper()}: Missing Actions in Target</b><br>
                {', '.join(sorted(missing_in_tgt))}
            </div>
            """, unsafe_allow_html=True)
            report["Critical"].append(f"{service}: Missing {len(missing_in_tgt)} actions")
        elif extra_in_tgt:
            st.markdown(f"""
            <div class='resource-card' style='border-left: 5px solid #4caf50;'>
                <b>✅ {service.upper()}: All actions present</b><br>
                <small>({len(actions_tgt)} actions)</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"✅ {service.upper()}: Permissions match ({len(actions_src)} actions)")
    
    return report
