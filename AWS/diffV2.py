import boto3
import json
import os
import sys
import datetime
import urllib3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# 1. DISABLE SSL WARNINGS & VERIFICATION
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
VERIFY_SSL = False

# 2. LOAD CONFIGURATION
load_dotenv()

# Check for required env vars
required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'DEV_API_ID', 'LOCAL_API_ID']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    sys.exit(1)

# Initialize Client
client = boto3.client(
    'apigateway',
    region_name=os.getenv('AWS_REGION', 'us-east-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
    verify=VERIFY_SSL
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

def compare_dicts(d1, d2, path=""):
    """
    Recursively compares two dictionaries and returns a list of difference strings.
    """
    differences = []
    
    # Keys in d1 but not d2
    for key in d1:
        if key not in d2:
            differences.append(f"MISSING KEY at {path}->{key}: Present in Dev, Missing in Local")
    
    # Keys in d2 but not d1
    for key in d2:
        if key not in d1:
            differences.append(f"EXTRA KEY at {path}->{key}: Missing in Dev, Present in Local")

    # Compare values for common keys
    for key in d1:
        if key in d2:
            val1 = d1[key]
            val2 = d2[key]
            current_path = f"{path}->{key}"

            # Ignore specific keys that will ALWAYS be different or shouldn't be checked
            if key in ['uri', 'credentials', 'passthroughBehavior']: 
                # You might want to compare URIs if you expect them to be identical strings
                # If they are different Lambda ARNs, we can skip strict equality check or log it differently
                pass 

            if isinstance(val1, dict) and isinstance(val2, dict):
                differences.extend(compare_dicts(val1, val2, current_path))
            elif isinstance(val1, list) and isinstance(val2, list):
                if val1 != val2:
                     differences.append(f"LIST MISMATCH at {current_path}\n      Dev:   {val1}\n      Local: {val2}")
            else:
                if val1 != val2:
                    differences.append(f"VALUE MISMATCH at {current_path}\n      Dev:   {val1}\n      Local: {val2}")

    return differences

def normalize_integration(method_data):
    """Extracts integration details often responsible for 'typos'"""
    if 'x-amazon-apigateway-integration' in method_data:
        integ = method_data['x-amazon-apigateway-integration']
        return {
            'type': integ.get('type'),
            'uri': integ.get('uri'),
            'httpMethod': integ.get('httpMethod'),
            'timeoutInMillis': integ.get('timeoutInMillis'),
            'requestParameters': integ.get('requestParameters')
        }
    return {}

def main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"gateway_diff_{timestamp}.txt"
    
    print(f"📝 Generating Report: {filename}")
    
    dev_json = get_api_export(os.getenv('DEV_API_ID'), "DEV Gateway")
    local_json = get_api_export(os.getenv('LOCAL_API_ID'), "LOCAL Gateway")

    if not dev_json or not local_json:
        return

    dev_paths = dev_json.get('paths', {})
    local_paths = local_json.get('paths', {})
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("========================================================\n")
        f.write(f" AWS API GATEWAY AUDIT REPORT\n")
        f.write(f" Generated: {timestamp}\n")
        f.write(f" Dev ID:    {os.getenv('DEV_API_ID')}\n")
        f.write(f" Local ID:  {os.getenv('LOCAL_API_ID')}\n")
        f.write("========================================================\n\n")

        issues_found = 0

        # Loop through every path in the Main Gateway
        all_paths = sorted(dev_paths.keys())
        
        for path in all_paths:
            if path not in local_paths:
                f.write(f"🔴 [MISSING PATH] {path}\n")
                f.write(f"   Action: This entire endpoint is missing in Local.\n\n")
                issues_found += 1
                continue

            # Path exists, check methods
            dev_methods = dev_paths[path]
            local_methods = local_paths[path]

            for method, dev_details in dev_methods.items():
                if method not in local_methods:
                    f.write(f"🟠 [MISSING METHOD] {path} [{method.upper()}]\n")
                    f.write(f"   Action: The path exists, but {method.upper()} is missing.\n\n")
                    issues_found += 1
                    continue

                # Compare Integration Details (The most common place for Typos)
                local_details = local_methods[method]
                
                dev_integ = normalize_integration(dev_details)
                local_integ = normalize_integration(local_details)

                # Check specifically for Integration Differences
                diffs = compare_dicts(dev_integ, local_integ, path="Integration")
                
                if diffs:
                    f.write(f"⚠️  [MISMATCH] {path} [{method.upper()}]\n")
                    for d in diffs:
                        f.write(f"   - {d}\n")
                    f.write("\n")
                    issues_found += 1

        if issues_found == 0:
            f.write("\n✅ RESULT: Perfect Match! No configuration differences found.\n")
            print("\n✅ No differences found. Logs saved to file.")
        else:
            f.write(f"\n❌ RESULT: Found {issues_found} issues that need attention.\n")
            print(f"\n⚠️  Found {issues_found} issues. Check {filename} for details.")

if __name__ == "__main__":
    main()
