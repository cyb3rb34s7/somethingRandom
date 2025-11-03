import os
import time
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values

# Database connection parameters from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'your_database'),
    'user': os.getenv('DB_USER', 'your_user'),
    'password': os.getenv('DB_PASSWORD', 'your_password'),
    'port': os.getenv('DB_PORT', '5432')
}

# IMDb chart URLs
MOVIE_CHART_URL = 'https://www.imdb.com/chart/top/'
TV_CHART_URL = 'https://www.imdb.com/chart/toptv/'

# Request headers to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_imdb_chart(url, limit=100):
    """
    Scrape IMDb chart page and extract title names and IMDb IDs
    
    Args:
        url: IMDb chart URL
        limit: Number of entries to extract (default 100)
    
    Returns:
        List of tuples: [(name, imdb_id), ...]
    """
    print(f"Scraping {url}...")
    
    try:
        response = requests.get(url, headers=HEADERS, verify=False, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all title entries (adjust selector based on current IMDb structure)
        entries = []
        
        # IMDb chart uses different selectors - trying multiple approaches
        title_columns = soup.find_all('td', class_='titleColumn')
        
        for idx, column in enumerate(title_columns[:limit]):
            if idx >= limit:
                break
                
            # Extract title name
            title_link = column.find('a')
            if not title_link:
                continue
                
            title_name = title_link.text.strip()
            
            # Extract IMDb ID from href (format: /title/tt1234567/)
            href = title_link.get('href', '')
            imdb_id = None
            
            if '/title/' in href:
                # Extract tt ID
                parts = href.split('/title/')
                if len(parts) > 1:
                    imdb_id = parts[1].split('/')[0]
            
            if title_name and imdb_id and imdb_id.startswith('tt'):
                entries.append((title_name, imdb_id))
        
        print(f"Successfully scraped {len(entries)} entries")
        return entries
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

def get_existing_imdb_ids(cursor):
    """
    Get all existing IMDb IDs from topic_sources table
    
    Args:
        cursor: Database cursor
    
    Returns:
        Set of existing IMDb IDs
    """
    cursor.execute("""
        SELECT source_id 
        FROM topic_sources 
        WHERE source_name = 'imdb' AND source_id_type = 'imdb_id'
    """)
    
    existing_ids = {row[0] for row in cursor.fetchall()}
    return existing_ids

def insert_entries(conn, entries, content_type):
    """
    Insert entries into database in batches
    
    Args:
        conn: Database connection
        entries: List of tuples [(name, imdb_id), ...]
        content_type: 'movie' or 'show'
    """
    cursor = conn.cursor()
    
    try:
        # Get existing IMDb IDs to avoid duplicates
        existing_ids = get_existing_imdb_ids(cursor)
        print(f"Found {len(existing_ids)} existing IMDb entries in database")
        
        # Filter out duplicates
        new_entries = [(name, imdb_id) for name, imdb_id in entries if imdb_id not in existing_ids]
        
        if not new_entries:
            print(f"No new {content_type}s to insert (all already exist)")
            return 0
        
        print(f"Inserting {len(new_entries)} new {content_type}s...")
        
        inserted_count = 0
        
        for name, imdb_id in new_entries:
            try:
                # Insert into primary_topics and get the generated ID
                cursor.execute("""
                    INSERT INTO primary_topics (type, name)
                    VALUES (%s, %s)
                    RETURNING primary_topic_id
                """, (content_type, name))
                
                primary_topic_id = cursor.fetchone()[0]
                
                # Insert into topic_sources
                cursor.execute("""
                    INSERT INTO topic_sources (primary_topic_id, source_id, source_name, source_id_type)
                    VALUES (%s, %s, %s, %s)
                """, (primary_topic_id, imdb_id, 'imdb', 'imdb_id'))
                
                inserted_count += 1
                
                # Commit in batches of 10
                if inserted_count % 10 == 0:
                    conn.commit()
                    print(f"  Committed {inserted_count} {content_type}s...")
                
            except Exception as e:
                print(f"Error inserting {name} ({imdb_id}): {str(e)}")
                conn.rollback()
                continue
        
        # Final commit for remaining entries
        conn.commit()
        print(f"Successfully inserted {inserted_count} {content_type}s")
        
        return inserted_count
        
    except Exception as e:
        print(f"Error during insertion: {str(e)}")
        conn.rollback()
        return 0
    finally:
        cursor.close()

def main():
    """
    Main execution function
    """
    print("=" * 60)
    print("IMDb Top 100 Movies & Shows Scraper")
    print("=" * 60)
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Step 1: Scrape top 100 movies
    movies = scrape_imdb_chart(MOVIE_CHART_URL, limit=100)
    time.sleep(2)  # Rate limiting
    
    # Step 2: Scrape top 100 TV shows
    shows = scrape_imdb_chart(TV_CHART_URL, limit=100)
    
    print("\n" + "=" * 60)
    print(f"Scraped {len(movies)} movies and {len(shows)} shows")
    print("=" * 60 + "\n")
    
    # Step 3: Connect to database
    try:
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("Database connection successful!\n")
        
        # Step 4: Insert movies
        print("Processing movies...")
        movies_inserted = insert_entries(conn, movies, 'movie')
        
        print("\nProcessing TV shows...")
        shows_inserted = insert_entries(conn, shows, 'show')
        
        # Close connection
        conn.close()
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total movies scraped: {len(movies)}")
        print(f"Total shows scraped: {len(shows)}")
        print(f"Movies inserted: {movies_inserted}")
        print(f"Shows inserted: {shows_inserted}")
        print(f"Total inserted: {movies_inserted + shows_inserted}")
        print("=" * 60)
        
    except psycopg2.Error as e:
        print(f"Database error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()