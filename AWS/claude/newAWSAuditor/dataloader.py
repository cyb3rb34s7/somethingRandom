# ==========================================
# UPDATED DATA LOADER
# Replace the existing load_data_recursively function with this
# ==========================================

@st.cache_data
def load_data_recursively(folder_path):
    data = {
        "ecs_td": {}, 
        "s3": {}, 
        "api_gw": {}, 
        "lambda": {},
        "sqs": {}, 
        "sns": {}, 
        "lb": {}, 
        "sg": {}, 
        "iam": {}
    }
    
    if not folder_path or not os.path.exists(folder_path):
        return data
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json") and not file.startswith("metadata") and file != "_index.json":
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r') as f:
                        content = json.load(f)
                    name = file.replace('.json', '')
                    parent = os.path.basename(root)
                    
                    # ECS Task Definitions
                    if "task_definitions" in root or "task_definitions" in parent:
                        if 'containerDefinitions' in content or 'taskDefinition' in content:
                            data["ecs_td"][name] = content
                    
                    # S3 Buckets (policies/config)
                    elif "s3_buckets" in root:
                        data["s3"][name] = content
                    
                    # API Gateway
                    elif "api_gateway" in root:
                        data["api_gw"][name] = content
                    
                    # Lambda Functions
                    elif "lambda_functions" in root:
                        data["lambda"][name] = content
                    
                    # SQS Queues
                    elif "sqs_queues" in root:
                        data["sqs"][name] = content
                    
                    # SNS Topics
                    elif "sns_topics" in root:
                        data["sns"][name] = content
                    
                    # Load Balancers
                    elif "load_balancers" in root:
                        data["lb"][name] = content
                    
                    # Security Groups
                    elif "security_groups" in root:
                        data["sg"][name] = content
                    
                    # IAM Roles
                    elif "iam_roles" in root:
                        data["iam"][name] = content
                
                except Exception as e:
                    pass  # Skip files that can't be loaded
    
    return data
