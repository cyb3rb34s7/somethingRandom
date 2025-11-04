import os
import html
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'your_database'),
    'user': os.getenv('DB_USER', 'your_user'),
    'password': os.getenv('DB_PASSWORD', 'your_password'),
    'port': os.getenv('DB_PORT', '5432')
}

def find_records_with_html_entities(cursor):
    """
    Find all records in primary_topics that contain HTML entities
    
    Returns:
        List of tuples: [(primary_topic_id, current_name, decoded_name), ...]
    """
    # Find records that contain common HTML entity patterns
    cursor.execute("""
        SELECT primary_topic_id, name
        FROM primary_topics
        WHERE name LIKE '%&%'
        ORDER BY primary_topic_id
    """)
    
    records = cursor.fetchall()
    
    # Decode and prepare changes
    changes = []
    for topic_id, current_name in records:
        decoded_name = html.unescape(current_name)
        
        # Only include if the name actually changed after decoding
        if current_name != decoded_name:
            changes.append((topic_id, current_name, decoded_name))
    
    return changes

def preview_changes(changes):
    """
    Display the proposed changes in a readable format
    
    Args:
        changes: List of tuples [(id, old_name, new_name), ...]
    """
    if not changes:
        print("No records found that need fixing!")
        return
    
    print("\n" + "=" * 80)
    print(f"FOUND {len(changes)} RECORDS WITH HTML ENTITIES")
    print("=" * 80)
    
    for idx, (topic_id, old_name, new_name) in enumerate(changes, 1):
        print(f"\n[{idx}] ID: {topic_id}")
        print(f"  BEFORE: {old_name}")
        print(f"  AFTER:  {new_name}")
    
    print("\n" + "=" * 80)

def apply_changes(conn, changes):
    """
    Apply the name fixes to the database
    
    Args:
        conn: Database connection
        changes: List of tuples [(id, old_name, new_name), ...]
    
    Returns:
        Number of successfully updated records
    """
    cursor = conn.cursor()
    updated_count = 0
    
    try:
        for topic_id, old_name, new_name in changes:
            try:
                cursor.execute("""
                    UPDATE primary_topics
                    SET name = %s
                    WHERE primary_topic_id = %s AND name = %s
                """, (new_name, topic_id, old_name))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    
            except Exception as e:
                print(f"Error updating ID {topic_id}: {str(e)}")
                continue
        
        # Commit all changes
        conn.commit()
        print(f"\n✓ Successfully updated {updated_count} records")
        
    except Exception as e:
        print(f"Error during update: {str(e)}")
        conn.rollback()
        updated_count = 0
    finally:
        cursor.close()
    
    return updated_count

def main():
    """
    Main execution function
    """
    print("=" * 80)
    print("DATABASE NAME CLEANUP TOOL")
    print("Fixes HTML entities in primary_topics table")
    print("=" * 80)
    
    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✓ Connected successfully")
        
        # Find records that need fixing
        print("\nScanning for records with HTML entities...")
        changes = find_records_with_html_entities(cursor)
        
        if not changes:
            print("\n✓ No records found that need fixing!")
            cursor.close()
            conn.close()
            return
        
        # Preview the changes
        preview_changes(changes)
        
        # Ask for confirmation
        print("\n" + "=" * 80)
        response = input("\nDo you want to apply these changes? (yes/no): ").strip().lower()
        
        if response in ['yes', 'y']:
            print("\nApplying changes...")
            updated_count = apply_changes(conn, changes)
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Total records found: {len(changes)}")
            print(f"Successfully updated: {updated_count}")
            print("=" * 80)
        else:
            print("\n✗ Changes cancelled. No updates were made.")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {str(e)}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()