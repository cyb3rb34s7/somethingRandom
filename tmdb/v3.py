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
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import sys

@dataclass
class ProcessingStats:
    # Overall stats
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    
    # Detailed insertion counts
    genres_updated: int = 0
    descriptions_inserted: int = 0
    actors_inserted: int = 0
    directors_inserted: int = 0
    
    # API stats
    tmdb_direct_calls: int = 0
    imdb_conversions: int = 0
    name_searches: int = 0
    api_failures: int = 0
    
    # Timing
    start_time: datetime = None
    end_time: datetime = None
    
    # Failed items details
    failed_items_details: List[Dict] = field(default_factory=list)

@dataclass
class MovieShow:
    primary_topic_id: int
    name: str
    type: str
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    source_name: Optional[str] = None

class LogManager:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.log_dir = f"logs/{run_id}"
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging directories and files"""
        # Create log directory
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup different loggers
        self.setup_logger('processing', 'processing.log', logging.INFO)
        self.setup_logger('api', 'api_calls.log', logging.INFO)
        self.setup_logger('performance', 'performance.log', logging.INFO)
        
        # Create symlink to latest run
        latest_link = "logs/latest"
        if os.path.islink(latest_link):
            os.unlink(latest_link)
        os.symlink(self.run_id, latest_link)
    
    def setup_logger(self, name: str, filename: str, level: int):
        """Setup individual logger"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(f"{self.log_dir}/{filename}")
        file_handler.setLevel(level)
        
        # Console handler for main processing log
        if name == 'processing':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File formatter
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    def write_statistics(self, stats: ProcessingStats):
        """Write final statistics report"""
        duration = stats.end_time - stats.start_time if stats.start_time and stats.end_time else None
        duration_str = str(duration).split('.')[0] if duration else "Unknown"
        
        success_rate = (stats.successful_items / stats.total_items * 100) if stats.total_items > 0 else 0
        
        stats_content = f"""=== MOVIE ENRICHMENT STATISTICS ===
Run ID: {self.run_id}
Start Time: {stats.start_time.strftime('%Y-%m-%d %H:%M:%S') if stats.start_time else 'Unknown'}
End Time: {stats.end_time.strftime('%Y-%m-%d %H:%M:%S') if stats.end_time else 'Unknown'}
Duration: {duration_str}

OVERALL RESULTS:
Total Items: {stats.total_items}
Successful: {stats.successful_items} ({success_rate:.1f}%)
Failed: {stats.failed_items} ({100-success_rate:.1f}%)

INSERTIONS:
Descriptions: {stats.descriptions_inserted}
Actors: {stats.actors_inserted} (avg {stats.actors_inserted/stats.successful_items:.1f} per item)
Directors: {stats.directors_inserted}
Genres Updated: {stats.genres_updated}

API USAGE:
Direct TMDB Calls: {stats.tmdb_direct_calls}
IMDB→TMDB Conversions: {stats.imdb_conversions}
Name Searches: {stats.name_searches}
API Failures: {stats.api_failures}
"""
        
        # Add source breakdown if we have details
        if stats.failed_items_details:
            source_stats = {}
            for item in stats.failed_items_details:
                source = item.get('source_name', 'unknown')
                if source not in source_stats:
                    source_stats[source] = {'total': 0, 'failed': 0}
                source_stats[source]['total'] += 1
                source_stats[source]['failed'] += 1
            
            stats_content += "\nSOURCE BREAKDOWN:\n"
            for source, data in source_stats.items():
                success = data['total'] - data['failed']
                success_rate = (success / data['total'] * 100) if data['total'] > 0 else 0
                stats_content += f"{source}: {success}/{data['total']} ({success_rate:.1f}% success)\n"
        
        with open(f"{self.log_dir}/statistics.log", 'w') as f:
            f.write(stats_content)
    
    def write_failed_items(self, failed_items: List[Dict]):
        """Write failed items report"""
        if not failed_items:
            return
        
        content = "FAILED ITEMS REPORT\n===================\n\n"
        
        for item in failed_items:
            content += f"ID: {item['primary_topic_id']} | Name: \"{item['name']}\" | Type: {item['type']} | Source: {item['source_name']}\n"
            content += f"Error: {item['error_message']}\n"
            content += f"Timestamp: {item['timestamp']}\n"
            content += "---\n\n"
        
        with open(f"{self.log_dir}/failed_items.log", 'w') as f:
            f.write(content)

class TMDBClient:
    def __init__(self, bearer_token: str, log_manager: LogManager):
        self.bearer_token = bearer_token
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.api_logger = logging.getLogger('api')
        self.log_manager = log_manager
    
    def find_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Find TMDB data using IMDB ID"""
        try:
            if not imdb_id.startswith('tt'):
                imdb_id = f"tt{imdb_id}"
            
            url = f"{self.base_url}/find/{imdb_id}"
            params = {"external_source": "imdb_id"}
            
            self.api_logger.info(f"Converting IMDB ID {imdb_id} to TMDB ID")
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('movie_results'):
                    result = {'type': 'movie', 'id': data['movie_results'][0]['id']}
                    self.api_logger.info(f"Found TMDB movie ID {result['id']} for IMDB {imdb_id}")
                    return result
                elif data.get('tv_results'):
                    result = {'type': 'tv', 'id': data['tv_results'][0]['id']}
                    self.api_logger.info(f"Found TMDB TV ID {result['id']} for IMDB {imdb_id}")
                    return result
                else:
                    self.api_logger.warning(f"No TMDB match found for IMDB ID: {imdb_id}")
                    return None
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                self.api_logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.find_by_imdb_id(imdb_id)
            else:
                self.api_logger.error(f"Failed to find IMDB {imdb_id}: {response.status_code}")
                return None
        except Exception as e:
            self.api_logger.error(f"Error finding IMDB {imdb_id}: {str(e)}")
            return None
    
    def search_by_name_and_type(self, name: str, media_type: str) -> Optional[Dict]:
        """Search TMDB by name and type, return first result"""
        try:
            if media_type.lower() == 'movie':
                endpoint = 'search/movie'
            else:
                endpoint = 'search/tv'
            
            url = f"{self.base_url}/{endpoint}"
            params = {
                "query": name,
                "include_adult": "false",
                "language": "en-US",
                "page": 1
            }
            
            self.api_logger.info(f"Searching TMDB for '{name}' (type: {media_type})")
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    first_result = results[0]
                    result = {
                        'type': 'movie' if media_type.lower() == 'movie' else 'tv',
                        'id': first_result['id']
                    }
                    self.api_logger.info(f"Found TMDB ID {result['id']} for '{name}'")
                    return result
                else:
                    self.api_logger.warning(f"No TMDB search results for: {name} ({media_type})")
                    return None
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                self.api_logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.search_by_name_and_type(name, media_type)
            else:
                self.api_logger.error(f"Failed to search for {name}: {response.status_code}")
                return None
        except Exception as e:
            self.api_logger.error(f"Error searching for {name}: {str(e)}")
            return None
    
    def get_movie_details(self, tmdb_id: str) -> Optional[Dict]:
        """Fetch movie details from TMDB"""
        try:
            url = f"{self.base_url}/movie/{tmdb_id}"
            params = {"append_to_response": "credits"}
            
            self.api_logger.info(f"Fetching movie details for TMDB ID {tmdb_id}")
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                self.api_logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.get_movie_details(tmdb_id)
            else:
                self.api_logger.error(f"Failed to fetch movie {tmdb_id}: {response.status_code}")
                return None
        except Exception as e:
            self.api_logger.error(f"Error fetching movie {tmdb_id}: {str(e)}")
            return None
    
    def get_tv_details(self, tmdb_id: str) -> Optional[Dict]:
        """Fetch TV show details from TMDB"""
        try:
            url = f"{self.base_url}/tv/{tmdb_id}"
            params = {"append_to_response": "credits"}
            
            self.api_logger.info(f"Fetching TV details for TMDB ID {tmdb_id}")
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                self.api_logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self.get_tv_details(tmdb_id)
            else:
                self.api_logger.error(f"Failed to fetch TV show {tmdb_id}: {response.status_code}")
                return None
        except Exception as e:
            self.api_logger.error(f"Error fetching TV show {tmdb_id}: {str(e)}")
            return None

class DatabaseManager:
    def __init__(self, connection_params: Dict[str, str], log_manager: LogManager):
        self.connection_params = connection_params
        self.conn = None
        self.cursor = None
        self.performance_logger = logging.getLogger('performance')
        self.log_manager = log_manager
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor()
            self.performance_logger.info("Database connection established")
        except Exception as e:
            self.performance_logger.error(f"Database connection failed: {str(e)}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.performance_logger.info("Database connection closed")
    
    def create_savepoint(self, savepoint_name: str):
        """Create a savepoint"""
        try:
            self.cursor.execute(f"SAVEPOINT {savepoint_name}")
        except Exception as e:
            self.performance_logger.error(f"Error creating savepoint {savepoint_name}: {str(e)}")
            raise
    
    def rollback_to_savepoint(self, savepoint_name: str):
        """Rollback to a savepoint"""
        try:
            self.cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        except Exception as e:
            self.performance_logger.error(f"Error rolling back to savepoint {savepoint_name}: {str(e)}")
            raise
    
    def release_savepoint(self, savepoint_name: str):
        """Release a savepoint"""
        try:
            self.cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        except Exception as e:
            self.performance_logger.error(f"Error releasing savepoint {savepoint_name}: {str(e)}")
            raise
    
    def get_unprocessed_items(self, test_ids: Optional[List[int]] = None) -> List[MovieShow]:
        """Get movies/shows that haven't been processed yet"""
        base_query = """
        SELECT DISTINCT 
            pt.primary_topic_id,
            pt.name,
            pt.type,
            ts.source_id,
            ts.source_name
        FROM bingeplus_external.primary_topics pt
        JOIN bingeplus_external.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
        WHERE pt.primary_topic_id NOT IN (
            SELECT DISTINCT primary_topic_id 
            FROM bingeplus_external.topic_people 
            WHERE record_provider = 'tmdb'
        )
        AND pt.primary_topic_id NOT IN (
            SELECT DISTINCT primary_topic_id 
            FROM bingeplus_external.topic_descriptions 
            WHERE record_provider = 'tmdb'
        )
        """
        
        if test_ids:
            id_list = ','.join(map(str, test_ids))
            query = f"{base_query} AND pt.primary_topic_id IN ({id_list})"
            self.performance_logger.info(f"TESTING MODE: Processing only IDs: {test_ids}")
        else:
            query = f"{base_query} ORDER BY pt.created_at DESC"
        
        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            items = []
            for row in results:
                item = MovieShow(
                    primary_topic_id=row[0],
                    name=row[1],
                    type=row[2],
                    source_name=row[4]
                )
                
                if row[4] == 'tmdb':
                    item.tmdb_id = row[3]
                elif row[4] == 'imdb':
                    item.imdb_id = row[3]
                
                items.append(item)
            
            self.performance_logger.info(f"Found {len(items)} unprocessed items")
            return items
            
        except Exception as e:
            self.performance_logger.error(f"Error fetching unprocessed items: {str(e)}")
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
        except Exception as e:
            self.performance_logger.error(f"Error updating genres for {primary_topic_id}: {str(e)}")
            raise
    
    def insert_person(self, primary_topic_id: int, person_name: str, role: str, 
                     character_name: str, order_rank: int):
        """Insert person into topic_people table"""
        try:
            query = """
            INSERT INTO bingeplus_external.topic_people 
            (primary_topic_id, person_name, role, character_name, order_rank, record_provider, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'tmdb', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            self.cursor.execute(query, (
                primary_topic_id, person_name, role, character_name, order_rank
            ))
        except Exception as e:
            self.performance_logger.error(f"Error inserting person: {str(e)}")
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
            """
            self.cursor.execute(query, (
                primary_topic_id, description, lang_code, desc_type, desc_size
            ))
        except Exception as e:
            self.performance_logger.error(f"Error inserting description: {str(e)}")
            raise
    
    def commit(self):
        """Commit transaction"""
        try:
            self.conn.commit()
        except Exception as e:
            self.performance_logger.error(f"Error committing transaction: {str(e)}")
            self.conn.rollback()
            raise

class MovieShowEnricher:
    def __init__(self, db_manager: DatabaseManager, tmdb_client: TMDBClient, log_manager: LogManager):
        self.db_manager = db_manager
        self.tmdb_client = tmdb_client
        self.log_manager = log_manager
        self.processing_logger = logging.getLogger('processing')
        self.stats = ProcessingStats()
    
    def process_item(self, item: MovieShow) -> bool:
        """Process a single movie/show item"""
        try:
            self.processing_logger.info(f"Processing {item.type}: {item.name} (ID: {item.primary_topic_id}, Source: {item.source_name})")
            
            tmdb_id = None
            
            # Handle different source types
            if item.source_name == 'tmdb' and item.tmdb_id:
                tmdb_id = item.tmdb_id
                self.stats.tmdb_direct_calls += 1
                self.processing_logger.info(f"Using direct TMDB ID: {tmdb_id}")
                
            elif item.source_name == 'imdb' and item.imdb_id:
                self.processing_logger.info(f"Converting IMDB ID {item.imdb_id} to TMDB ID")
                find_result = self.tmdb_client.find_by_imdb_id(item.imdb_id)
                if find_result:
                    tmdb_id = str(find_result['id'])
                    self.stats.imdb_conversions += 1
                    expected_type = 'movie' if item.type.lower() == 'movie' else 'tv'
                    if find_result['type'] != expected_type:
                        self.processing_logger.warning(f"Type mismatch for {item.name}: expected {expected_type}, got {find_result['type']}")
                else:
                    self.stats.api_failures += 1
                    raise Exception(f"Could not find TMDB ID for IMDB ID: {item.imdb_id}")
                    
            else:
                self.processing_logger.info(f"Searching TMDB by name for '{item.name}' (type: {item.type})")
                search_result = self.tmdb_client.search_by_name_and_type(item.name, item.type)
                if search_result:
                    tmdb_id = str(search_result['id'])
                    self.stats.name_searches += 1
                    self.processing_logger.info(f"Found TMDB ID {tmdb_id} for '{item.name}'")
                else:
                    self.stats.api_failures += 1
                    raise Exception(f"Could not find TMDB match for: {item.name} ({item.type})")
            
            if not tmdb_id:
                raise Exception(f"No TMDB ID available for {item.name}")
            
            # Fetch data from TMDB
            if item.type.lower() == 'movie':
                data = self.tmdb_client.get_movie_details(tmdb_id)
            else:
                data = self.tmdb_client.get_tv_details(tmdb_id)
            
            if not data:
                self.stats.api_failures += 1
                raise Exception(f"No data found for {item.name}")
            
            # Process genres
            genres = [genre['name'] for genre in data.get('genres', [])]
            if genres:
                self.db_manager.update_genres(item.primary_topic_id, genres)
                self.stats.genres_updated += 1
            
            # Process description
            overview = data.get('overview', '').strip()
            if overview:
                self.db_manager.insert_description(item.primary_topic_id, overview)
                self.stats.descriptions_inserted += 1
            
            # Process cast and crew
            credits = data.get('credits', {})
            
            # Process actors (top 5)
            cast = credits.get('cast', [])[:5]
            for idx, actor in enumerate(cast, 1):
                self.db_manager.insert_person(
                    primary_topic_id=item.primary_topic_id,
                    person_name=actor.get('name', ''),
                    role='Actor',
                    character_name=actor.get('character', ''),
                    order_rank=idx
                )
                self.stats.actors_inserted += 1
            
            # Process directors
            crew = credits.get('crew', [])
            directors = [person for person in crew if person.get('job') == 'Director']
            for idx, director in enumerate(directors, 1):
                self.db_manager.insert_person(
                    primary_topic_id=item.primary_topic_id,
                    person_name=director.get('name', ''),
                    role='Director',
                    character_name='',
                    order_rank=idx
                )
                self.stats.directors_inserted += 1
            
            self.processing_logger.info(f"Successfully processed {item.name}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.processing_logger.error(f"Error processing {item.name}: {error_msg}")
            
            # Add to failed items details
            self.stats.failed_items_details.append({
                'primary_topic_id': item.primary_topic_id,
                'name': item.name,
                'type': item.type,
                'source_name': item.source_name,
                'error_message': error_msg,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return False
    
    def run_enrichment(self, batch_size: int = 50, test_ids: Optional[List[int]] = None):
        """Run the enrichment process"""
        try:
            self.stats.start_time = datetime.now()
            self.processing_logger.info("Starting enrichment process")
            
            self.db_manager.connect()
            
            # Get unprocessed items
            items = self.db_manager.get_unprocessed_items(test_ids)
            self.stats.total_items = len(items)
            
            if not items:
                self.processing_logger.info("No items to process")
                return
            
            # Process in batches
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(items) + batch_size - 1) // batch_size
                
                self.processing_logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
                
                for item in batch:
                    savepoint_name = f"item_{item.primary_topic_id}"
                    
                    try:
                        # Create savepoint before processing each item
                        self.db_manager.create_savepoint(savepoint_name)
                        
                        if self.process_item(item):
                            # Success - release savepoint
                            self.db_manager.release_savepoint(savepoint_name)
                            self.stats.successful_items += 1
                        else:
                            # Failure - rollback to savepoint
                            self.db_manager.rollback_to_savepoint(savepoint_name)
                            self.stats.failed_items += 1
                        
                        # Rate limiting
                        time.sleep(0.25)
                        
                    except Exception as e:
                        # Exception - rollback to savepoint
                        try:
                            self.db_manager.rollback_to_savepoint(savepoint_name)
                        except:
                            pass
                        self.stats.failed_items += 1
                        self.processing_logger.error(f"Failed to process item {item.primary_topic_id}: {str(e)}")
                
                # Commit batch
                self.db_manager.commit()
                self.processing_logger.info(f"Committed batch {batch_num}")
                
                # Brief pause between batches
                time.sleep(1)
            
            self.stats.end_time = datetime.now()
            
            self.processing_logger.info(f"Enrichment completed. Successful: {self.stats.successful_items}, Failed: {self.stats.failed_items}")
            
            # Write final reports
            self.log_manager.write_statistics(self.stats)
            self.log_manager.write_failed_items(self.stats.failed_items_details)
            
        except Exception as e:
            self.processing_logger.error(f"Error in enrichment process: {str(e)}")
        finally:
            self.db_manager.disconnect()

def main():
    """Main function"""
    # Create run ID with timestamp
    run_id = f"run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    
    # Initialize log manager
    log_manager = LogManager(run_id)
    
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
        print("TMDB Bearer token not configured")
        return
    
    # Initialize components
    db_manager = DatabaseManager(DB_CONFIG, log_manager)
    tmdb_client = TMDBClient(TMDB_TOKEN, log_manager)
    enricher = MovieShowEnricher(db_manager, tmdb_client, log_manager)
    
    # TESTING: Uncomment and add specific IDs to test with limited data
    # test_ids = [123, 456, 789]  # Replace with actual primary_topic_ids
    test_ids = None  # Set to None for production
    
    # Run enrichment
    processing_logger = logging.getLogger('processing')
    if test_ids:
        processing_logger.info(f"Starting TEST enrichment process for IDs: {test_ids}")
    else:
        processing_logger.info("Starting daily enrichment process")
    
    enricher.run_enrichment(test_ids=test_ids)
    
    processing_logger.info(f"Check logs in: logs/{run_id}/")

if __name__ == "__main__":
    main()