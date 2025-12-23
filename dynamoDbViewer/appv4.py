import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key, Attr
import pandas as pd
import json
from datetime import datetime
from decimal import Decimal
import os
from dotenv import load_dotenv
import urllib3
import traceback

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="DynamoDB Explorer",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-inactive {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS - TYPE CONVERSION & VALIDATION
# ============================================================================

def convert_dynamodb_types(obj):
    """
    Recursively convert DynamoDB types to Python native types
    Handles: Decimal, Set, Binary, nested dicts/lists
    """
    if isinstance(obj, Decimal):
        # Convert Decimal to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, set):
        # Convert sets to lists
        return list(obj)
    elif isinstance(obj, bytes):
        # Convert binary to base64 string for display
        import base64
        return base64.b64encode(obj).decode('utf-8')
    elif isinstance(obj, dict):
        # Recursively convert dict values
        return {k: convert_dynamodb_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Recursively convert list items
        return [convert_dynamodb_types(item) for item in obj]
    else:
        return obj

def safe_json_serializer(obj):
    """Safe JSON serializer for all DynamoDB types"""
    try:
        return convert_dynamodb_types(obj)
    except Exception:
        return str(obj)

def validate_items_list(items, source="unknown"):
    """
    Validate that items is a proper list
    Returns: (valid_items_list, error_message)
    """
    if items is None:
        return [], f"Items from {source} is None"
    
    if not isinstance(items, list):
        return [], f"Items from {source} is not a list, got {type(items).__name__}"
    
    # Additional validation - ensure it's a list of dicts
    if items:
        if not isinstance(items[0], dict):
            return [], f"Items from {source} contains non-dict elements"
    
    return items, None

def flatten_for_display(item, max_length=100):
    """
    Flatten a DynamoDB item for table display
    Converts complex nested objects to truncated strings
    """
    if not isinstance(item, dict):
        return {}
    
    flattened = {}
    for key, value in item.items():
        try:
            converted_value = convert_dynamodb_types(value)
            
            if isinstance(converted_value, (dict, list)):
                # Convert to JSON string and truncate
                json_str = json.dumps(converted_value, ensure_ascii=False)
                if len(json_str) > max_length:
                    flattened[key] = json_str[:max_length] + "..."
                else:
                    flattened[key] = json_str
            else:
                # Simple types - just convert to string if too long
                str_value = str(converted_value)
                if len(str_value) > max_length:
                    flattened[key] = str_value[:max_length] + "..."
                else:
                    flattened[key] = converted_value
        except Exception as e:
            flattened[key] = f"[Error: {str(e)}]"
    
    return flattened

def safe_items_to_dataframe(items):
    """
    Convert list of DynamoDB items to pandas DataFrame with full error handling
    """
    # Validate input
    validated_items, error = validate_items_list(items, "dataframe conversion")
    if error:
        st.error(f"❌ Validation Error: {error}")
        return pd.DataFrame()
    
    if not validated_items:
        return pd.DataFrame()
    
    try:
        # Flatten all items for display
        flattened_items = []
        for idx, item in enumerate(validated_items):
            try:
                flattened = flatten_for_display(item)
                flattened_items.append(flattened)
            except Exception as e:
                st.warning(f"⚠️ Could not flatten item {idx}: {str(e)}")
                # Add a placeholder
                flattened_items.append({"error": f"Item {idx} - {str(e)}"})
        
        if not flattened_items:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(flattened_items)
        return df
        
    except Exception as e:
        st.error(f"❌ DataFrame creation failed: {str(e)}")
        st.code(traceback.format_exc())
        
        # Ultimate fallback - create simple single column DataFrame
        try:
            simple_data = [{"Item_JSON": json.dumps(convert_dynamodb_types(item), ensure_ascii=False)[:200] + "..."} 
                          for item in validated_items]
            return pd.DataFrame(simple_data)
        except Exception as fallback_error:
            st.error(f"❌ Even fallback failed: {str(fallback_error)}")
            return pd.DataFrame({"Error": ["Could not convert items to DataFrame"]})

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize all session state variables with correct types"""
    if 'selected_table' not in st.session_state:
        st.session_state.selected_table = None
    
    if 'selected_item' not in st.session_state:
        st.session_state.selected_item = None
    
    if 'dynamodb_client' not in st.session_state:
        st.session_state.dynamodb_client = None
    
    if 'dynamodb_resource' not in st.session_state:
        st.session_state.dynamodb_resource = None
    
    # CRITICAL: Initialize items as empty list, NEVER as None or method
    if 'items' not in st.session_state:
        st.session_state.items = []
    
    # Ensure items is always a list
    if not isinstance(st.session_state.items, list):
        st.warning(f"⚠️ Session items was {type(st.session_state.items)}, resetting to empty list")
        st.session_state.items = []

# ============================================================================
# AWS CONNECTION FUNCTIONS
# ============================================================================

def init_aws_connection():
    """Initialize AWS DynamoDB connection with full error handling"""
    try:
        # Get credentials from environment
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.getenv('AWS_SESSION_TOKEN')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if not aws_access_key or not aws_secret_key:
            return None, None, "AWS credentials not found in environment variables"
        
        # Create session with SSL verification disabled
        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=aws_session_token,
            region_name=aws_region
        )
        
        # Create client and resource with SSL verification disabled
        client = session.client('dynamodb', verify=False)
        resource = session.resource('dynamodb', verify=False)
        
        # Test connection
        client.list_tables(Limit=1)
        
        return client, resource, None
        
    except Exception as e:
        error_details = f"{str(e)}\n\n{traceback.format_exc()}"
        return None, None, error_details

# ============================================================================
# DYNAMODB OPERATIONS
# ============================================================================

@st.cache_data(ttl=300)
def get_tables(_client):
    """Get all DynamoDB tables with error handling"""
    try:
        tables = []
        paginator = _client.get_paginator('list_tables')
        for page in paginator.paginate():
            tables.extend(page['TableNames'])
        
        # Validate result
        if not isinstance(tables, list):
            return [], f"Expected list of tables, got {type(tables)}"
        
        return tables, None
        
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return [], error_msg

@st.cache_data(ttl=300)
def get_table_info(_client, table_name):
    """Get table metadata with error handling"""
    try:
        response = _client.describe_table(TableName=table_name)
        return response['Table'], None
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return None, error_msg

def scan_table(resource, table_name, limit=100):
    """
    Scan DynamoDB table and return items as a list
    Returns: (list_of_items, error_message)
    """
    try:
        table = resource.Table(table_name)
        response = table.scan(Limit=int(limit))
        
        # Get items from response
        items = response.get('Items', [])
        
        # CRITICAL VALIDATION
        if not isinstance(items, list):
            return [], f"Scan returned non-list type: {type(items)}"
        
        # Convert all DynamoDB types
        converted_items = [convert_dynamodb_types(item) for item in items]
        
        return converted_items, None
        
    except Exception as e:
        error_msg = f"Scan error: {str(e)}\n{traceback.format_exc()}"
        return [], error_msg

def query_table(resource, table_name, partition_key_name, partition_key_value, 
                sort_key_name=None, sort_key_value=None, limit=100):
    """
    Query DynamoDB table with error handling
    Returns: (list_of_items, error_message)
    """
    try:
        table = resource.Table(table_name)
        
        # Build key condition
        if sort_key_name and sort_key_value:
            key_condition = Key(partition_key_name).eq(partition_key_value) & Key(sort_key_name).eq(sort_key_value)
        else:
            key_condition = Key(partition_key_name).eq(partition_key_value)
        
        response = table.query(
            KeyConditionExpression=key_condition,
            Limit=int(limit)
        )
        
        items = response.get('Items', [])
        
        # CRITICAL VALIDATION
        if not isinstance(items, list):
            return [], f"Query returned non-list type: {type(items)}"
        
        # Convert all DynamoDB types
        converted_items = [convert_dynamodb_types(item) for item in items]
        
        return converted_items, None
        
    except Exception as e:
        error_msg = f"Query error: {str(e)}\n{traceback.format_exc()}"
        return [], error_msg

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Initialize session state FIRST
    init_session_state()
    
    st.title("🗄️ DynamoDB Explorer")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        # Initialize connection
        if st.session_state.dynamodb_client is None:
            with st.spinner("Connecting to AWS..."):
                client, resource, error = init_aws_connection()
                if error:
                    st.error(f"❌ Connection failed:")
                    st.code(error)
                    st.info("💡 Please check your .env file and ensure AWS credentials are set correctly.")
                    return
                else:
                    st.session_state.dynamodb_client = client
                    st.session_state.dynamodb_resource = resource
                    st.success("✅ Connected to AWS")
        else:
            st.success("✅ Connected to AWS")
        
        # Region display
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        st.info(f"📍 Region: {aws_region}")
        
        st.divider()
        
        # Get tables
        tables, error = get_tables(st.session_state.dynamodb_client)
        if error:
            st.error(f"❌ Error loading tables:")
            st.code(error)
            return
        
        # Table selector
        st.subheader("Select Table")
        if tables:
            selected_table = st.selectbox(
                "Available Tables",
                options=tables,
                index=tables.index(st.session_state.selected_table) if st.session_state.selected_table in tables else 0
            )
            st.session_state.selected_table = selected_table
        else:
            st.warning("⚠️ No tables found in this region")
            return
        
        # Refresh button
        if st.button("🔄 Refresh Tables", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Main content area
    if st.session_state.selected_table:
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Table Overview", "🔍 Browse Items", "📝 Item Details", "🔎 Query/Search"])
        
        # ====================================================================
        # TAB 1: TABLE OVERVIEW
        # ====================================================================
        with tab1:
            st.header(f"Table: {st.session_state.selected_table}")
            
            table_info, error = get_table_info(st.session_state.dynamodb_client, st.session_state.selected_table)
            if error:
                st.error(f"❌ Error loading table info:")
                st.code(error)
            else:
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Item Count", f"{table_info.get('ItemCount', 0):,}")
                with col2:
                    table_size_bytes = table_info.get('TableSizeBytes', 0)
                    table_size_mb = table_size_bytes / (1024 * 1024)
                    st.metric("Table Size", f"{table_size_mb:.2f} MB")
                with col3:
                    status = table_info.get('TableStatus', 'UNKNOWN')
                    st.metric("Status", status)
                with col4:
                    creation_date = table_info.get('CreationDateTime')
                    if creation_date:
                        st.metric("Created", creation_date.strftime("%Y-%m-%d"))
                
                st.divider()
                
                # Key Schema
                st.subheader("Key Schema")
                key_schema = table_info.get('KeySchema', [])
                attribute_definitions = {attr['AttributeName']: attr['AttributeType'] 
                                       for attr in table_info.get('AttributeDefinitions', [])}
                
                if key_schema:
                    key_data = []
                    for key in key_schema:
                        key_data.append({
                            'Key Type': key['KeyType'],
                            'Attribute Name': key['AttributeName'],
                            'Data Type': attribute_definitions.get(key['AttributeName'], 'Unknown')
                        })
                    key_df = pd.DataFrame(key_data)
                    st.dataframe(key_df, use_container_width=True, hide_index=True)
                
                # Global Secondary Indexes
                gsi = table_info.get('GlobalSecondaryIndexes', [])
                if gsi:
                    st.subheader("Global Secondary Indexes")
                    for index in gsi:
                        with st.expander(f"📑 {index['IndexName']}"):
                            st.json(index)
                
                # Local Secondary Indexes
                lsi = table_info.get('LocalSecondaryIndexes', [])
                if lsi:
                    st.subheader("Local Secondary Indexes")
                    for index in lsi:
                        with st.expander(f"📑 {index['IndexName']}"):
                            st.json(index)
        
        # ====================================================================
        # TAB 2: BROWSE ITEMS
        # ====================================================================
        with tab2:
            st.header("Browse Items")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                search_query = st.text_input("🔍 Search in results (filters loaded data)", "")
            with col2:
                limit = st.number_input("Items to load", min_value=10, max_value=1000, value=100, step=10)
            
            if st.button("📥 Load Items", use_container_width=True, type="primary"):
                with st.spinner("Loading items from DynamoDB..."):
                    # Call scan_table and get results
                    items_result, error = scan_table(
                        st.session_state.dynamodb_resource, 
                        st.session_state.selected_table, 
                        limit
                    )
                    
                    if error:
                        st.error(f"❌ Error loading items:")
                        st.code(error)
                        st.session_state.items = []
                    else:
                        # Validate result before storing
                        validated_items, validation_error = validate_items_list(items_result, "scan_table")
                        
                        if validation_error:
                            st.error(f"❌ Validation failed: {validation_error}")
                            st.session_state.items = []
                        else:
                            # Store in session state
                            st.session_state.items = validated_items
                            st.success(f"✅ Successfully loaded {len(validated_items)} items")
            
            # Display loaded items
            if isinstance(st.session_state.items, list) and len(st.session_state.items) > 0:
                items = st.session_state.items
                
                st.info(f"📊 Total items loaded: {len(items)}")
                
                # Convert to DataFrame
                df = safe_items_to_dataframe(items)
                
                if df.empty:
                    st.warning("⚠️ No data to display")
                else:
                    # Apply search filter
                    if search_query:
                        try:
                            mask = df.astype(str).apply(
                                lambda x: x.str.contains(search_query, case=False, na=False)
                            ).any(axis=1)
                            df = df[mask]
                            st.info(f"🔍 Filtered to {len(df)} items matching '{search_query}'")
                        except Exception as filter_error:
                            st.warning(f"⚠️ Search filter error: {str(filter_error)}")
                    
                    # Display dataframe
                    st.dataframe(df, use_container_width=True, height=400)
                    
                    # Export functionality
                    col1, col2 = st.columns(2)
                    with col1:
                        try:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="⬇️ Download as CSV",
                                data=csv,
                                file_name=f"{st.session_state.selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"CSV export error: {str(e)}")
                    
                    with col2:
                        try:
                            json_data = json.dumps(items, indent=2, default=safe_json_serializer, ensure_ascii=False)
                            st.download_button(
                                label="⬇️ Download as JSON",
                                data=json_data,
                                file_name=f"{st.session_state.selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                        except Exception as e:
                            st.error(f"JSON export error: {str(e)}")
                    
                    # Select item for details
                    st.divider()
                    st.subheader("Select Item for Details")
                    
                    # Create simple item selector
                    item_options = []
                    for idx in range(len(items)):
                        try:
                            item = items[idx]
                            # Get first 3 keys for preview
                            preview_keys = list(item.keys())[:3]
                            preview = ", ".join([f"{k}: {str(item[k])[:30]}" for k in preview_keys])
                            item_options.append(f"Row {idx}: {preview}...")
                        except Exception:
                            item_options.append(f"Row {idx}: [Preview unavailable]")
                    
                    item_index = st.selectbox(
                        "Choose item by row number",
                        options=range(len(items)),
                        format_func=lambda x: item_options[x]
                    )
                    
                    if st.button("👁️ View Selected Item Details", use_container_width=True):
                        st.session_state.selected_item = items[item_index]
                        st.success("✅ Item selected! Switch to 'Item Details' tab")
            else:
                st.info("👆 Click 'Load Items' button above to fetch data from the table")
        
        # ====================================================================
        # TAB 3: ITEM DETAILS
        # ====================================================================
        with tab3:
            st.header("Item Details")
            
            if st.session_state.selected_item and isinstance(st.session_state.selected_item, dict):
                item = st.session_state.selected_item
                
                st.success("✅ Item loaded successfully")
                
                # Display as expandable JSON
                st.subheader("Raw JSON View")
                try:
                    json_display = json.dumps(item, indent=2, default=safe_json_serializer, ensure_ascii=False)
                    st.json(json.loads(json_display))
                except Exception as e:
                    st.error(f"JSON display error: {str(e)}")
                    st.code(str(item))
                
                st.divider()
                
                # Display attributes with types
                st.subheader("Attributes Table")
                
                attr_data = []
                for key, value in item.items():
                    try:
                        converted_value = convert_dynamodb_types(value)
                        value_str = str(converted_value)[:100]
                        if len(str(converted_value)) > 100:
                            value_str += "..."
                        
                        attr_data.append({
                            'Attribute Name': key,
                            'Type': type(converted_value).__name__,
                            'Value Preview': value_str,
                            'Full Value': converted_value
                        })
                    except Exception as e:
                        attr_data.append({
                            'Attribute Name': key,
                            'Type': 'Error',
                            'Value Preview': f"[Error: {str(e)}]",
                            'Full Value': None
                        })
                
                if attr_data:
                    # Create display DataFrame
                    attr_display_df = pd.DataFrame([
                        {
                            'Attribute Name': attr['Attribute Name'],
                            'Type': attr['Type'],
                            'Value Preview': attr['Value Preview']
                        }
                        for attr in attr_data
                    ])
                    
                    st.dataframe(attr_display_df, use_container_width=True, hide_index=True)
                    
                    # Detailed view for each attribute
                    st.subheader("Detailed Attribute View")
                    for attr in attr_data:
                        with st.expander(f"🔹 {attr['Attribute Name']} ({attr['Type']})"):
                            try:
                                if isinstance(attr['Full Value'], (dict, list)):
                                    st.json(json.loads(json.dumps(attr['Full Value'], default=safe_json_serializer)))
                                elif attr['Full Value'] is not None:
                                    st.code(str(attr['Full Value']))
                                else:
                                    st.write("No value available")
                            except Exception as e:
                                st.error(f"Display error: {str(e)}")
                                st.code(str(attr['Full Value']))
                
                # Clear selection
                if st.button("🔄 Clear Selection", use_container_width=True):
                    st.session_state.selected_item = None
                    st.rerun()
            else:
                st.info("ℹ️ No item selected. Go to 'Browse Items' tab and select an item to view its details.")
        
        # ====================================================================
        # TAB 4: QUERY/SEARCH
        # ====================================================================
        with tab4:
            st.header("Query Table")
            
            # Get table key schema
            table_info, _ = get_table_info(st.session_state.dynamodb_client, st.session_state.selected_table)
            if table_info:
                key_schema = table_info.get('KeySchema', [])
                
                partition_key = next((key['AttributeName'] for key in key_schema if key['KeyType'] == 'HASH'), None)
                sort_key = next((key['AttributeName'] for key in key_schema if key['KeyType'] == 'RANGE'), None)
                
                if partition_key:
                    st.info(f"🔑 Primary Key: **{partition_key}**" + (f" | Sort Key: **{sort_key}**" if sort_key else ""))
                    
                    # Query inputs
                    col1, col2 = st.columns(2)
                    with col1:
                        partition_value = st.text_input(f"Enter {partition_key} value", "")
                    with col2:
                        if sort_key:
                            sort_value = st.text_input(f"Enter {sort_key} value (optional)", "")
                        else:
                            sort_value = None
                    
                    query_limit = st.number_input("Max results", min_value=1, max_value=1000, value=100)
                    
                    if st.button("🔎 Execute Query", use_container_width=True, type="primary"):
                        if partition_value:
                            with st.spinner("Querying DynamoDB..."):
                                results, error = query_table(
                                    st.session_state.dynamodb_resource,
                                    st.session_state.selected_table,
                                    partition_key,
                                    partition_value,
                                    sort_key if sort_value else None,
                                    sort_value if sort_value else None,
                                    query_limit
                                )
                                
                                if error:
                                    st.error(f"❌ Query error:")
                                    st.code(error)
                                elif results:
                                    st.success(f"✅ Found {len(results)} item(s)")
                                    
                                    # Convert to DataFrame
                                    df = safe_items_to_dataframe(results)
                                    st.dataframe(df, use_container_width=True)
                                    
                                    # Export
                                    try:
                                        json_data = json.dumps(results, indent=2, default=safe_json_serializer, ensure_ascii=False)
                                        st.download_button(
                                            label="⬇️ Download Results as JSON",
                                            data=json_data,
                                            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                            mime="application/json"
                                        )
                                    except Exception as e:
                                        st.error(f"Export error: {str(e)}")
                                else:
                                    st.warning("⚠️ No items found matching the query")
                        else:
                            st.warning(f"⚠️ Please enter a value for {partition_key}")
                else:
                    st.error("❌ Could not determine primary key for this table")

if __name__ == "__main__":
    main()