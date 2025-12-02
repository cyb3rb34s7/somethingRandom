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
