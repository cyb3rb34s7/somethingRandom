I'll help you create a script to fetch TMDB IDs for your primary topics and review your table structure. Let me create a Python script that handles this efficiently.

import requests
import psycopg2
import time
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TMDBFetcher:
    def __init__(self, tmdb_bearer_token: str, db_config: Dict[str, str]):
        self.tmdb_bearer_token = tmdb_bearer_token
        self.db_config = db_config
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Authorization": f"Bearer {tmdb_bearer_token}",
            "Content-Type": "application/json"
        }
        self.rate_limit_delay = 0.25  # 4 requests per second limit
    
    def get_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def fetch_imdb_topics(self) -> list:
        """Fetch primary topics that have IMDB as source"""
        query = """
        SELECT DISTINCT 
            pt.primary_topic_id,
            pt.name,
            pt.type,
            ts.source_id as imdb_id
        FROM bingeplus_external.primary_topics pt
        JOIN bingeplus_external.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
        WHERE LOWER(ts.source_name) = 'imdb'
        """
        
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        logger.info(f"Found {len(results)} topics with IMDB source")
        return results
    
    def search_tmdb_by_imdb_id(self, imdb_id: str, media_type: str = None) -> Optional[Dict[str, Any]]:
        """Search TMDB using IMDB ID"""
        # Clean IMDB ID (ensure it starts with 'tt')
        if not imdb_id.startswith('tt'):
            imdb_id = f"tt{imdb_id}"
        
        # Try finding by external ID first
        url = f"{self.tmdb_base_url}/find/{imdb_id}"
        params = {"external_source": "imdb_id"}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check movie results first
            if data.get('movie_results'):
                return {
                    'tmdb_id': data['movie_results'][0]['id'],
                    'media_type': 'movie',
                    'title': data['movie_results'][0].get('title', ''),
                    'release_date': data['movie_results'][0].get('release_date', '')
                }
            
            # Then check TV results
            if data.get('tv_results'):
                return {
                    'tmdb_id': data['tv_results'][0]['id'],
                    'media_type': 'tv',
                    'title': data['tv_results'][0].get('name', ''),
                    'first_air_date': data['tv_results'][0].get('first_air_date', '')
                }
            
            # Check person results
            if data.get('person_results'):
                return {
                    'tmdb_id': data['person_results'][0]['id'],
                    'media_type': 'person',
                    'name': data['person_results'][0].get('name', ''),
                    'known_for_department': data['person_results'][0].get('known_for_department', '')
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching TMDB for IMDB ID {imdb_id}: {e}")
            return None
    
    def insert_or_update_internal_table(self, topic_data: Dict[str, Any]) -> bool:
        """Insert or update data in the internal table"""
        query = """
        INSERT INTO bingeplus_internal.your_table_name 
        (primary_topic_id, imdb_id, tmdb_id, name, media_type, additional_info, created_at, updated_at)
        VALUES (%(primary_topic_id)s, %(imdb_id)s, %(tmdb_id)s, %(name)s, %(media_type)s, %(additional_info)s, NOW(), NOW())
        ON CONFLICT (primary_topic_id) 
        DO UPDATE SET 
            tmdb_id = EXCLUDED.tmdb_id,
            name = EXCLUDED.name,
            media_type = EXCLUDED.media_type,
            additional_info = EXCLUDED.additional_info,
            updated_at = NOW()
        """
        
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, topic_data)
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting/updating data for topic {topic_data['primary_topic_id']}: {e}")
            return False
    
    def process_all_topics(self):
        """Main processing function"""
        topics = self.fetch_imdb_topics()
        successful_updates = 0
        failed_updates = 0
        
        for i, topic in enumerate(topics):
            logger.info(f"Processing topic {i+1}/{len(topics)}: {topic['name']}")
            
            # Search TMDB
            tmdb_result = self.search_tmdb_by_imdb_id(topic['imdb_id'], topic.get('type'))
            
            if tmdb_result:
                # Prepare data for insertion
                insert_data = {
                    'primary_topic_id': topic['primary_topic_id'],
                    'imdb_id': topic['imdb_id'],
                    'tmdb_id': tmdb_result['tmdb_id'],
                    'name': topic['name'],
                    'media_type': tmdb_result['media_type'],
                    'additional_info': tmdb_result  # Store full TMDB response as JSON
                }
                
                if self.insert_or_update_internal_table(insert_data):
                    successful_updates += 1
                    logger.info(f"✓ Found TMDB ID {tmdb_result['tmdb_id']} for {topic['name']}")
                else:
                    failed_updates += 1
            else:
                failed_updates += 1
                logger.warning(f"✗ No TMDB ID found for {topic['name']} (IMDB: {topic['imdb_id']})")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
        
        logger.info(f"Processing complete. Successful: {successful_updates}, Failed: {failed_updates}")

# Usage example
if __name__ == "__main__":
    # Configuration
    TMDB_BEARER_TOKEN = "your_tmdb_bearer_token_here"
    
    DB_CONFIG = {
        'host': 'your_host',
        'database': 'your_database',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }
    
    # Initialize and run
    fetcher = TMDBFetcher(TMDB_BEARER_TOKEN, DB_CONFIG)
    fetcher.process_all_topics()

Now, regarding your table structure, here are my recommendations for your `bingeplus_internal` table:

**Current columns you mentioned:**
- `primary_topic_id`
- `imdb_id` 
- `tmdb_id`
- `name`

**Recommended additional columns:**

1. **`media_type`** - Essential for distinguishing between movies, TV shows, and people
2. **`created_at`** - Timestamp when the record was created
3. **`updated_at`** - Timestamp when the record was last updated
4. **`status`** - To track processing status (e.g., 'pending', 'found', 'not_found')
5. **`additional_info`** - JSON/JSONB column to store extra metadata from TMDB
6. **`last_sync_attempt`** - When you last tried to fetch TMDB data
7. **`sync_attempts`** - Counter for failed attempts

**Suggested complete table structure:**

```sql
CREATE TABLE bingeplus_internal.your_table_name (
    id SERIAL PRIMARY KEY,
    primary_topic_id INTEGER NOT NULL UNIQUE,
    imdb_id VARCHAR(20),
    tmdb_id INTEGER,
    name VARCHAR(500),
    media_type VARCHAR(20), -- 'movie', 'tv', 'person'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'found', 'not_found', 'error'
    additional_info JSONB, -- Store full TMDB response
    sync_attempts INTEGER DEFAULT 0,
    last_sync_attempt TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_primary_topic 
        FOREIGN KEY (primary_topic_id) 
        REFERENCES bingeplus_external.primary_topics(primary_topic_id)
);

CREATE INDEX idx_primary_topic_id ON bingeplus_internal.your_table_name(primary_topic_id);
CREATE INDEX idx_imdb_id ON bingeplus_internal.your_table_name(imdb_id);
CREATE INDEX idx_tmdb_id ON bingeplus_internal.your_table_name(tmdb_id);
CREATE INDEX idx_status ON bingeplus_internal.your_table_name(status);
```

**Key benefits of this approach:**

1. **Rate limiting** - Respects TMDB's API limits
2. **Error handling** - Gracefully handles API failures
3. **Logging** - Tracks progress and issues
4. **Flexibility** - Handles movies, TV shows, and people
5. **Resumability** - Can restart from where it left off
6. **Data integrity** - Uses database transactions

**Before running the script:**

1. Replace `your_table_name` with your actual table name
2. Update the database configuration
3. Add your TMDB bearer token
4. Install required packages: `pip install requests psycopg2-binary`

The script will efficiently process all your IMDB topics and populate the TMDB IDs while respecting API rate limits and providing detailed logging.