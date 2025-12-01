import boto3
import json
import os
import sys
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# 1. Load variables from .env file
load_dotenv()

# 2. Fetch Config
try:
    ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
    SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')
    REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    DEV_API_ID = os.getenv('DEV_API_ID')
    LOCAL_API_ID = os.getenv('LOCAL_API_ID')

    if not all([ACCESS_KEY, SECRET_KEY, SESSION_TOKEN, DEV_API_ID, LOCAL_API_ID]):
        print("❌ Error: Missing variables in .env file.")
        print("Please ensure AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, DEV_API_ID, and LOCAL_API_ID are set.")
        sys.exit(1)

except Exception as e:
    print(f"Error loading environment: {e}")
    sys.exit(1)

# 3. Initialize AWS Client
client = boto3.client(
    'apigateway',
    region_name=REGION,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    aws_session_token=SESSION_TOKEN
)

def get_api_export(api_id, name):
    print(f"⬇️  Fetching definition for {name} ({api_id})...")
    try:
        response = client.get_export(
            restApiId=api_id,
            stageName='dev', 
            exportType='oas30',
            parameters={'extensions': 'integrations'}
        )
        return json.loads(response['body'].read())
    except ClientError as e:
        print(f"❌ Error fetching {name}: {e}")
        return None

def normalize_integration(method_data):
    """Extracts critical integration details for comparison"""
    if 'x-amazon-apigateway-integration' in method_data:
        integ = method_data['x-amazon-apigateway-integration']
        return {
            'type': integ.get('type'),
            'uri': integ.get('uri'),
            'httpMethod': integ.get('httpMethod')
        }
    return None

def main():
    print("--------------------------------------------------")
    print("   AWS API GATEWAY DIFFERENCE CHECKER (.env)")
    print("--------------------------------------------------")

    dev_json = get_api_export(DEV_API_ID, "DEV Gateway")
    local_json = get_api_export(LOCAL_API_ID, "LOCAL Gateway")

    if not dev_json or not local_json:
        return

    print("\n🔍 ANALYZING...\n")

    dev_paths = dev_json.get('paths', {})
    local_paths = local_json.get('paths', {})
    
    issues_found = 0

    # A. Check for Missing Paths (Whole Endpoints)
    all_dev_paths = set(dev_paths.keys())
    all_local_paths = set(local_paths.keys())
    
    missing_in_local = all_dev_paths - all_local_paths
    
    if missing_in_local:
        print(f"🔴 MISSING ENDPOINTS (Exists in Dev, missing in Local):")
        for p in missing_in_local:
            print(f"   ❌ {p}")
            issues_found += 1
        print("-" * 40)

    # B. Check for Missing Methods & Integration Mismatches
    print(f"🟠 CONFIGURATION DIFFERENCES (Checking overlapping paths):")
    for path in all_dev_paths.intersection(all_local_paths):
        dev_methods = dev_paths[path]
        local_methods = local_paths[path]

        for method, dev_details in dev_methods.items():
            # 1. Method Missing? (e.g. GET exists, but POST missing)
            if method not in local_methods:
                print(f"   ❌ [MISSING METHOD] {path} -> {method.upper()} missing in Local")
                issues_found += 1
            else:
                # 2. Integration Mismatch? (e.g. Points to wrong Lambda)
                local_details = local_methods[method]
                dev_integ = normalize_integration(dev_details)
                local_integ = normalize_integration(local_details)

                # We ignore 'uri' differences if they are identical except for the function name
                # But strict comparison is usually better for 'Ditto Copy' requirements.
                if dev_integ != local_integ:
                    print(f"   ⚠️  [MISMATCH] {path} [{method.upper()}]")
                    print(f"       Dev URI:   {dev_integ.get('uri')}")
                    print(f"       Local URI: {local_integ.get('uri')}")
                    issues_found += 1

    print("\n" + "="*50)
    if issues_found == 0:
        print("✅ SUCCESS: The Local Gateway is an exact copy of Dev.")
    else:
        print(f"❌ COMPLETED: Found {issues_found} differences.")
    print("="*50)

if __name__ == "__main__":
    main()
