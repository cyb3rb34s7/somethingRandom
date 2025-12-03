import boto3
import json
import os
import datetime
import sys
import hashlib
import re
from pathlib import Path

# CONFIG
CURRENT_REGION = os.environ.get('AWS_REGION', 'us-east-1')
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
BASE_DIR = f"aws_dump_{CURRENT_REGION}_{TIMESTAMP}"

def save_json(service, name, data, subfolder=None):
    path = os.path.join(BASE_DIR, service)
    if subfolder: path = os.path.join(path, subfolder)
    if not os.path.exists(path): os.makedirs(path)
    safe_name = "".join([c if c.isalnum() or c in ('-','_','.') else '_' for c in name])
    
    def json_serial(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)): return obj.isoformat()
        return str(obj)

    with open(os.path.join(path, f"{safe_name}.json"), 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)
    print(f"   [+] Saved {service}: {name}")

def extract_version_from_filename(filename):
    """Extract version from filename like: documentation_v1.2.3.docx"""
    match = re.search(r'_v?(\d+\.\d+\.\d+)', filename)
    if match:
        return match.group(1)
    return None

def should_skip_file(filename, size):
    """Determine if file should be skipped"""
    # Skip images
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp', '.bmp']
    # Skip videos
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv']
    # Skip archives (optional)
    archive_extensions = ['.zip', '.tar', '.gz', '.rar', '.7z']
    
    file_lower = filename.lower()
    
    for ext in image_extensions:
        if file_lower.endswith(ext):
            return True, "image_file_skipped"
    
    for ext in video_extensions:
        if file_lower.endswith(ext):
            return True, "video_file_skipped"
    
    # Skip files larger than 10MB
    if size > 10 * 1024 * 1024:  # 10MB in bytes
        return True, "file_size_exceeds_limit"
    
    return False, None

def scan_ecs_cluster(cluster_name):
    print(f"\n🚀 SCANNING ECS CLUSTER: {cluster_name}")
    ecs = boto3.client('ecs', region_name=CURRENT_REGION)
    try:
        # Cluster
        resp = ecs.describe_clusters(clusters=[cluster_name])
        if not resp['clusters']: print("❌ Cluster not found"); return
        save_json("ecs_focused", "cluster_config", resp['clusters'][0])
        
        # Services & Tasks
        svcs = ecs.list_services(cluster=cluster_name)['serviceArns']
        if svcs:
            desc_svcs = ecs.describe_services(cluster=cluster_name, services=svcs)['services']
            for s in desc_svcs:
                save_json("ecs_focused", s['serviceName'], s, subfolder="services")
                # Fetch TD
                td_arn = s['taskDefinition']
                td = ecs.describe_task_definition(taskDefinition=td_arn)['taskDefinition']
                family = td['family']
                save_json("ecs_focused", f"{family}", td, subfolder="task_definitions")
    except Exception as e: print(f"ECS Error: {e}")

def scan_s3_buckets():
    print(f"\n📦 SCANNING S3 BUCKETS ({CURRENT_REGION})")
    s3 = boto3.client('s3')
    try:
        for b in s3.list_buckets()['Buckets']:
            name = b['Name']
            try:
                loc = s3.get_bucket_location(Bucket=name)['LocationConstraint']
                if loc is None: loc = 'us-east-1'
                if loc != CURRENT_REGION: continue
                
                config = {"Name": name}
                try: config['Policy'] = json.loads(s3.get_bucket_policy(Bucket=name)['Policy'])
                except: config['Policy'] = None
                try: config['Encryption'] = s3.get_bucket_encryption(Bucket=name)['ServerSideEncryptionConfiguration']
                except: config['Encryption'] = None
                try: config['Versioning'] = s3.get_bucket_versioning(Bucket=name).get('Status', 'Suspended')
                except: config['Versioning'] = 'Suspended'
                
                save_json("s3_buckets", name, config)
            except: continue
    except Exception as e: print(f"S3 Error: {e}")

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
                    # Save with stage name included
                    save_json("api_gateway", f"{name}_{stage_name}", body)
                except Exception as e:
                    print(f"   ❌ Export Failed for {name} [{stage_name}]: {e}")

    except Exception as e: 
        print(f"API GW Error: {e}")

def scan_lambda_functions():
    print(f"\n⚡ SCANNING LAMBDA FUNCTIONS")
    lambda_client = boto3.client('lambda', region_name=CURRENT_REGION)
    try:
        paginator = lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page['Functions']:
                func_name = func['FunctionName']
                print(f"   ... Processing Lambda: {func_name}")
                
                try:
                    # Get full function configuration
                    full_config = lambda_client.get_function(FunctionName=func_name)
                    
                    # Extract relevant configuration
                    config = {
                        "FunctionName": func_name,
                        "FunctionArn": func['FunctionArn'],
                        "Runtime": func.get('Runtime'),
                        "Role": func.get('Role'),
                        "Handler": func.get('Handler'),
                        "Timeout": func.get('Timeout'),
                        "MemorySize": func.get('MemorySize'),
                        "Environment": func.get('Environment', {}),
                        "VpcConfig": func.get('VpcConfig', {}),
                        "DeadLetterConfig": func.get('DeadLetterConfig', {}),
                        "Layers": func.get('Layers', []),
                        "ReservedConcurrentExecutions": func.get('ReservedConcurrentExecutions'),
                        "LastModified": func.get('LastModified'),
                        "CodeSize": func.get('CodeSize'),
                        "CodeSha256": func.get('CodeSha256')
                    }
                    
                    save_json("lambda_functions", func_name, config)
                    
                except Exception as e:
                    print(f"   ❌ Failed to process {func_name}: {e}")
                    
    except Exception as e:
        print(f"Lambda Error: {e}")

def scan_sqs_queues():
    print(f"\n📬 SCANNING SQS QUEUES")
    sqs = boto3.client('sqs', region_name=CURRENT_REGION)
    try:
        queues = sqs.list_queues()
        if 'QueueUrls' not in queues:
            print("   No queues found")
            return
            
        for queue_url in queues['QueueUrls']:
            queue_name = queue_url.split('/')[-1]
            print(f"   ... Processing Queue: {queue_name}")
            
            try:
                # Get all queue attributes
                attrs = sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['All']
                )
                
                config = {
                    "QueueName": queue_name,
                    "QueueUrl": queue_url,
                    "QueueArn": attrs['Attributes'].get('QueueArn'),
                    "VisibilityTimeout": attrs['Attributes'].get('VisibilityTimeout'),
                    "MessageRetentionPeriod": attrs['Attributes'].get('MessageRetentionPeriod'),
                    "MaximumMessageSize": attrs['Attributes'].get('MaximumMessageSize'),
                    "DelaySeconds": attrs['Attributes'].get('DelaySeconds'),
                    "ReceiveMessageWaitTimeSeconds": attrs['Attributes'].get('ReceiveMessageWaitTimeSeconds'),
                    "RedrivePolicy": attrs['Attributes'].get('RedrivePolicy'),
                    "KmsMasterKeyId": attrs['Attributes'].get('KmsMasterKeyId'),
                    "CreatedTimestamp": attrs['Attributes'].get('CreatedTimestamp'),
                    "LastModifiedTimestamp": attrs['Attributes'].get('LastModifiedTimestamp')
                }
                
                save_json("sqs_queues", queue_name, config)
                
            except Exception as e:
                print(f"   ❌ Failed to process {queue_name}: {e}")
                
    except Exception as e:
        print(f"SQS Error: {e}")

def scan_sns_topics():
    print(f"\n📢 SCANNING SNS TOPICS")
    sns = boto3.client('sns', region_name=CURRENT_REGION)
    try:
        paginator = sns.get_paginator('list_topics')
        for page in paginator.paginate():
            for topic in page['Topics']:
                topic_arn = topic['TopicArn']
                topic_name = topic_arn.split(':')[-1]
                print(f"   ... Processing Topic: {topic_name}")
                
                try:
                    # Get topic attributes
                    attrs = sns.get_topic_attributes(TopicArn=topic_arn)
                    
                    # Get subscriptions
                    subs = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
                    
                    config = {
                        "TopicName": topic_name,
                        "TopicArn": topic_arn,
                        "DisplayName": attrs['Attributes'].get('DisplayName'),
                        "Owner": attrs['Attributes'].get('Owner'),
                        "Policy": attrs['Attributes'].get('Policy'),
                        "SubscriptionsConfirmedCount": attrs['Attributes'].get('SubscriptionsConfirmed'),
                        "Subscriptions": subs.get('Subscriptions', []),
                        "KmsMasterKeyId": attrs['Attributes'].get('KmsMasterKeyId')
                    }
                    
                    save_json("sns_topics", topic_name, config)
                    
                except Exception as e:
                    print(f"   ❌ Failed to process {topic_name}: {e}")
                    
    except Exception as e:
        print(f"SNS Error: {e}")

def scan_load_balancers():
    print(f"\n⚖️ SCANNING LOAD BALANCERS")
    elbv2 = boto3.client('elbv2', region_name=CURRENT_REGION)
    try:
        lbs = elbv2.describe_load_balancers()
        
        for lb in lbs['LoadBalancers']:
            lb_name = lb['LoadBalancerName']
            lb_arn = lb['LoadBalancerArn']
            print(f"   ... Processing LB: {lb_name}")
            
            try:
                # Get listeners
                listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arn)
                
                # Get target groups
                target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
                
                # For each target group, get health check config
                for tg in target_groups['TargetGroups']:
                    tg_arn = tg['TargetGroupArn']
                    tg['TargetHealth'] = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                
                config = {
                    "LoadBalancerName": lb_name,
                    "LoadBalancerArn": lb_arn,
                    "Type": lb['Type'],
                    "Scheme": lb['Scheme'],
                    "State": lb['State'],
                    "AvailabilityZones": lb['AvailabilityZones'],
                    "SecurityGroups": lb.get('SecurityGroups', []),
                    "VpcId": lb.get('VpcId'),
                    "Listeners": listeners['Listeners'],
                    "TargetGroups": target_groups['TargetGroups']
                }
                
                save_json("load_balancers", lb_name, config)
                
            except Exception as e:
                print(f"   ❌ Failed to process {lb_name}: {e}")
                
    except Exception as e:
        print(f"Load Balancer Error: {e}")

def scan_security_groups_used():
    print(f"\n🔒 SCANNING SECURITY GROUPS (Used by Services)")
    ec2 = boto3.client('ec2', region_name=CURRENT_REGION)
    ecs = boto3.client('ecs', region_name=CURRENT_REGION)
    lambda_client = boto3.client('lambda', region_name=CURRENT_REGION)
    elbv2 = boto3.client('elbv2', region_name=CURRENT_REGION)
    
    used_sg_ids = set()
    sg_usage_map = {}
    
    try:
        # Get SGs from ECS services (if cluster name provided)
        try:
            clusters = ecs.list_clusters()
            for cluster_arn in clusters.get('clusterArns', []):
                services = ecs.list_services(cluster=cluster_arn)
                if services.get('serviceArns'):
                    desc_services = ecs.describe_services(
                        cluster=cluster_arn,
                        services=services['serviceArns']
                    )
                    for service in desc_services['services']:
                        if 'networkConfiguration' in service:
                            sgs = service['networkConfiguration'].get('awsvpcConfiguration', {}).get('securityGroups', [])
                            for sg in sgs:
                                used_sg_ids.add(sg)
                                if sg not in sg_usage_map:
                                    sg_usage_map[sg] = []
                                sg_usage_map[sg].append(f"ECS:{service['serviceName']}")
        except Exception as e:
            print(f"   ⚠️ Could not scan ECS SGs: {e}")
        
        # Get SGs from Lambda functions
        try:
            paginator = lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for func in page['Functions']:
                    if 'VpcConfig' in func and 'SecurityGroupIds' in func['VpcConfig']:
                        for sg in func['VpcConfig']['SecurityGroupIds']:
                            used_sg_ids.add(sg)
                            if sg not in sg_usage_map:
                                sg_usage_map[sg] = []
                            sg_usage_map[sg].append(f"Lambda:{func['FunctionName']}")
        except Exception as e:
            print(f"   ⚠️ Could not scan Lambda SGs: {e}")
        
        # Get SGs from Load Balancers
        try:
            lbs = elbv2.describe_load_balancers()
            for lb in lbs['LoadBalancers']:
                for sg in lb.get('SecurityGroups', []):
                    used_sg_ids.add(sg)
                    if sg not in sg_usage_map:
                        sg_usage_map[sg] = []
                    sg_usage_map[sg].append(f"ALB/NLB:{lb['LoadBalancerName']}")
        except Exception as e:
            print(f"   ⚠️ Could not scan LB SGs: {e}")
        
        # Now describe only the used security groups
        if used_sg_ids:
            sg_list = list(used_sg_ids)
            print(f"   Found {len(sg_list)} security groups in use")
            
            # Describe in batches (API limit)
            for i in range(0, len(sg_list), 100):
                batch = sg_list[i:i+100]
                sgs = ec2.describe_security_groups(GroupIds=batch)
                
                for sg in sgs['SecurityGroups']:
                    sg_id = sg['GroupId']
                    sg['UsedBy'] = sg_usage_map.get(sg_id, [])
                    save_json("security_groups", sg_id, sg)
        else:
            print("   No security groups found in use")
            
    except Exception as e:
        print(f"Security Groups Error: {e}")

def scan_iam_roles_for_services():
    print(f"\n🔐 SCANNING IAM ROLES (Used by Services)")
    iam = boto3.client('iam')
    ecs = boto3.client('ecs', region_name=CURRENT_REGION)
    lambda_client = boto3.client('lambda', region_name=CURRENT_REGION)
    
    used_role_arns = set()
    role_usage_map = {}
    
    try:
        # Get roles from ECS task definitions
        try:
            clusters = ecs.list_clusters()
            for cluster_arn in clusters.get('clusterArns', []):
                services = ecs.list_services(cluster=cluster_arn)
                if services.get('serviceArns'):
                    desc_services = ecs.describe_services(
                        cluster=cluster_arn,
                        services=services['serviceArns']
                    )
                    for service in desc_services['services']:
                        td_arn = service['taskDefinition']
                        td = ecs.describe_task_definition(taskDefinition=td_arn)
                        task_def = td['taskDefinition']
                        
                        # Task Execution Role
                        if 'executionRoleArn' in task_def:
                            role_arn = task_def['executionRoleArn']
                            used_role_arns.add(role_arn)
                            if role_arn not in role_usage_map:
                                role_usage_map[role_arn] = []
                            role_usage_map[role_arn].append(f"ECS-Execution:{service['serviceName']}")
                        
                        # Task Role
                        if 'taskRoleArn' in task_def:
                            role_arn = task_def['taskRoleArn']
                            used_role_arns.add(role_arn)
                            if role_arn not in role_usage_map:
                                role_usage_map[role_arn] = []
                            role_usage_map[role_arn].append(f"ECS-Task:{service['serviceName']}")
        except Exception as e:
            print(f"   ⚠️ Could not scan ECS roles: {e}")
        
        # Get roles from Lambda functions
        try:
            paginator = lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for func in page['Functions']:
                    role_arn = func['Role']
                    used_role_arns.add(role_arn)
                    if role_arn not in role_usage_map:
                        role_usage_map[role_arn] = []
                    role_usage_map[role_arn].append(f"Lambda:{func['FunctionName']}")
        except Exception as e:
            print(f"   ⚠️ Could not scan Lambda roles: {e}")
        
        # Describe each role
        if used_role_arns:
            print(f"   Found {len(used_role_arns)} IAM roles in use")
            
            for role_arn in used_role_arns:
                role_name = role_arn.split('/')[-1]
                print(f"   ... Processing Role: {role_name}")
                
                try:
                    role = iam.get_role(RoleName=role_name)
                    
                    # Get attached policies
                    attached_policies = iam.list_attached_role_policies(RoleName=role_name)
                    
                    # Get inline policies
                    inline_policies = iam.list_role_policies(RoleName=role_name)
                    inline_policy_docs = {}
                    for policy_name in inline_policies['PolicyNames']:
                        policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                        inline_policy_docs[policy_name] = policy_doc['PolicyDocument']
                    
                    # Get managed policy documents
                    managed_policy_docs = []
                    for policy in attached_policies['AttachedPolicies']:
                        try:
                            policy_arn = policy['PolicyArn']
                            policy_detail = iam.get_policy(PolicyArn=policy_arn)
                            default_version = policy_detail['Policy']['DefaultVersionId']
                            policy_version = iam.get_policy_version(
                                PolicyArn=policy_arn,
                                VersionId=default_version
                            )
                            managed_policy_docs.append({
                                "PolicyName": policy['PolicyName'],
                                "PolicyArn": policy_arn,
                                "Document": policy_version['PolicyVersion']['Document']
                            })
                        except Exception as e:
                            print(f"   ⚠️ Could not get policy {policy['PolicyName']}: {e}")
                    
                    config = {
                        "RoleName": role_name,
                        "RoleArn": role_arn,
                        "AssumeRolePolicyDocument": role['Role']['AssumeRolePolicyDocument'],
                        "AttachedManagedPolicies": attached_policies['AttachedPolicies'],
                        "InlinePolicies": inline_policy_docs,
                        "ManagedPolicyDocuments": managed_policy_docs,
                        "UsedBy": role_usage_map.get(role_arn, []),
                        "CreateDate": role['Role']['CreateDate'].isoformat() if 'CreateDate' in role['Role'] else None
                    }
                    
                    save_json("iam_roles", role_name, config)
                    
                except Exception as e:
                    print(f"   ❌ Failed to process {role_name}: {e}")
        else:
            print("   No IAM roles found in use")
            
    except Exception as e:
        print(f"IAM Roles Error: {e}")

def scan_s3_file_contents(config_file_path):
    print(f"\n📂 SCANNING S3 FILE CONTENTS (from config)")
    s3 = boto3.client('s3')
    
    try:
        # Load config file
        if not os.path.exists(config_file_path):
            print(f"   ⚠️ Config file not found: {config_file_path}")
            print(f"   Skipping S3 file content download")
            return
        
        with open(config_file_path, 'r') as f:
            config = json.load(f)
        
        environment = config.get('environment', 'unknown')
        print(f"   Environment: {environment}")
        
        for bucket_config in config.get('s3_file_downloads', []):
            bucket = bucket_config['bucket']
            prefix = bucket_config['prefix']
            description = bucket_config.get('description', '')
            
            print(f"   📦 Scanning: s3://{bucket}/{prefix} ({description})")
            
            # Create folder structure
            folder_name = f"{bucket}_{prefix.replace('/', '_').rstrip('_')}"
            folder_path = os.path.join(BASE_DIR, "s3_file_contents", folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            index_data = {
                "bucket": bucket,
                "prefix": prefix,
                "environment": environment,
                "scan_timestamp": datetime.datetime.now().isoformat(),
                "total_files": 0,
                "downloaded_files": 0,
                "skipped_files": 0,
                "files": []
            }
            
            try:
                # List all objects in the folder
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    if 'Contents' not in page:
                        continue
                    
                    for obj in page['Contents']:
                        key = obj['Key']
                        
                        # Skip folder markers
                        if key.endswith('/'):
                            continue
                        
                        filename = key.replace(prefix, '')
                        if not filename:
                            continue
                        
                        size = obj['Size']
                        index_data['total_files'] += 1
                        
                        print(f"      ... Processing: {filename}")
                        
                        # Check if should skip
                        should_skip, skip_reason = should_skip_file(filename, size)
                        
                        file_info = {
                            "filename": filename,
                            "key": key,
                            "size": size,
                            "last_modified": obj['LastModified'].isoformat(),
                            "etag": obj['ETag'].strip('"'),
                            "downloaded": False,
                            "content_hash": None,
                            "skip_reason": skip_reason
                        }
                        
                        # Get content type
                        try:
                            head = s3.head_object(Bucket=bucket, Key=key)
                            file_info['content_type'] = head.get('ContentType', 'unknown')
                        except:
                            file_info['content_type'] = 'unknown'
                        
                        # Extract version if present
                        version = extract_version_from_filename(filename)
                        if version:
                            file_info['version_detected'] = version
                        
                        if should_skip:
                            index_data['skipped_files'] += 1
                            print(f"         ⏭️  Skipped: {skip_reason}")
                        else:
                            # Download the file
                            try:
                                obj_response = s3.get_object(Bucket=bucket, Key=key)
                                content_bytes = obj_response['Body'].read()
                                
                                # Calculate hash
                                file_info['content_hash'] = hashlib.md5(content_bytes).hexdigest()
                                file_info['downloaded'] = True
                                index_data['downloaded_files'] += 1
                                
                                # Save file to disk
                                file_path = os.path.join(folder_path, filename)
                                
                                # Create subdirectories if needed
                                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                                
                                # For JSON files, parse and pretty-print
                                if filename.endswith('.json'):
                                    try:
                                        content_json = json.loads(content_bytes.decode('utf-8'))
                                        with open(file_path, 'w') as f:
                                            json.dump(content_json, f, indent=2)
                                    except:
                                        # If can't parse as JSON, save as-is
                                        with open(file_path, 'wb') as f:
                                            f.write(content_bytes)
                                else:
                                    # Binary file - save as-is
                                    with open(file_path, 'wb') as f:
                                        f.write(content_bytes)
                                
                                print(f"         ✅ Downloaded ({size} bytes)")
                                
                            except Exception as e:
                                print(f"         ❌ Download failed: {e}")
                                file_info['skip_reason'] = f"download_error: {str(e)}"
                                index_data['skipped_files'] += 1
                        
                        index_data['files'].append(file_info)
                
                # Save index file
                index_path = os.path.join(folder_path, "_index.json")
                with open(index_path, 'w') as f:
                    json.dump(index_data, f, indent=2)
                
                print(f"   ✅ Completed: {index_data['downloaded_files']} files downloaded, {index_data['skipped_files']} skipped")
                
            except Exception as e:
                print(f"   ❌ Failed to scan bucket {bucket}: {e}")
                
    except Exception as e:
        print(f"S3 File Contents Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("AWS INFRASTRUCTURE COLLECTOR")
    print("=" * 60)
    
    # Get S3 files config path
    s3_config_path = None
    if len(sys.argv) > 1 and sys.argv[1] == "--s3-files-config":
        if len(sys.argv) > 2:
            s3_config_path = sys.argv[2]
        else:
            print("❌ Please provide config file path after --s3-files-config")
            sys.exit(1)
    
    cluster = input("Enter ECS Cluster Name (or press Enter to skip): ").strip()
    
    if cluster:
        scan_ecs_cluster(cluster)
    else:
        print("⏭️  Skipping ECS scan")
    
    # Always scan these
    scan_s3_buckets()
    scan_api_gateway()
    scan_lambda_functions()
    scan_sqs_queues()
    scan_sns_topics()
    scan_load_balancers()
    scan_security_groups_used()
    scan_iam_roles_for_services()
    
    # S3 file contents (if config provided)
    if s3_config_path:
        scan_s3_file_contents(s3_config_path)
    else:
        print("\n📂 Skipping S3 file contents (no config provided)")
        print("   Use: python collector.py --s3-files-config config.json")
    
    print(f"\n✅ DONE. Data saved to: {BASE_DIR}")
    print(f"   To create archive: zip -r dump.zip {BASE_DIR}")
