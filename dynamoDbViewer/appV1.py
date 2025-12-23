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

# Helper function to convert Decimal to float/int for JSON serialization
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    raise TypeError

# Initialize session state
if 'selected_table' not in st.session_state:
    st.session_state.selected_table = None
if 'selected_item' not in st.session_state:
    st.session_state.selected_item = None
if 'dynamodb_client' not in st.session_state:
    st.session_state.dynamodb_client = None
if 'dynamodb_resource' not in st.session_state:
    st.session_state.dynamodb_resource = None

# Function to initialize AWS connection
def init_aws_connection():
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
        return None, None, str(e)

# Function to get all tables
@st.cache_data(ttl=300)
def get_tables(_client):
    try:
        tables = []
        paginator = _client.get_paginator('list_tables')
        for page in paginator.paginate():
            tables.extend(page['TableNames'])
        return tables, None
    except Exception as e:
        return [], str(e)

# Function to get table details
@st.cache_data(ttl=300)
def get_table_info(_client, table_name):
    try:
        response = _client.describe_table(TableName=table_name)
        return response['Table'], None
    except Exception as e:
        return None, str(e)

# Function to scan table
def scan_table(resource, table_name, limit=100):
    try:
        table = resource.Table(table_name)
        response = table.scan(Limit=limit)
        items = response.get('Items', [])
        return items, None
    except Exception as e:
        return [], str(e)

# Function to get item by key
def get_item_by_key(resource, table_name, key_dict):
    try:
        table = resource.Table(table_name)
        response = table.get_item(Key=key_dict)
        return response.get('Item'), None
    except Exception as e:
        return None, str(e)

# Function to query table
def query_table(resource, table_name, partition_key_name, partition_key_value, sort_key_name=None, sort_key_value=None, limit=100):
    try:
        table = resource.Table(table_name)
        
        if sort_key_name and sort_key_value:
            key_condition = Key(partition_key_name).eq(partition_key_value) & Key(sort_key_name).eq(sort_key_value)
        else:
            key_condition = Key(partition_key_name).eq(partition_key_value)
        
        response = table.query(
            KeyConditionExpression=key_condition,
            Limit=limit
        )
        return response.get('Items', []), None
    except Exception as e:
        return [], str(e)

# Function to format attribute value with type
def format_attribute_with_type(value):
    if isinstance(value, str):
        return f"String: {value}"
    elif isinstance(value, (int, float, Decimal)):
        return f"Number: {value}"
    elif isinstance(value, bool):
        return f"Boolean: {value}"
    elif isinstance(value, list):
        return f"List: {json.dumps(value, indent=2, default=decimal_default)}"
    elif isinstance(value, dict):
        return f"Map: {json.dumps(value, indent=2, default=decimal_default)}"
    elif value is None:
        return "Null"
    else:
        return f"{type(value).__name__}: {str(value)}"

# Main app
def main():
    st.title("🗄️ DynamoDB Explorer")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        # Initialize connection
        if st.session_state.dynamodb_client is None:
            with st.spinner("Connecting to AWS..."):
                client, resource, error = init_aws_connection()
                if error:
                    st.error(f"❌ Connection failed: {error}")
                    st.info("Please check your .env file and ensure AWS credentials are set correctly.")
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
            st.error(f"Error loading tables: {error}")
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
            st.warning("No tables found in this region")
            return
        
        # Refresh button
        if st.button("🔄 Refresh Tables", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Main content area
    if st.session_state.selected_table:
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Table Overview", "🔍 Browse Items", "📝 Item Details", "🔎 Query/Search"])
        
        # Tab 1: Table Overview
        with tab1:
            st.header(f"Table: {st.session_state.selected_table}")
            
            table_info, error = get_table_info(st.session_state.dynamodb_client, st.session_state.selected_table)
            if error:
                st.error(f"Error loading table info: {error}")
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
                
                key_df = pd.DataFrame([
                    {
                        'Key Type': key['KeyType'],
                        'Attribute Name': key['AttributeName'],
                        'Data Type': attribute_definitions.get(key['AttributeName'], 'Unknown')
                    }
                    for key in key_schema
                ])
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
        
        # Tab 2: Browse Items
        with tab2:
            st.header("Browse Items")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                search_query = st.text_input("🔍 Search in results (filters loaded data)", "")
            with col2:
                limit = st.number_input("Items to load", min_value=10, max_value=1000, value=100, step=10)
            
            if st.button("📥 Load Items", use_container_width=True):
                with st.spinner("Loading items..."):
                    items, error = scan_table(st.session_state.dynamodb_resource, st.session_state.selected_table, limit)
                    if error:
                        st.error(f"Error loading items: {error}")
                    else:
                        st.session_state.items = items
            
            if 'items' in st.session_state and st.session_state.items:
                items = st.session_state.items
                
                # Convert to DataFrame
                df = pd.DataFrame(items)
                
                # Apply search filter
                if search_query:
                    mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
                    df = df[mask]
                
                st.info(f"Showing {len(df)} of {len(items)} items")
                
                # Display dataframe
                st.dataframe(df, use_container_width=True, height=400)
                
                # Export functionality
                col1, col2 = st.columns(2)
                with col1:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download as CSV",
                        data=csv,
                        file_name=f"{st.session_state.selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                with col2:
                    json_data = json.dumps(items, indent=2, default=decimal_default)
                    st.download_button(
                        label="⬇️ Download as JSON",
                        data=json_data,
                        file_name=f"{st.session_state.selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                # Select item for details
                st.divider()
                st.subheader("Select Item for Details")
                if len(df) > 0:
                    item_index = st.selectbox(
                        "Choose item by row number",
                        options=range(len(df)),
                        format_func=lambda x: f"Row {x}: {str(df.iloc[x].to_dict())[:100]}..."
                    )
                    if st.button("View Selected Item Details"):
                        st.session_state.selected_item = items[item_index]
                        st.success("Item selected! Go to 'Item Details' tab")
        
        # Tab 3: Item Details
        with tab3:
            st.header("Item Details")
            
            if st.session_state.selected_item:
                item = st.session_state.selected_item
                
                st.success("✅ Item loaded")
                
                # Display as expandable JSON
                st.subheader("Raw JSON View")
                st.json(json.loads(json.dumps(item, default=decimal_default)))
                
                st.divider()
                
                # Display attributes with types
                st.subheader("Attributes with Types")
                
                attr_data = []
                for key, value in item.items():
                    attr_data.append({
                        'Attribute Name': key,
                        'Value': str(value)[:100] + ('...' if len(str(value)) > 100 else ''),
                        'Type': type(value).__name__,
                        'Full Value': value
                    })
                
                attr_df = pd.DataFrame(attr_data)
                st.dataframe(attr_df[['Attribute Name', 'Type', 'Value']], use_container_width=True, hide_index=True)
                
                # Detailed view for each attribute
                st.subheader("Detailed Attribute View")
                for attr in attr_data:
                    with st.expander(f"🔹 {attr['Attribute Name']} ({attr['Type']})"):
                        if isinstance(attr['Full Value'], (dict, list)):
                            st.json(json.loads(json.dumps(attr['Full Value'], default=decimal_default)))
                        else:
                            st.code(str(attr['Full Value']))
                
                # Clear selection
                if st.button("Clear Selection"):
                    st.session_state.selected_item = None
                    st.rerun()
            else:
                st.info("No item selected. Go to 'Browse Items' tab and select an item to view its details.")
        
        # Tab 4: Query/Search
        with tab4:
            st.header("Query Table")
            
            # Get table key schema
            table_info, _ = get_table_info(st.session_state.dynamodb_client, st.session_state.selected_table)
            if table_info:
                key_schema = table_info.get('KeySchema', [])
                
                partition_key = next((key['AttributeName'] for key in key_schema if key['KeyType'] == 'HASH'), None)
                sort_key = next((key['AttributeName'] for key in key_schema if key['KeyType'] == 'RANGE'), None)
                
                st.info(f"Primary Key: {partition_key}" + (f" | Sort Key: {sort_key}" if sort_key else ""))
                
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
                
                if st.button("🔎 Execute Query", use_container_width=True):
                    if partition_value:
                        with st.spinner("Querying..."):
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
                                st.error(f"Query error: {error}")
                            elif results:
                                st.success(f"Found {len(results)} item(s)")
                                df = pd.DataFrame(results)
                                st.dataframe(df, use_container_width=True)
                                
                                # Export
                                json_data = json.dumps(results, indent=2, default=decimal_default)
                                st.download_button(
                                    label="⬇️ Download Results as JSON",
                                    data=json_data,
                                    file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json"
                                )
                            else:
                                st.warning("No items found matching the query")
                    else:
                        st.warning(f"Please enter a value for {partition_key}")

if __name__ == "__main__":
    main()