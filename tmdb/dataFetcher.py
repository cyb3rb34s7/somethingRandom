#!/usr/bin/env python3
"""
Daily Movie/Show Data Enrichment Script
Fetches and updates movie/show data from TMDB API
"""

import psycopg2
import requests
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_enrichment.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class MovieShow:
    primary_topic_id: int
    name: str
    type: str
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None

class TMDBClient:
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_movie_details(self, tmdb_id: str) -> Optional[Dict]:
        """Fetch movie details from TMDB"""
        try:
            url = f"{self.base_url}/movie/{tmdb_id}"
            params = {"append_to_response": "credits"}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit handling
                retry_after = int(response.headers.get('Retry-After', 1))
                logging.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.get_movie_details(tmdb_id)
            else:
                logging.error(f"Failed to fetch movie {tmdb_id}: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error fetching movie {tmdb_id}: {str(e)}")
            return None
    
    def get_tv_details(self, tmdb_id: str) -> Optional[Dict]:
        """Fetch TV show details from TMDB"""
        try:
            url = f"{self.base_url}/tv/{tmdb_id}"
            params = {"append_to_response": "credits"}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                logging.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.get_tv_details(tmdb_id)
            else:
                logging.error(f"Failed to fetch TV show {tmdb_id}: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error fetching TV show {tmdb_id}: {str(e)}")
            return None

class DatabaseManager:
    def __init__(self, connection_params: Dict[str, str]):
        self.connection_params = connection_params
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor()
            logging.info("Database connection established")
        except Exception as e:
            logging.error(f"Database connection failed: {str(e)}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logging.info("Database connection closed")
    
    def get_unprocessed_items(self) -> List[MovieShow]:
        """Get movies/shows that haven't been processed yet"""
        query = """
        SELECT DISTINCT 
            pt.primary_topic_id,
            pt.name,
            pt.type,
            ts.source_id,
            ts.source_name
        FROM bingeplus_external.primary_topics pt
        JOIN bingeplus_external.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
        WHERE ts.source_name = 'tmdb'
        AND pt.primary_topic_id NOT IN (
            SELECT DISTINCT primary_topic_id 
            FROM bingeplus_external.topic_people 
            WHERE record_provider = 'tmdb'
        )
        AND pt.primary_topic_id NOT IN (
            SELECT DISTINCT primary_topic_id 
            FROM bingeplus_external.topic_descriptions 
            WHERE record_provider = 'tmdb'
        )
        ORDER BY pt.created_at DESC
        """
        
        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            items = []
            for row in results:
                item = MovieShow(
                    primary_topic_id=row[0],
                    name=row[1],
                    type=row[2],
                    tmdb_id=row[3] if row[4] == 'tmdb' else None
                )
                items.append(item)
            
            logging.info(f"Found {len(items)} unprocessed items")
            return items
            
        except Exception as e:
            logging.error(f"Error fetching unprocessed items: {str(e)}")
            return []
    
    def update_genres(self, primary_topic_id: int, genres: List[str]):
        """Update genres in primary_topics table"""
        try:
            query = """
            UPDATE bingeplus_external.primary_topics 
            SET genres = %s, updated_at = CURRENT_TIMESTAMP
            WHERE primary_topic_id = %s
            """
            self.cursor.execute(query, (genres, primary_topic_id))
            logging.debug(f"Updated genres for topic {primary_topic_id}")
        except Exception as e:
            logging.error(f"Error updating genres for {primary_topic_id}: {str(e)}")
            raise
    
    def insert_person(self, primary_topic_id: int, person_name: str, role: str, 
                     character_name: str, order_rank: int):
        """Insert person into topic_people table"""
        try:
            query = """
            INSERT INTO bingeplus_external.topic_people 
            (primary_topic_id, person_name, role, character_name, order_rank, record_provider, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'tmdb', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (primary_topic_id, person_name, role, order_rank) DO NOTHING
            """
            self.cursor.execute(query, (
                primary_topic_id, person_name, role, character_name, order_rank
            ))
            logging.debug(f"Inserted {role} {person_name} for topic {primary_topic_id}")
        except Exception as e:
            logging.error(f"Error inserting person: {str(e)}")
            raise
    
    def insert_description(self, primary_topic_id: int, description: str, 
                          lang_code: str = 'en', desc_type: str = 'main'):
        """Insert description into topic_descriptions table"""
        try:
            desc_size = len(description)
            query = """
            INSERT INTO bingeplus_external.topic_descriptions 
            (primary_topic_id, description, lang_code, desc_type, desc_size, record_provider, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'tmdb', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (primary_topic_id, desc_type, lang_code) DO UPDATE SET
                description = EXCLUDED.description,
                desc_size = EXCLUDED.desc_size,
                updated_at = CURRENT_TIMESTAMP
            """
            self.cursor.execute(query, (
                primary_topic_id, description, lang_code, desc_type, desc_size
            ))
            logging.debug(f"Inserted description for topic {primary_topic_id}")
        except Exception as e:
            logging.error(f"Error inserting description: {str(e)}")
            raise
    
    def commit(self):
        """Commit transaction"""
        try:
            self.conn.commit()
        except Exception as e:
            logging.error(f"Error committing transaction: {str(e)}")
            self.conn.rollback()
            raise

class MovieShowEnricher:
    def __init__(self, db_manager: DatabaseManager, tmdb_client: TMDBClient):
        self.db_manager = db_manager
        self.tmdb_client = tmdb_client
    
    def process_item(self, item: MovieShow) -> bool:
        """Process a single movie/show item"""
        try:
            logging.info(f"Processing {item.type}: {item.name} (ID: {item.primary_topic_id})")
            
            # Fetch data from TMDB
            if item.type.lower() == 'movie':
                data = self.tmdb_client.get_movie_details(item.tmdb_id)
            else:  # show/tv
                data = self.tmdb_client.get_tv_details(item.tmdb_id)
            
            if not data:
                logging.warning(f"No data found for {item.name}")
                return False
            
            # Process genres
            genres = [genre['name'] for genre in data.get('genres', [])]
            if genres:
                self.db_manager.update_genres(item.primary_topic_id, genres)
            
            # Process description
            overview = data.get('overview', '').strip()
            if overview:
                self.db_manager.insert_description(item.primary_topic_id, overview)
            
            # Process cast and crew
            credits = data.get('credits', {})
            
            # Process actors (top 10)
            cast = credits.get('cast', [])[:10]  # Limit to top 10 actors
            for idx, actor in enumerate(cast, 1):
                self.db_manager.insert_person(
                    primary_topic_id=item.primary_topic_id,
                    person_name=actor.get('name', ''),
                    role='Actor',
                    character_name=actor.get('character', ''),
                    order_rank=idx
                )
            
            # Process directors
            crew = credits.get('crew', [])
            directors = [person for person in crew if person.get('job') == 'Director']
            for idx, director in enumerate(directors, 1):
                self.db_manager.insert_person(
                    primary_topic_id=item.primary_topic_id,
                    person_name=director.get('name', ''),
                    role='Director',
                    character_name='',  # Directors don't have character names
                    order_rank=idx
                )
            
            logging.info(f"Successfully processed {item.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error processing {item.name}: {str(e)}")
            return False
    
    def run_enrichment(self, batch_size: int = 50):
        """Run the enrichment process"""
        try:
            self.db_manager.connect()
            
            # Get unprocessed items
            items = self.db_manager.get_unprocessed_items()
            
            if not items:
                logging.info("No items to process")
                return
            
            successful = 0
            failed = 0
            
            # Process in batches
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                logging.info(f"Processing batch {i//batch_size + 1} ({len(batch)} items)")
                
                for item in batch:
                    try:
                        if self.process_item(item):
                            successful += 1
                        else:
                            failed += 1
                        
                        # Rate limiting - TMDB allows 50 requests per second
                        time.sleep(0.25)  # 4 requests per second to be safe
                        
                    except Exception as e:
                        logging.error(f"Failed to process item {item.primary_topic_id}: {str(e)}")
                        failed += 1
                
                # Commit batch
                self.db_manager.commit()
                logging.info(f"Committed batch {i//batch_size + 1}")
                
                # Brief pause between batches
                time.sleep(1)
            
            logging.info(f"Enrichment completed. Successful: {successful}, Failed: {failed}")
            
        except Exception as e:
            logging.error(f"Error in enrichment process: {str(e)}")
        finally:
            self.db_manager.disconnect()

def main():
    """Main function"""
    # Configuration
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'your_database'),
        'user': os.getenv('DB_USER', 'your_user'),
        'password': os.getenv('DB_PASSWORD', 'your_password'),
        'port': os.getenv('DB_PORT', '5432')
    }
    
    TMDB_TOKEN = os.getenv('TMDB_BEARER_TOKEN', 'your_tmdb_bearer_token')
    
    if not TMDB_TOKEN or TMDB_TOKEN == 'your_tmdb_bearer_token':
        logging.error("TMDB Bearer token not configured")
        return
    
    # Initialize components
    db_manager = DatabaseManager(DB_CONFIG)
    tmdb_client = TMDBClient(TMDB_TOKEN)
    enricher = MovieShowEnricher(db_manager, tmdb_client)
    
    # Run enrichment
    start_time = datetime.now()
    logging.info("Starting daily enrichment process")
    
    enricher.run_enrichment()
    
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Enrichment process completed in {duration}")

if __name__ == "__main__":
    main()