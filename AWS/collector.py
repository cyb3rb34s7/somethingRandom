import boto3
import json
import os
import datetime
import sys
from botocore.exceptions import ClientError

# ==========================================
# CONFIGURATION
# ==========================================
# Get current region from CloudShell environment
CURRENT_REGION = os.environ.get('AWS_REGION', 'us-east-1')
TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
BASE_DIR = f"aws_dump_{CURRENT_REGION}_{TIMESTAMP}"

# Services to scan (Strictly Read-Only)
SCAN_S3 = True
SCAN_SQS = True
SCAN_SNS = True
SCAN_LAMBDA = True
SCAN_APIGW = True

# ==========================================
# HELPERS
# ==========================================
def save_json(service, name, data, subfolder=None):
    """Saves data to formatted JSON file"""
    # Create directory structure
    path = os.path.join(BASE_DIR, service)
    if subfolder:
        path = os.path.join(path, subfolder)
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    # Sanitize filename
    safe_name = "".join([c if c.isalnum() or c in ('-','_','.') else '_' for c in name])
    filepath = os.path.join(path, f"{safe_name}.json")

    # Serialize dates/binary
    def json_serial(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return str(obj)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=json_serial)
    print(f"   [+] Saved {service}: {name}")

def get_boto(service):
    return boto3.client(service, region_name=CURRENT_REGION)

# ==========================================
# 1. FOCUSED ECS SCAN
# ==========================================
def scan_ecs_cluster(cluster_name):
    print(f"\n🚀 STARTING FOCUSED SCAN: ECS Cluster '{cluster_name}'")
    ecs = get_boto('ecs')
    
    try:
        # A. Cluster Config
        print("... Fetching Cluster Configuration")
        resp = ecs.describe_clusters(clusters=[cluster_name])
        if not resp['clusters']:
            print(f"❌ Cluster '{cluster_name}' not found!")
            return
        save_json("ecs_focused", "cluster_config", resp['clusters'][0])

        # B. List Services (Paginated)
        print("... Fetching Services")
        service_arns = []
        paginator = ecs.get_paginator('list_services')
        for page in paginator.paginate(cluster=cluster_name):
            service_arns.extend(page['serviceArns'])
        
        # C. Describe Services (Batched 10 at a time)
        print(f"... Describing {len(service_arns)} Services")
        task_def_arns = set()
        
        # Batching logic
        for i in range(0, len(service_arns), 10):
            batch = service_arns[i:i+10]
            svcs = ecs.describe_services(cluster=cluster_name, services=batch)
            for s in svcs['services']:
                save_json("ecs_focused", s['serviceName'], s, subfolder="services")
                task_def_arns.add(s['taskDefinition'])

        # D. Fetch Task Definitions (Active only)
        print(f"... Fetching {len(task_def_arns)} Unique Task Definitions")
        for td_arn in task_def_arns:
            # Describe TD
            td_resp = ecs.describe_task_definition(taskDefinition=td_arn)
            td_data = td_resp['taskDefinition']
            family = td_data['family']
            revision = td_data['revision']
            save_json("ecs_focused", f"{family}_v{revision}", td_data, subfolder="task_definitions")

    except Exception as e:
        print(f"❌ ECS Scan Error: {str(e)}")

# ==========================================
# 2. BROAD REGIONAL SCANS (DEPENDENCIES)
# ==========================================
def scan_s3_buckets():
    print(f"\n📦 SCANNING S3 (Region: {CURRENT_REGION})")
    s3 = boto3.client('s3') # S3 is global client, but we filter
    
    try:
        buckets = s3.list_buckets()['Buckets']
        count = 0
        for b in buckets:
            name = b['Name']
            
            # Check Location (Only download if in CURRENT_REGION)
            try:
                loc = s3.get_bucket_location(Bucket=name)['LocationConstraint']
                # 'None' means us-east-1
                if loc is None: loc = 'us-east-1'
                if loc != CURRENT_REGION:
                    continue
            except: continue

            count += 1
            config = {"Name": name, "Region": CURRENT_REGION}
            
            # Get Policy
            try: 
                p = s3.get_bucket_policy(Bucket=name)
                config['Policy'] = json.loads(p['Policy'])
            except: config['Policy'] = None

            # Get Encryption
            try: 
                e = s3.get_bucket_encryption(Bucket=name)
                config['Encryption'] = e['ServerSideEncryptionConfiguration']
            except: config['Encryption'] = None
            
            # Get Versioning
            try: 
                v = s3.get_bucket_versioning(Bucket=name)
                config['Versioning'] = v.get('Status', 'Suspended')
            except: config['Versioning'] = None

            save_json("s3_buckets", name, config)
            
        print(f"   -> Processed {count} buckets in this region.")
            
    except Exception as e: print(f"❌ S3 Error: {e}")

def scan_sqs_queues():
    print(f"\n📨 SCANNING SQS")
    sqs = get_boto('sqs')
    try:
        resp = sqs.list_queues()
        if 'QueueUrls' in resp:
            for q_url in resp['QueueUrls']:
                q_name = q_url.split('/')[-1]
                # Get Attributes (Policy, Redrive, etc.)
                attrs = sqs.get_queue_attributes(QueueUrl=q_url, AttributeNames=['All'])
                save_json("sqs_queues", q_name, attrs['Attributes'])
    except Exception as e: print(f"❌ SQS Error: {e}")

def scan_sns_topics():
    print(f"\n📢 SCANNING SNS")
    sns = get_boto('sns')
    try:
        paginator = sns.get_paginator('list_topics')
        for page in paginator.paginate():
            for t in page['Topics']:
                arn = t['TopicArn']
                name = arn.split(':')[-1]
                attrs = sns.get_topic_attributes(TopicArn=arn)
                save_json("sns_topics", name, attrs['Attributes'])
    except Exception as e: print(f"❌ SNS Error: {e}")

def scan_lambdas():
    print(f"\n⚡ SCANNING LAMBDA")
    lam = get_boto('lambda')
    try:
        paginator = lam.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page['Functions']:
                name = func['FunctionName']
                # Get details (Env vars are here)
                # We save the 'func' object from list which has most config
                # Usually Env Vars are in 'Environment' key
                save_json("lambdas", name, func)
    except Exception as e: print(f"❌ Lambda Error: {e}")

def scan_api_gateway():
    print(f"\n🌐 SCANNING API GATEWAY (REST)")
    apig = get_boto('apigateway')
    try:
        apis = apig.get_rest_apis()['items']
        for api in apis:
            api_id = api['id']
            name = api['name']
            
            # Export OAS30 JSON (Compatible with your Audit Tool)
            try:
                export = apig.get_export(
                    restApiId=api_id,
                    stageName='dev', # Assumes 'dev' exists, fallback logic below
                    exportType='oas30',
                    parameters={'extensions': 'integrations'}
                )
                body = json.loads(export['body'].read())
                save_json("api_gateway", f"{name}_{api_id}", body)
            except:
                # Fallback: Just save the raw config if export fails (e.g. no stage)
                save_json("api_gateway", f"{name}_{api_id}_raw", api)
                
    except Exception as e: print(f"❌ API Gateway Error: {e}")

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    print("="*60)
    print(f"🛡️  AWS READ-ONLY COLLECTOR | Region: {CURRENT_REGION}")
    print("="*60)
    
    cluster_input = input("Enter ECS Cluster Name to Scan: ").strip()
    
    if not cluster_input:
        print("❌ No cluster provided. Exiting.")
        sys.exit(1)

    # 1. Run Focused Scan
    scan_ecs_cluster(cluster_input)
    
    # 2. Run Broad Scans
    if SCAN_S3: scan_s3_buckets()
    if SCAN_SQS: scan_sqs_queues()
    if SCAN_SNS: scan_sns_topics()
    if SCAN_LAMBDA: scan_lambdas()
    if SCAN_APIGW: scan_api_gateway()
    
    print("\n" + "="*60)
    print("✅ SCAN COMPLETE!")
    print(f"📂 Output Directory: {BASE_DIR}")
    print("="*60)
    print("\n⬇️  TO DOWNLOAD:")
    print(f"zip -r dump.zip {BASE_DIR}")
    print("(Then verify checksum and download via Actions -> Download File)")

if __name__ == "__main__":
    main()
