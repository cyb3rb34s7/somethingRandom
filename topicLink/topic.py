import requests
import os
import time
import json
import logging
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
import argparse
import sys

# Load environment variables
load_dotenv()

# API authorization and configuration
TMDB_BEARER_TOKEN = os.getenv('TMDB_BEARER_TOKEN')
TOPIC_INGESTION_API_URL = os.getenv('TOPIC_INGESTION_API_URL', 'https://dummy-api.com/api/topics/ingest')

# Database configuration for PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = 'x'  # Your database name
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_EXTERNAL_SCHEMA = 'bingeplus_external'  # Schema for source tables
DB_INTERNAL_SCHEMA = 'bingeplus_internal'  # Schema for destination table

class CastDataImporter:
    def __init__(self, tmdb_bearer_token=TMDB_BEARER_TOKEN, test_mode=False):
        self.tmdb_bearer_token = tmdb_bearer_token
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.topic_api_url = TOPIC_INGESTION_API_URL
        self.test_mode = test_mode
        self.headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}",
            "Content-Type": "application/json"
        }
        self.conn = None
        self.cursor = None
        self.setup_logging()
        
        # Statistics tracking
        self.stats = {
            'total_movies': 0,
            'successful_movies': 0,
            'failed_movies': 0,
            'total_cast_added': 0,
            'total_links_created': 0,
            'tmdb_api_errors': 0,
            'topic_api_errors': 0,
            'db_errors': 0,
            'start_time': None,
            'end_time': None
        }
        
    def setup_logging(self):
        """Setup detailed logging with separate files for success and errors"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        timestamp = datetime.now().strftime('%Y-%m-%d')
        
        # Setup loggers
        self.success_logger = logging.getLogger('success')
        self.error_logger = logging.getLogger('error')
        self.summary_logger = logging.getLogger('summary')
        
        # Clear any existing handlers
        for logger in [self.success_logger, self.error_logger, self.summary_logger]:
            logger.handlers.clear()
            logger.setLevel(logging.INFO)
        
        # Success logger
        success_handler = logging.FileHandler(f'logs/cast_import_success_{timestamp}.log')
        success_formatter = logging.Formatter('%(asctime)s - SUCCESS - %(message)s')
        success_handler.setFormatter(success_formatter)
        self.success_logger.addHandler(success_handler)
        
        # Error logger
        error_handler = logging.FileHandler(f'logs/cast_import_errors_{timestamp}.log')
        error_formatter = logging.Formatter('%(asctime)s - ERROR - %(message)s')
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
        
        # Summary logger
        summary_handler = logging.FileHandler(f'logs/cast_import_summary_{timestamp}.log')
        summary_formatter = logging.Formatter('%(asctime)s - SUMMARY - %(message)s')
        summary_handler.setFormatter(summary_formatter)
        self.summary_logger.addHandler(summary_handler)
        
        # Console logging
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add console handler to a main logger
        self.main_logger = logging.getLogger('main')
        self.main_logger.handlers.clear()
        self.main_logger.setLevel(logging.INFO)
        self.main_logger.addHandler(console_handler)
        
    def connect_to_db(self):
        """Connect to the PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            self.cursor = self.conn.cursor()
            self.conn.commit()
            return True
        except Exception as e:
            self.error_logger.error(f"Database connection failed: {str(e)}")
            return False
    
    def close_db_connection(self):
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def create_cast_table(self):
        """Create the cast table if it doesn't exist in the internal schema"""
        try:
            self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB_INTERNAL_SCHEMA}.cast_details (
                cast_id SERIAL PRIMARY KEY,
                primary_topic_id INTEGER,
                movie_show_name TEXT,
                name TEXT,
                character TEXT,
                tmdb_id INTEGER,
                imdb_id TEXT,
                gender INTEGER,
                birthday DATE,
                place_of_birth TEXT,
                biography TEXT,
                popularity REAL,
                profile_image TEXT,
                alternate_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            self.conn.commit()
            return True
        except Exception as e:
            self.error_logger.error(f"Failed to create cast table: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_movies_and_shows(self, specific_movie_id=None):
        """Get movies and shows from primary_topic table in external schema"""
        try:
            if specific_movie_id:
                # For testing - get specific movie
                self.cursor.execute(f'''
                SELECT pt.primary_topic_id, pt.name, ts.source_id, ts.source_name, ts.source_id_type
                FROM {DB_EXTERNAL_SCHEMA}.primary_topic pt
                JOIN {DB_EXTERNAL_SCHEMA}.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
                WHERE pt.type IN ('movie', 'show') AND pt.primary_topic_id = %s
                ''', (specific_movie_id,))
            else:
                # Get all movies and shows
                self.cursor.execute(f'''
                SELECT pt.primary_topic_id, pt.name, ts.source_id, ts.source_name, ts.source_id_type
                FROM {DB_EXTERNAL_SCHEMA}.primary_topic pt
                JOIN {DB_EXTERNAL_SCHEMA}.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
                WHERE pt.type IN ('movie', 'show')
                ORDER BY pt.primary_topic_id
                ''')
            return self.cursor.fetchall()
        except Exception as e:
            self.error_logger.error(f"Failed to fetch movies and shows: {str(e)}")
            return []
    
    def call_topic_ingestion_api(self, actor_data, retry_count=0):
        """Call the topic ingestion API to create/get actor topic"""
        try:
            payload = {
                "name": actor_data['name'],
                "topic_type": "actor",
                "source_id": str(actor_data['tmdb_id']),
                "source_name": "tmdb",
                "source_id_type": "tmdb_id"
            }
            
            if actor_data.get('imdb_id'):
                # If we have IMDb ID, use that as primary source
                payload.update({
                    "source_id": actor_data['imdb_id'],
                    "source_name": "imdb",
                    "source_id_type": "imdb_id"
                })
            
            self.main_logger.info(f"Calling topic API for actor: {actor_data['name']}")
            
            response = requests.post(
                self.topic_api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                topic_id = result.get('topic_id')
                if topic_id:
                    self.success_logger.info(f"Actor topic created/found - Name: {actor_data['name']}, Topic ID: {topic_id}")
                    return topic_id
                else:
                    raise ValueError("No topic_id in API response")
            else:
                raise requests.RequestException(f"API returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            if retry_count == 0:
                self.main_logger.warning(f"Topic API failed for {actor_data['name']}, retrying...")
                time.sleep(2)
                return self.call_topic_ingestion_api(actor_data, retry_count=1)
            else:
                self.error_logger.error(f"Topic API failed for {actor_data['name']} after retry: {str(e)}")
                self.stats['topic_api_errors'] += 1
                return None
    
    def fetch_cast_from_tmdb(self, tmdb_id, primary_topic_id, movie_show_name, cast_limit=2, retry_count=0):
        """Fetch cast details from TMDb"""
        try:
            # Get movie credits (cast and crew)
            endpoint = f"{self.tmdb_base_url}/movie/{tmdb_id}/credits"
            response = requests.get(endpoint, headers=self.headers, timeout=30)
            
            # If movie endpoint fails, try TV show endpoint
            if response.status_code != 200:
                endpoint = f"{self.tmdb_base_url}/tv/{tmdb_id}/credits"
                response = requests.get(endpoint, headers=self.headers, timeout=30)
            
            response.raise_for_status()
            credits_data = response.json()
            
            if 'cast' not in credits_data or not credits_data['cast']:
                self.main_logger.warning(f"No cast information found for TMDb ID: {tmdb_id}")
                return []
                
            # Process cast data (limit to top 2 cast members - lead actors)
            cast_details = []
            for actor in credits_data.get('cast', [])[:cast_limit]:
                # Get detailed person info for each cast member
                person_endpoint = f"{self.tmdb_base_url}/person/{actor['id']}"
                person_params = {"append_to_response": "external_ids,images"}
                person_response = requests.get(person_endpoint, headers=self.headers, params=person_params, timeout=30)
                
                if person_response.status_code != 200:
                    self.main_logger.warning(f"Failed to fetch details for actor {actor.get('name', 'Unknown')}")
                    continue
                    
                person_data = person_response.json()
                
                # Extract external IDs
                external_ids = person_data.get('external_ids', {})
                imdb_id = external_ids.get('imdb_id')
                
                # Get profile image and one alternate image
                profile_image = f"{self.image_base_url}{person_data.get('profile_path')}" if person_data.get('profile_path') else None
                alternate_image = None
                
                # Try to get one alternate image if available
                if 'profiles' in person_data.get('images', {}) and len(person_data['images']['profiles']) > 1:
                    alternate_image = f"{self.image_base_url}{person_data['images']['profiles'][1]['file_path']}"
                
                cast_member = {
                    "primary_topic_id": primary_topic_id,
                    "movie_show_name": movie_show_name,
                    "name": person_data.get('name', actor.get('name')),
                    "character": actor.get('character'),
                    "tmdb_id": actor.get('id'),
                    "imdb_id": imdb_id,
                    "gender": person_data.get('gender'),
                    "birthday": person_data.get('birthday'),
                    "place_of_birth": person_data.get('place_of_birth'),
                    "biography": person_data.get('biography'),
                    "popularity": person_data.get('popularity'),
                    "profile_image": profile_image,
                    "alternate_image": alternate_image
                }
                
                cast_details.append(cast_member)
                self.main_logger.info(f"Fetched cast member: {cast_member['name']} as {cast_member['character']}")
                
                # Respect API rate limits
                time.sleep(0.25)
                
            return cast_details
            
        except Exception as e:
            if retry_count == 0:
                self.main_logger.warning(f"TMDb API failed for movie {movie_show_name}, retrying...")
                time.sleep(2)
                return self.fetch_cast_from_tmdb(tmdb_id, primary_topic_id, movie_show_name, cast_limit, retry_count=1)
            else:
                self.error_logger.error(f"TMDb API failed for movie {movie_show_name} after retry: {str(e)}")
                self.stats['tmdb_api_errors'] += 1
                return []
    
    def fetch_cast_from_imdb_id(self, imdb_id, primary_topic_id, movie_show_name, cast_limit=2):
        """Convert IMDb ID to TMDb ID and fetch cast details"""
        try:
            # First find the TMDb ID using the IMDb ID
            find_endpoint = f"{self.tmdb_base_url}/find/{imdb_id}"
            params = {"external_source": "imdb_id"}
            response = requests.get(find_endpoint, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            find_data = response.json()
            
            # Check if we found a movie match
            movie_results = find_data.get('movie_results', [])
            tv_results = find_data.get('tv_results', [])
            
            if movie_results:
                tmdb_id = movie_results[0]['id']
            elif tv_results:
                tmdb_id = tv_results[0]['id']
            else:
                self.main_logger.warning(f"No movie/show found with IMDb ID: {imdb_id}")
                return []
                
            # Now use the TMDb ID to fetch cast details
            return self.fetch_cast_from_tmdb(tmdb_id, primary_topic_id, movie_show_name, cast_limit)
            
        except Exception as e:
            self.error_logger.error(f"Failed to convert IMDb ID {imdb_id} to TMDb ID: {str(e)}")
            return []
    
    def insert_cast_data(self, cast_details, retry_count=0):
        """Insert cast details into the internal schema table"""
        try:
            inserted_count = 0
            for cast_member in cast_details:
                birthday = cast_member['birthday']
                
                # Use ON CONFLICT to handle duplicates gracefully
                self.cursor.execute(f'''
                INSERT INTO {DB_INTERNAL_SCHEMA}.cast_details (
                    primary_topic_id, movie_show_name, name, character, tmdb_id, imdb_id,
                    gender, birthday, place_of_birth, biography,
                    popularity, profile_image, alternate_image
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (primary_topic_id, tmdb_id) DO NOTHING
                ''', (
                    cast_member['primary_topic_id'],
                    cast_member['movie_show_name'],
                    cast_member['name'],
                    cast_member['character'],
                    cast_member['tmdb_id'],
                    cast_member['imdb_id'],
                    cast_member['gender'],
                    birthday,
                    cast_member['place_of_birth'],
                    cast_member['biography'],
                    cast_member['popularity'],
                    cast_member['profile_image'],
                    cast_member['alternate_image']
                ))
                
                if self.cursor.rowcount > 0:
                    inserted_count += 1
                    self.success_logger.info(f"Inserted cast member: {cast_member['name']} for {cast_member['movie_show_name']}")
            
            self.conn.commit()
            return inserted_count
        except Exception as e:
            self.conn.rollback()
            if retry_count == 0:
                self.main_logger.warning(f"Database insert failed, retrying...")
                time.sleep(1)
                return self.insert_cast_data(cast_details, retry_count=1)
            else:
                self.error_logger.error(f"Database insert failed after retry: {str(e)}")
                self.stats['db_errors'] += 1
                return 0
    
    def insert_topic_links(self, primary_topic_id, actor_topic_ids, retry_count=0):
        """Insert topic-to-topic links"""
        try:
            inserted_count = 0
            for actor_topic_id in actor_topic_ids:
                if actor_topic_id:  # Only if we successfully got a topic ID
                    self.cursor.execute(f'''
                    INSERT INTO {DB_EXTERNAL_SCHEMA}.topic_to_topic_links (
                        primary_topic_id, linked_topic_id, link_type, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (primary_topic_id, linked_topic_id, link_type) DO NOTHING
                    ''', (primary_topic_id, actor_topic_id, 'cast'))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        self.success_logger.info(f"Created topic link: Movie {primary_topic_id} -> Actor {actor_topic_id}")
            
            self.conn.commit()
            return inserted_count
        except Exception as e:
            self.conn.rollback()
            if retry_count == 0:
                self.main_logger.warning(f"Topic links insert failed, retrying...")
                time.sleep(1)
                return self.insert_topic_links(primary_topic_id, actor_topic_ids, retry_count=1)
            else:
                self.error_logger.error(f"Topic links insert failed after retry: {str(e)}")
                self.stats['db_errors'] += 1
                return 0
    
    def process_single_movie(self, movie_data):
        """Process a single movie - core logic used by both test and full processing"""
        primary_topic_id, movie_show_name, source_id, source_name, source_id_type = movie_data
        
        self.main_logger.info(f"Processing: {movie_show_name} (ID: {primary_topic_id})")
        
        try:
            # Step 1: Fetch cast details from TMDb/IMDb
            cast_details = []
            if source_name.lower() == 'tmdb' and source_id_type.lower() == 'tmdb_id':
                cast_details = self.fetch_cast_from_tmdb(source_id, primary_topic_id, movie_show_name)
            elif source_name.lower() == 'imdb' and source_id_type.lower() == 'imdb_id':
                cast_details = self.fetch_cast_from_imdb_id(source_id, primary_topic_id, movie_show_name)
            
            if not cast_details:
                self.error_logger.error(f"No cast details found for {movie_show_name}")
                return False
            
            # Step 2: Insert cast data
            cast_inserted = self.insert_cast_data(cast_details)
            self.stats['total_cast_added'] += cast_inserted
            
            # Step 3: Create actor topics and get topic IDs
            actor_topic_ids = []
            for cast_member in cast_details:
                topic_id = self.call_topic_ingestion_api(cast_member)
                if topic_id:
                    actor_topic_ids.append(topic_id)
            
            # Step 4: Create topic links
            links_created = self.insert_topic_links(primary_topic_id, actor_topic_ids)
            self.stats['total_links_created'] += links_created
            
            self.success_logger.info(f"Successfully processed {movie_show_name}: {len(cast_details)} cast, {cast_inserted} inserted, {links_created} links created")
            return True
            
        except Exception as e:
            self.error_logger.error(f"Failed to process {movie_show_name}: {str(e)}")
            return False
    
    def test_single_movie(self, movie_id):
        """Test the complete workflow on a single movie"""
        self.main_logger.info(f"=== TESTING MODE: Processing single movie ID {movie_id} ===")
        
        if not self.connect_to_db():
            return False
            
        if not self.create_cast_table():
            self.close_db_connection()
            return False
            
        # Get the specific movie
        movies = self.get_movies_and_shows(specific_movie_id=movie_id)
        if not movies:
            self.main_logger.error(f"Movie with ID {movie_id} not found in database")
            self.close_db_connection()
            return False
        
        movie_data = movies[0]
        success = self.process_single_movie(movie_data)
        
        self.close_db_connection()
        
        # Print test results
        self.main_logger.info("=== TEST RESULTS ===")
        self.main_logger.info(f"Movie processing: {'SUCCESS' if success else 'FAILED'}")
        self.main_logger.info(f"Cast members added: {self.stats['total_cast_added']}")
        self.main_logger.info(f"Topic links created: {self.stats['total_links_created']}")
        self.main_logger.info(f"TMDb API errors: {self.stats['tmdb_api_errors']}")
        self.main_logger.info(f"Topic API errors: {self.stats['topic_api_errors']}")
        self.main_logger.info(f"Database errors: {self.stats['db_errors']}")
        
        return success
    
    def process_all_movies_shows(self):
        """Process all movies and shows to fetch and store cast data"""
        self.stats['start_time'] = datetime.now()
        self.main_logger.info("=== STARTING FULL PROCESSING ===")
        
        if not self.connect_to_db():
            return False
            
        if not self.create_cast_table():
            self.close_db_connection()
            return False
            
        movies_shows = self.get_movies_and_shows()
        self.stats['total_movies'] = len(movies_shows)
        
        self.main_logger.info(f"Found {self.stats['total_movies']} movies/shows to process")
        
        for index, movie_data in enumerate(movies_shows, 1):
            movie_show_name = movie_data[1]
            
            # Progress reporting
            progress_pct = (index / self.stats['total_movies']) * 100
            self.main_logger.info(f"Progress: {index}/{self.stats['total_movies']} ({progress_pct:.1f}%) - {movie_show_name}")
            
            success = self.process_single_movie(movie_data)
            
            if success:
                self.stats['successful_movies'] += 1
            else:
                self.stats['failed_movies'] += 1
            
            # Respect API rate limits between movies/shows
            time.sleep(1)
            
            # Progress checkpoint every 100 movies
            if index % 100 == 0:
                self.summary_logger.info(f"Checkpoint: Processed {index}/{self.stats['total_movies']} movies. Success: {self.stats['successful_movies']}, Failed: {self.stats['failed_movies']}")
        
        self.stats['end_time'] = datetime.now()
        self.close_db_connection()
        self.generate_final_report()
        return True
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        duration = self.stats['end_time'] - self.stats['start_time']
        success_rate = (self.stats['successful_movies'] / self.stats['total_movies'] * 100) if self.stats['total_movies'] > 0 else 0
        
        report = f"""
=== CAST IMPORT FINAL REPORT ===
Processing completed at: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
Total processing time: {duration}

OVERALL STATISTICS:
Total Movies/Shows: {self.stats['total_movies']}
✅ Successful: {self.stats['successful_movies']} ({success_rate:.1f}%)
❌ Failed: {self.stats['failed_movies']} ({100-success_rate:.1f}%)

DATA CREATED:
Total Cast Members Added: {self.stats['total_cast_added']}
Total Topic Links Created: {self.stats['total_links_created']}

ERROR BREAKDOWN:
TMDb API Errors: {self.stats['tmdb_api_errors']}
Topic Ingestion API Errors: {self.stats['topic_api_errors']}
Database Errors: {self.stats['db_errors']}

FILES GENERATED:
- logs/cast_import_success_{datetime.now().strftime('%Y-%m-%d')}.log
- logs/cast_import_errors_{datetime.now().strftime('%Y-%m-%d')}.log
- logs/cast_import_summary_{datetime.now().strftime('%Y-%m-%d')}.log
        """
        
        self.summary_logger.info(report)
        self.main_logger.info(report)

def main():
    parser = argparse.ArgumentParser(description='Cast Data Importer')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--movie-id', type=int, help='Movie ID to test (required with --test)')
    
    args = parser.parse_args()
    
    if args.test:
        if not args.movie_id:
            print("Error: --movie-id is required when using --test")
            sys.exit(1)
        
        importer = CastDataImporter(test_mode=True)
        success = importer.test_single_movie(args.movie_id)
        sys.exit(0 if success else 1)
    else:
        importer = CastDataImporter()
        success = importer.process_all_movies_shows()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()