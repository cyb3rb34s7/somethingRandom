import boto3
import json
import os
import datetime
import sys

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
    print(f"\n📦 SCANNING S3 ({CURRENT_REGION})")
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
            
            # 1. FIND STAGE (The Fix)
            stages = apig.get_stages(restApiId=api_id)
            if not stages['item']:
                print(f"   ⚠️ Skipping {name}: No deployed stages found.")
                continue
                
            # Pick the first stage found (usually dev/stage/prod)
            target_stage = stages['item'][0]['stageName']
            print(f"   ... Exporting {name} (Stage: {target_stage})")

            try:
                export = apig.get_export(
                    restApiId=api_id,
                    stageName=target_stage,
                    exportType='oas30',
                    parameters={'extensions': 'integrations'}
                )
                body = json.loads(export['body'].read())
                save_json("api_gateway", f"{name}", body)
            except Exception as e:
                print(f"   ❌ Export Failed for {name}: {e}")

    except Exception as e: print(f"API GW Error: {e}")

if __name__ == "__main__":
    cluster = input("Enter Cluster Name: ").strip()
    scan_ecs_cluster(cluster)
    scan_s3_buckets()
    scan_api_gateway()
    print(f"\n✅ DONE. Download: zip -r dump.zip {BASE_DIR}")
