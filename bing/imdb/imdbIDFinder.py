import os
import json
import time
import requests
import psycopg2
from datetime import datetime
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

# TMDB API Configuration
TMDB_BEARER_TOKEN = os.getenv('TMDB_BEARER_TOKEN')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# Request headers for TMDB
TMDB_HEADERS = {
    'Authorization': f'Bearer {TMDB_BEARER_TOKEN}',
    'Content-Type': 'application/json'
}

# Log file setup
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f'imdb_finder_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

class Logger:
    """Simple logger class to write to both console and file"""
    
    def __init__(self, log_file):
        self.log_file = log_file
        self.entries = []
    
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.entries.append(log_entry)
    
    def save(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.entries))

logger = Logger(LOG_FILE)

def get_entries_without_imdb(cursor):
    """
    Get all primary_topics that don't have IMDb entries in topic_sources
    
    Returns:
        List of tuples: [(primary_topic_id, name, type), ...]
    """
    cursor.execute("""
        SELECT pt.primary_topic_id, pt.name, pt.type
        FROM primary_topics pt
        WHERE pt.primary_topic_id NOT IN (
            SELECT DISTINCT primary_topic_id
            FROM topic_sources
            WHERE source_name = 'imdb' AND source_id_type = 'imdb_id'
        )
        ORDER BY pt.primary_topic_id
    """)
    
    return cursor.fetchall()

def search_tmdb(name, content_type):
    """
    Search TMDB for a movie or TV show
    
    Args:
        name: Title name to search
        content_type: 'movie' or 'show'
    
    Returns:
        TMDB ID if found, None otherwise
    """
    endpoint = 'movie' if content_type == 'movie' else 'tv'
    url = f'{TMDB_BASE_URL}/search/{endpoint}'
    
    params = {
        'query': name,
        'include_adult': 'false',
        'language': 'en-US',
        'page': 1
    }
    
    try:
        response = requests.get(url, headers=TMDB_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('results') and len(data['results']) > 0:
            # Get the first (most popular) result
            first_result = data['results'][0]
            tmdb_id = first_result.get('id')
            result_name = first_result.get('title' if content_type == 'movie' else 'name')
            popularity = first_result.get('popularity', 0)
            
            logger.log(f"  TMDB Search: Found '{result_name}' (ID: {tmdb_id}, Popularity: {popularity:.1f})")
            return tmdb_id, result_name
        else:
            logger.log(f"  TMDB Search: No results found", "WARNING")
            return None, None
            
    except Exception as e:
        logger.log(f"  TMDB Search Error: {str(e)}", "ERROR")
        return None, None

def get_imdb_id_from_tmdb(tmdb_id, content_type):
    """
    Get IMDb ID from TMDB using external IDs endpoint
    
    Args:
        tmdb_id: TMDB ID
        content_type: 'movie' or 'show'
    
    Returns:
        IMDb ID (tt format) if found, None otherwise
    """
    endpoint = 'movie' if content_type == 'movie' else 'tv'
    url = f'{TMDB_BASE_URL}/{endpoint}/{tmdb_id}/external_ids'
    
    try:
        response = requests.get(url, headers=TMDB_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        imdb_id = data.get('imdb_id')
        
        if imdb_id and imdb_id.startswith('tt'):
            logger.log(f"  IMDb ID Found: {imdb_id}")
            return imdb_id
        else:
            logger.log(f"  IMDb ID: Not available in TMDB", "WARNING")
            return None
            
    except Exception as e:
        logger.log(f"  IMDb ID Fetch Error: {str(e)}", "ERROR")
        return None

def insert_imdb_source(cursor, primary_topic_id, imdb_id):
    """
    Insert IMDb source into topic_sources
    
    Args:
        cursor: Database cursor
        primary_topic_id: Primary topic ID
        imdb_id: IMDb ID to insert
    
    Returns:
        True if successful, False otherwise
    """
    try:
        cursor.execute("""
            INSERT INTO topic_sources (primary_topic_id, source_id, source_name, source_id_type)
            VALUES (%s, %s, %s, %s)
        """, (primary_topic_id, imdb_id, 'imdb', 'imdb_id'))
        
        return True
        
    except Exception as e:
        logger.log(f"  DB Insert Error: {str(e)}", "ERROR")
        return False

def main():
    """
    Main execution function
    """
    logger.log("=" * 80)
    logger.log("TMDB TO IMDB ID FINDER")
    logger.log("Finding and adding IMDb IDs for entries without them")
    logger.log("=" * 80)
    
    # Statistics
    stats = {
        'total_entries': 0,
        'successfully_added': 0,
        'no_tmdb_match': 0,
        'no_imdb_id': 0,
        'insert_failed': 0,
        'api_errors': 0
    }
    
    failed_entries = []
    successful_entries = []
    
    try:
        # Connect to database
        logger.log("\nConnecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        logger.log("Database connected successfully")
        
        # Get entries without IMDb IDs
        logger.log("\nQuerying entries without IMDb IDs...")
        entries = get_entries_without_imdb(cursor)
        stats['total_entries'] = len(entries)
        
        if not entries:
            logger.log("No entries found that need IMDb IDs!", "INFO")
            cursor.close()
            conn.close()
            logger.save()
            return
        
        logger.log(f"Found {len(entries)} entries that need IMDb IDs\n")
        logger.log("=" * 80)
        
        # Process each entry
        for idx, (topic_id, name, content_type) in enumerate(entries, 1):
            logger.log(f"\n[{idx}/{len(entries)}] Processing: '{name}' (ID: {topic_id}, Type: {content_type})")
            
            # Search TMDB
            tmdb_id, tmdb_name = search_tmdb(name, content_type)
            
            if not tmdb_id:
                stats['no_tmdb_match'] += 1
                failed_entries.append({
                    'id': topic_id,
                    'name': name,
                    'type': content_type,
                    'reason': 'No TMDB match found'
                })
                logger.log(f"  Status: FAILED - No TMDB match\n")
                time.sleep(0.3)  # Rate limiting
                continue
            
            # Get IMDb ID
            imdb_id = get_imdb_id_from_tmdb(tmdb_id, content_type)
            
            if not imdb_id:
                stats['no_imdb_id'] += 1
                failed_entries.append({
                    'id': topic_id,
                    'name': name,
                    'type': content_type,
                    'tmdb_id': tmdb_id,
                    'tmdb_name': tmdb_name,
                    'reason': 'IMDb ID not available in TMDB'
                })
                logger.log(f"  Status: FAILED - No IMDb ID available\n")
                time.sleep(0.3)  # Rate limiting
                continue
            
            # Insert into database
            success = insert_imdb_source(cursor, topic_id, imdb_id)
            
            if success:
                stats['successfully_added'] += 1
                successful_entries.append({
                    'id': topic_id,
                    'name': name,
                    'type': content_type,
                    'imdb_id': imdb_id,
                    'tmdb_match': tmdb_name
                })
                logger.log(f"  Status: SUCCESS - IMDb ID added to topic_sources")
                
                # Commit in batches of 10
                if stats['successfully_added'] % 10 == 0:
                    conn.commit()
                    logger.log(f"  Committed batch ({stats['successfully_added']} total)")
            else:
                stats['insert_failed'] += 1
                failed_entries.append({
                    'id': topic_id,
                    'name': name,
                    'type': content_type,
                    'imdb_id': imdb_id,
                    'reason': 'Database insert failed'
                })
                logger.log(f"  Status: FAILED - Insert error")
            
            logger.log("")
            time.sleep(0.3)  # Rate limiting
        
        # Final commit
        conn.commit()
        logger.log("\n" + "=" * 80)
        logger.log("PROCESSING COMPLETE - Final commit executed")
        logger.log("=" * 80)
        
        # Generate detailed summary
        logger.log("\n" + "=" * 80)
        logger.log("SUMMARY STATISTICS")
        logger.log("=" * 80)
        logger.log(f"Total entries processed:     {stats['total_entries']}")
        logger.log(f"Successfully added:          {stats['successfully_added']}")
        logger.log(f"No TMDB match found:         {stats['no_tmdb_match']}")
        logger.log(f"No IMDb ID available:        {stats['no_imdb_id']}")
        logger.log(f"Database insert failed:      {stats['insert_failed']}")
        logger.log(f"Success rate:                {(stats['successfully_added']/stats['total_entries']*100):.1f}%")
        logger.log("=" * 80)
        
        # Log successful entries details
        if successful_entries:
            logger.log("\n" + "=" * 80)
            logger.log(f"SUCCESSFULLY ADDED ({len(successful_entries)} entries)")
            logger.log("=" * 80)
            for entry in successful_entries:
                logger.log(f"ID: {entry['id']} | {entry['name']} | IMDb: {entry['imdb_id']}")
                if entry['name'] != entry['tmdb_match']:
                    logger.log(f"  Note: TMDB matched as '{entry['tmdb_match']}'")
        
        # Log failed entries details
        if failed_entries:
            logger.log("\n" + "=" * 80)
            logger.log(f"FAILED ENTRIES ({len(failed_entries)} entries)")
            logger.log("=" * 80)
            for entry in failed_entries:
                logger.log(f"ID: {entry['id']} | {entry['name']} | Type: {entry['type']}")
                logger.log(f"  Reason: {entry['reason']}")
                if 'tmdb_name' in entry:
                    logger.log(f"  TMDB Match: {entry['tmdb_name']} (ID: {entry['tmdb_id']})")
        
        # Close database connection
        cursor.close()
        conn.close()
        
        logger.log("\n" + "=" * 80)
        logger.log(f"Log file saved to: {LOG_FILE}")
        logger.log("=" * 80)
        
    except psycopg2.Error as e:
        logger.log(f"\nDatabase error: {str(e)}", "ERROR")
    except Exception as e:
        logger.log(f"\nUnexpected error: {str(e)}", "ERROR")
    finally:
        # Save log file
        logger.save()
        print(f"\nDetailed log saved to: {LOG_FILE}")

if __name__ == "__main__":
    main()