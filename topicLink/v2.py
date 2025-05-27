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
import urllib3

# Disable SSL warnings for dev environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# API authorization and configuration
TMDB_BEARER_TOKEN = os.getenv('TMDB_BEARER_TOKEN')
TOPIC_INGESTION_API_URL = os.getenv('TOPIC_INGESTION_API_URL', 'https://dummy-api.com/api/topics/ingest')

# Database configuration for PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = 'bingeplus'  # Your database name
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
        
        # Enhanced statistics tracking
        self.stats = {
            'total_movies': 0,
            'successful_movies': 0,
            'partially_successful_movies': 0,
            'failed_movies': 0,
            'total_cast_fetched': 0,
            'total_cast_inserted': 0,
            'total_topics_created': 0,
            'total_links_created': 0,
            'tmdb_api_errors': 0,
            'tmdb_search_used': 0,
            'tmdb_search_multiple_results': 0,
            'topic_api_errors': 0,
            'db_errors': 0,
            'start_time': None,
            'end_time': None
        }
        
    def setup_logging(self):
        """Setup detailed logging with separate files for success and errors"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Setup loggers
        self.success_logger = logging.getLogger('success')
        self.error_logger = logging.getLogger('error')
        self.warning_logger = logging.getLogger('warning')
        self.summary_logger = logging.getLogger('summary')
        
        # Clear any existing handlers
        for logger in [self.success_logger, self.error_logger, self.warning_logger, self.summary_logger]:
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
        
        # Warning logger
        warning_handler = logging.FileHandler(f'logs/cast_import_warnings_{timestamp}.log')
        warning_formatter = logging.Formatter('%(asctime)s - WARNING - %(message)s')
        warning_handler.setFormatter(warning_formatter)
        self.warning_logger.addHandler(warning_handler)
        
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
            self.main_logger.info("Database connection established successfully")
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
        self.main_logger.info("Database connection closed")
    
    def get_movies_and_shows(self, specific_movie_id=None):
        """Get movies and shows from primary_topics table in external schema"""
        try:
            if specific_movie_id:
                # For testing - get specific movie
                self.cursor.execute(f'''
                SELECT pt.primary_topic_id, pt.name, ts.source_id, ts.source_name, ts.source_id_type
                FROM {DB_EXTERNAL_SCHEMA}.primary_topics pt
                JOIN {DB_EXTERNAL_SCHEMA}.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
                WHERE pt.type IN ('movie', 'show') AND pt.primary_topic_id = %s AND ts.source_name != 'letterboxd'
                ''', (specific_movie_id,))
            else:
                # Get all movies and shows
                self.cursor.execute(f'''
                SELECT pt.primary_topic_id, pt.name, ts.source_id, ts.source_name, ts.source_id_type
                FROM {DB_EXTERNAL_SCHEMA}.primary_topics pt
                JOIN {DB_EXTERNAL_SCHEMA}.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
                WHERE pt.type IN ('movie', 'show') AND ts.source_name != 'letterboxd'
                ORDER BY pt.primary_topic_id
                ''')
            return self.cursor.fetchall()
        except Exception as e:
            self.error_logger.error(f"Database query failed while fetching movies/shows: {str(e)}")
            return []
    
    def search_tmdb_by_name(self, movie_name, primary_topic_id):
        """Search TMDb using movie/show name and return TMDb ID"""
        try:
            self.main_logger.info(f"Searching TMDb for: '{movie_name}' (primary_topic_id: {primary_topic_id})")
            
            # Try movie search first
            search_endpoint = f"{self.tmdb_base_url}/search/movie"
            params = {"query": movie_name}
            response = requests.get(search_endpoint, headers=self.headers, params=params, timeout=30, verify=False)
            
            if response.status_code == 200:
                movie_results = response.json().get('results', [])
                if movie_results:
                    self.stats['tmdb_search_used'] += 1
                    
                    # Check for multiple exact title matches
                    exact_matches = [r for r in movie_results if r.get('title', '').lower() == movie_name.lower()]
                    if len(exact_matches) > 1:
                        self.stats['tmdb_search_multiple_results'] += 1
                        self.warning_logger.warning(f"Multiple exact title matches found for '{movie_name}' (primary_topic_id: {primary_topic_id}). Found {len(exact_matches)} matches. Using first result (TMDb ID: {exact_matches[0]['id']})")
                        return exact_matches[0]['id'], 'movie'
                    
                    # Use first result
                    tmdb_id = movie_results[0]['id']
                    self.success_logger.info(f"Found movie in TMDb search: '{movie_name}' -> TMDb ID: {tmdb_id}")
                    return tmdb_id, 'movie'
            
            # If movie search fails, try TV search
            search_endpoint = f"{self.tmdb_base_url}/search/tv"
            response = requests.get(search_endpoint, headers=self.headers, params=params, timeout=30, verify=False)
            
            if response.status_code == 200:
                tv_results = response.json().get('results', [])
                if tv_results:
                    self.stats['tmdb_search_used'] += 1
                    
                    # Check for multiple exact title matches
                    exact_matches = [r for r in tv_results if r.get('name', '').lower() == movie_name.lower()]
                    if len(exact_matches) > 1:
                        self.stats['tmdb_search_multiple_results'] += 1
                        self.warning_logger.warning(f"Multiple exact title matches found for TV show '{movie_name}' (primary_topic_id: {primary_topic_id}). Found {len(exact_matches)} matches. Using first result (TMDb ID: {exact_matches[0]['id']})")
                        return exact_matches[0]['id'], 'tv'
                    
                    # Use first result
                    tmdb_id = tv_results[0]['id']
                    self.success_logger.info(f"Found TV show in TMDb search: '{movie_name}' -> TMDb ID: {tmdb_id}")
                    return tmdb_id, 'tv'
            
            # No results found
            self.error_logger.error(f"TMDb search failed: No results found for '{movie_name}' (primary_topic_id: {primary_topic_id})")
            return None, None
            
        except Exception as e:
            self.error_logger.error(f"TMDb search API error for '{movie_name}' (primary_topic_id: {primary_topic_id}): {str(e)}")
            return None, None
    
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
            
            self.main_logger.info(f"Calling topic API for actor: {actor_data['name']} (TMDb ID: {actor_data['tmdb_id']})")
            
            response = requests.post(
                self.topic_api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                result = response.json()
                topic_id = result.get('topic_id')
                if topic_id:
                    self.stats['total_topics_created'] += 1
                    self.success_logger.info(f"Topic API success: Actor '{actor_data['name']}' -> Topic ID: {topic_id}")
                    return topic_id
                else:
                    raise ValueError("No topic_id in API response")
            else:
                raise requests.RequestException(f"Topic API returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            if retry_count == 0:
                self.main_logger.warning(f"Topic API failed for {actor_data['name']}, retrying in 2 seconds...")
                time.sleep(2)
                return self.call_topic_ingestion_api(actor_data, retry_count=1)
            else:
                self.error_logger.error(f"Topic API failed for '{actor_data['name']}' (TMDb ID: {actor_data['tmdb_id']}) after retry: {str(e)}")
                self.stats['topic_api_errors'] += 1
                return None
    
    def fetch_cast_from_tmdb(self, tmdb_id, primary_topic_id, movie_show_name, content_type='movie', cast_limit=2, retry_count=0):
        """Fetch cast details from TMDb"""
        try:
            self.main_logger.info(f"Fetching cast from TMDb for: '{movie_show_name}' (TMDb ID: {tmdb_id}, Type: {content_type})")
            
            # Choose endpoint based on content type
            if content_type == 'tv':
                endpoint = f"{self.tmdb_base_url}/tv/{tmdb_id}/credits"
            else:
                endpoint = f"{self.tmdb_base_url}/movie/{tmdb_id}/credits"
            
            response = requests.get(endpoint, headers=self.headers, timeout=30, verify=False)
            
            # If initial endpoint fails, try the other type
            if response.status_code != 200 and content_type == 'movie':
                self.main_logger.warning(f"Movie endpoint failed for '{movie_show_name}', trying TV endpoint...")
                endpoint = f"{self.tmdb_base_url}/tv/{tmdb_id}/credits"
                response = requests.get(endpoint, headers=self.headers, timeout=30, verify=False)
            elif response.status_code != 200 and content_type == 'tv':
                self.main_logger.warning(f"TV endpoint failed for '{movie_show_name}', trying Movie endpoint...")
                endpoint = f"{self.tmdb_base_url}/movie/{tmdb_id}/credits"
                response = requests.get(endpoint, headers=self.headers, timeout=30, verify=False)
            
            response.raise_for_status()
            credits_data = response.json()
            
            if 'cast' not in credits_data or not credits_data['cast']:
                self.error_logger.error(f"TMDb returned empty cast list for '{movie_show_name}' (TMDb ID: {tmdb_id})")
                return []
            
            cast_list = credits_data.get('cast', [])
            self.main_logger.info(f"TMDb returned {len(cast_list)} cast members for '{movie_show_name}', processing top {cast_limit}")
            self.stats['total_cast_fetched'] += len(cast_list[:cast_limit])
                
            # Process cast data (limit to top cast members - lead actors)
            cast_details = []
            for i, actor in enumerate(cast_list[:cast_limit]):
                self.main_logger.info(f"Processing cast member {i+1}/{cast_limit}: {actor.get('name', 'Unknown')} as {actor.get('character', 'Unknown character')}")
                
                # Get detailed person info for each cast member
                person_endpoint = f"{self.tmdb_base_url}/person/{actor['id']}"
                person_params = {"append_to_response": "external_ids,images"}
                person_response = requests.get(person_endpoint, headers=self.headers, params=person_params, timeout=30, verify=False)
                
                if person_response.status_code != 200:
                    self.error_logger.error(f"Failed to fetch person details for actor {actor.get('name', 'Unknown')} (TMDb person ID: {actor['id']})")
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
                self.success_logger.info(f"Successfully processed cast member: {cast_member['name']} as {cast_member['character']} for '{movie_show_name}'")
                
                # Respect API rate limits
                time.sleep(0.25)
                
            self.main_logger.info(f"Successfully fetched {len(cast_details)} cast members for '{movie_show_name}'")
            return cast_details
            
        except Exception as e:
            if retry_count == 0:
                self.main_logger.warning(f"TMDb API failed for '{movie_show_name}' (TMDb ID: {tmdb_id}), retrying in 2 seconds...")
                time.sleep(2)
                return self.fetch_cast_from_tmdb(tmdb_id, primary_topic_id, movie_show_name, content_type, cast_limit, retry_count=1)
            else:
                self.error_logger.error(f"TMDb API failed for '{movie_show_name}' (TMDb ID: {tmdb_id}) after retry: {str(e)}")
                self.stats['tmdb_api_errors'] += 1
                return []
    
    def fetch_cast_from_imdb_id(self, imdb_id, primary_topic_id, movie_show_name, cast_limit=2):
        """Convert IMDb ID to TMDb ID and fetch cast details"""
        try:
            self.main_logger.info(f"Converting IMDb ID to TMDb ID for: '{movie_show_name}' (IMDb ID: {imdb_id})")
            
            # First find the TMDb ID using the IMDb ID
            find_endpoint = f"{self.tmdb_base_url}/find/{imdb_id}"
            params = {"external_source": "imdb_id"}
            response = requests.get(find_endpoint, headers=self.headers, params=params, timeout=30, verify=False)
            response.raise_for_status()
            
            find_data = response.json()
            
            # Check if we found a movie match
            movie_results = find_data.get('movie_results', [])
            tv_results = find_data.get('tv_results', [])
            
            if movie_results:
                tmdb_id = movie_results[0]['id']
                content_type = 'movie'
                self.success_logger.info(f"IMDb ID {imdb_id} converted to TMDb movie ID: {tmdb_id}")
            elif tv_results:
                tmdb_id = tv_results[0]['id']
                content_type = 'tv'
                self.success_logger.info(f"IMDb ID {imdb_id} converted to TMDb TV ID: {tmdb_id}")
            else:
                self.error_logger.error(f"No TMDb match found for IMDb ID: {imdb_id} ('{movie_show_name}')")
                return []
                
            # Now use the TMDb ID to fetch cast details
            return self.fetch_cast_from_tmdb(tmdb_id, primary_topic_id, movie_show_name, content_type, cast_limit)
            
        except Exception as e:
            self.error_logger.error(f"Failed to convert IMDb ID {imdb_id} to TMDb ID for '{movie_show_name}': {str(e)}")
            return []
    
    def insert_cast_data(self, cast_details, retry_count=0):
        """Insert cast details into the internal schema table"""
        try:
            if not cast_details:
                return 0
                
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
                    self.success_logger.info(f"Inserted cast data: {cast_member['name']} for '{cast_member['movie_show_name']}'")
                else:
                    self.warning_logger.warning(f"Duplicate cast data skipped: {cast_member['name']} for '{cast_member['movie_show_name']}' (already exists)")
            
            self.conn.commit()
            self.stats['total_cast_inserted'] += inserted_count
            self.main_logger.info(f"Database: Inserted {inserted_count}/{len(cast_details)} cast members")
            return inserted_count
        except Exception as e:
            self.conn.rollback()
            if retry_count == 0:
                self.main_logger.warning(f"Database insert failed, retrying in 1 second...")
                time.sleep(1)
                return self.insert_cast_data(cast_details, retry_count=1)
            else:
                self.error_logger.error(f"Database insert failed after retry: {str(e)}")
                self.stats['db_errors'] += 1
                return 0
    
    def insert_topic_links(self, primary_topic_id, actor_topic_ids, movie_show_name, retry_count=0):
        """Insert topic-to-topic links"""
        try:
            if not actor_topic_ids:
                return 0
                
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
                        self.success_logger.info(f"Created topic link: Movie {primary_topic_id} -> Actor topic {actor_topic_id}")
                    else:
                        self.warning_logger.warning(f"Duplicate topic link skipped: Movie {primary_topic_id} -> Actor topic {actor_topic_id} (already exists)")
            
            self.conn.commit()
            self.stats['total_links_created'] += inserted_count
            self.main_logger.info(f"Database: Created {inserted_count}/{len([x for x in actor_topic_ids if x])} topic links for '{movie_show_name}'")
            return inserted_count
        except Exception as e:
            self.conn.rollback()
            if retry_count == 0:
                self.main_logger.warning(f"Topic links insert failed, retrying in 1 second...")
                time.sleep(1)
                return self.insert_topic_links(primary_topic_id, actor_topic_ids, movie_show_name, retry_count=1)
            else:
                self.error_logger.error(f"Topic links insert failed for '{movie_show_name}' after retry: {str(e)}")
                self.stats['db_errors'] += 1
                return 0
    
    def process_single_movie(self, movie_data, use_search=False):
        """Process a single movie - core logic used by both test and full processing"""
        primary_topic_id, movie_show_name, source_id, source_name, source_id_type = movie_data
        
        self.main_logger.info(f"=== Processing: '{movie_show_name}' (ID: {primary_topic_id}) ===")
        
        success_metrics = {
            'cast_fetched': 0,
            'cast_inserted': 0,
            'topics_created': 0,
            'links_created': 0,
            'errors': []
        }
        
        try:
            # Step 1: Determine source and fetch cast details
            cast_details = []
            
            if use_search or (not source_id and not source_name):
                # Use TMDb search for priority items without proper sources
                self.main_logger.info(f"Using TMDb search for '{movie_show_name}' (no TMDb/IMDb source available)")
                tmdb_id, content_type = self.search_tmdb_by_name(movie_show_name, primary_topic_id)
                if tmdb_id:
                    cast_details = self.fetch_cast_from_tmdb(tmdb_id, primary_topic_id, movie_show_name, content_type)
                else:
                    success_metrics['errors'].append("TMDb search failed - no results")
            elif source_name and source_name.lower() == 'tmdb' and source_id_type and source_id_type.lower() == 'tmdb_id':
                cast_details = self.fetch_cast_from_tmdb(source_id, primary_topic_id, movie_show_name)
            elif source_name and source_name.lower() == 'imdb' and source_id_type and source_id_type.lower() == 'imdb_id':
                cast_details = self.fetch_cast_from_imdb_id(source_id, primary_topic_id, movie_show_name)
            else:
                success_metrics['errors'].append(f"Unsupported source: {source_name}/{source_id_type}")
            
            success_metrics['cast_fetched'] = len(cast_details)
            
            if not cast_details:
                self.error_logger.error(f"FAILED: No cast details obtained for '{movie_show_name}' (primary_topic_id: {primary_topic_id}). Errors: {success_metrics['errors']}")
                return False, success_metrics
            
            # Step 2: Insert cast data
            cast_inserted = self.insert_cast_data(cast_details)
            success_metrics['cast_inserted'] = cast_inserted
            
            # Step 3: Create actor topics and get topic IDs
            actor_topic_ids = []
            for cast_member in cast_details:
                topic_id = self.call_topic_ingestion_api(cast_member)
                if topic_id:
                    actor_topic_ids.append(topic_id)
                    success_metrics['topics_created'] += 1
                else:
                    success_metrics['errors'].append(f"Topic creation failed for {cast_member['name']}")
            
            # Step 4: Create topic links
            links_created = self.insert_topic_links(primary_topic_id, actor_topic_ids, movie_show_name)
            success_metrics['links_created'] = links_created
            
            # Determine success level
            is_full_success = (success_metrics['cast_inserted'] > 0 and 
                             success_metrics['topics_created'] > 0 and 
                             success_metrics['links_created'] > 0 and 
                             len(success_metrics['errors']) == 0)
            
            is_partial_success = (success_metrics['cast_inserted'] > 0 or 
                                success_metrics['topics_created'] > 0 or 
                                success_metrics['links_created'] > 0)
            
            if is_full_success:
                self.success_logger.info(f"FULL SUCCESS: '{movie_show_name}' - Cast: {success_metrics['cast_fetched']}/{success_metrics['cast_inserted']}, Topics: {success_metrics['topics_created']}, Links: {success_metrics['links_created']}")
                return True, success_metrics
            elif is_partial_success:
                self.warning_logger.warning(f"PARTIAL SUCCESS: '{movie_show_name}' - Cast: {success_metrics['cast_fetched']}/{success_metrics['cast_inserted']}, Topics: {success_metrics['topics_created']}, Links: {success_metrics['links_created']}, Errors: {success_metrics['errors']}")
                return 'partial', success_metrics
            else:
                self.error_logger.error(f"FAILED: '{movie_show_name}' - No data was successfully processed. Errors: {success_metrics['errors']}")
                return False, success_metrics
            
        except Exception as e:
            success_metrics['errors'].append(f"Unexpected error: {str(e)}")
            self.error_logger.error(f"CRITICAL ERROR processing '{movie_show_name}' (primary_topic_id: {primary_topic_id}): {str(e)}")
            return False, success_metrics
    
    def get_priority_movie_sources(self, primary_topic_id):
        """Get existing sources for a priority movie"""
        try:
            self.cursor.execute(f'''
            SELECT ts.source_id, ts.source_name, ts.source_id_type
            FROM {DB_EXTERNAL_SCHEMA}.topic_sources ts
            WHERE ts.primary_topic_id = %s 
            AND ts.source_name IN ('tmdb', 'imdb')
            LIMIT 1
            ''', (primary_topic_id,))
            
            result = self.cursor.fetchone()
            if result:
                return result[0], result[1], result[2]  # source_id, source_name, source_id_type
            return None, None, None
        except Exception as e:
            self.error_logger.error(f"Failed to get sources for primary_topic_id {primary_topic_id}: {str(e)}")
            return None, None, None
    
    def process_priority_list(self, priority_file_path):
        """Process a specific list of movies/shows from JSON file"""
        self.main_logger.info("=== STARTING PRIORITY LIST PROCESSING ===")
        
        try:
            # Load priority list from JSON file
            with open(priority_file_path, 'r') as f:
                priority_items = json.load(f)
            
            self.main_logger.info(f"Loaded {len(priority_items)} items from priority list")
            
        except Exception as e:
            self.error_logger.error(f"Failed to load priority list from {priority_file_path}: {str(e)}")
            return False
        
        if not self.connect_to_db():
            return False
        
        self.stats['start_time'] = datetime.now()
        self.stats['total_movies'] = len(priority_items)
        
        for index, item in enumerate(priority_items, 1):
            primary_topic_id = item.get('primary_topic_id')
            movie_name = item.get('name', 'Unknown')
            
            if not primary_topic_id:
                self.error_logger.error(f"Missing primary_topic_id for item: {item}")
                continue
            
            self.main_logger.info(f"Priority Progress: {index}/{len(priority_items)} - Processing '{movie_name}' (ID: {primary_topic_id})")
            
            # Check if this movie has existing TMDb/IMDb sources
            source_id, source_name, source_id_type = self.get_priority_movie_sources(primary_topic_id)
            
            if source_id and source_name:
                # Has existing source - use normal processing
                self.main_logger.info(f"Found existing source for '{movie_name}': {source_name} ID {source_id}")
                movie_data = (primary_topic_id, movie_name, source_id, source_name, source_id_type)
                success, metrics = self.process_single_movie(movie_data, use_search=False)
            else:
                # No existing source - use TMDb search
                self.main_logger.info(f"No TMDb/IMDb source found for '{movie_name}', will use TMDb search")
                movie_data = (primary_topic_id, movie_name, None, None, None)
                success, metrics = self.process_single_movie(movie_data, use_search=True)
            
            # Update statistics
            if success == True:
                self.stats['successful_movies'] += 1
            elif success == 'partial':
                self.stats['partially_successful_movies'] += 1
            else:
                self.stats['failed_movies'] += 1
            
            # Rate limiting
            time.sleep(1)
        
        self.stats['end_time'] = datetime.now()
        self.close_db_connection()
        self.generate_final_report()
        return True
    
    def test_single_movie(self, movie_id):
        """Test the complete workflow on a single movie"""
        self.main_logger.info(f"=== TESTING MODE: Processing single movie ID {movie_id} ===")
        
        if not self.connect_to_db():
            return False
        
        # Get the specific movie
        movies = self.get_movies_and_shows(specific_movie_id=movie_id)
        if not movies:
            self.main_logger.error(f"Movie with ID {movie_id} not found in database")
            self.close_db_connection()
            return False
        
        movie_data = movies[0]
        success, metrics = self.process_single_movie(movie_data)
        
        self.close_db_connection()
        
        # Print test results
        self.main_logger.info("=== TEST RESULTS ===")
        self.main_logger.info(f"Movie processing: {'SUCCESS' if success == True else 'PARTIAL' if success == 'partial' else 'FAILED'}")
        self.main_logger.info(f"Cast fetched: {metrics['cast_fetched']}")
        self.main_logger.info(f"Cast inserted: {metrics['cast_inserted']}")
        self.main_logger.info(f"Topics created: {metrics['topics_created']}")
        self.main_logger.info(f"Links created: {metrics['links_created']}")
        if metrics['errors']:
            self.main_logger.info(f"Errors encountered: {metrics['errors']}")
        
        return success == True
    
    def process_all_movies_shows(self):
        """Process all movies and shows to fetch and store cast data"""
        self.stats['start_time'] = datetime.now()
        self.main_logger.info("=== STARTING FULL PROCESSING ===")
        
        if not self.connect_to_db():
            return False
        
        movies_shows = self.get_movies_and_shows()
        self.stats['total_movies'] = len(movies_shows)
        
        self.main_logger.info(f"Found {self.stats['total_movies']} movies/shows to process")
        
        for index, movie_data in enumerate(movies_shows, 1):
            movie_show_name = movie_data[1]
            
            # Progress reporting
            progress_pct = (index / self.stats['total_movies']) * 100
            self.main_logger.info(f"Progress: {index}/{self.stats['total_movies']} ({progress_pct:.1f}%) - {movie_show_name}")
            
            success, metrics = self.process_single_movie(movie_data)
            
            if success == True:
                self.stats['successful_movies'] += 1
            elif success == 'partial':
                self.stats['partially_successful_movies'] += 1
            else:
                self.stats['failed_movies'] += 1
            
            # Respect API rate limits between movies/shows
            time.sleep(1)
            
            # Progress checkpoint every 100 movies
            if index % 100 == 0:
                self.summary_logger.info(f"Checkpoint: Processed {index}/{self.stats['total_movies']} movies. Success: {self.stats['successful_movies']}, Partial: {self.stats['partially_successful_movies']}, Failed: {self.stats['failed_movies']}")
        
        self.stats['end_time'] = datetime.now()
        self.close_db_connection()
        self.generate_final_report()
        return True
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        duration = self.stats['end_time'] - self.stats['start_time']
        success_rate = (self.stats['successful_movies'] / self.stats['total_movies'] * 100) if self.stats['total_movies'] > 0 else 0
        partial_rate = (self.stats['partially_successful_movies'] / self.stats['total_movies'] * 100) if self.stats['total_movies'] > 0 else 0
        
        report = f"""
=== CAST IMPORT FINAL REPORT ===
Processing completed at: {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}
Total processing time: {duration}

OVERALL STATISTICS:
Total Movies/Shows Processed: {self.stats['total_movies']}
✅ Fully Successful: {self.stats['successful_movies']} ({success_rate:.1f}%)
⚠️  Partially Successful: {self.stats['partially_successful_movies']} ({partial_rate:.1f}%)
❌ Failed: {self.stats['failed_movies']} ({100-success_rate-partial_rate:.1f}%)

DATA STATISTICS:
Total Cast Members Fetched: {self.stats['total_cast_fetched']}
Total Cast Members Inserted: {self.stats['total_cast_inserted']}
Total Actor Topics Created: {self.stats['total_topics_created']}
Total Topic Links Created: {self.stats['total_links_created']}

API USAGE STATISTICS:
TMDb Search API Used: {self.stats['tmdb_search_used']} times
TMDb Multiple Results Found: {self.stats['tmdb_search_multiple_results']} times

ERROR BREAKDOWN:
TMDb API Errors: {self.stats['tmdb_api_errors']}
Topic Ingestion API Errors: {self.stats['topic_api_errors']}
Database Errors: {self.stats['db_errors']}

FILES GENERATED:
- logs/cast_import_success_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log
- logs/cast_import_errors_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log
- logs/cast_import_warnings_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log
- logs/cast_import_summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log

RECOMMENDATIONS:
{'- Review warning log for multiple TMDb search results' if self.stats['tmdb_search_multiple_results'] > 0 else ''}
{'- Check error log for failed API calls' if (self.stats['tmdb_api_errors'] + self.stats['topic_api_errors']) > 0 else ''}
{'- Investigate database connection issues' if self.stats['db_errors'] > 0 else ''}
        """
        
        self.summary_logger.info(report)
        self.main_logger.info(report)

def main():
    parser = argparse.ArgumentParser(description='Cast Data Importer with Priority Processing')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--movie-id', type=int, help='Movie ID to test (required with --test)')
    parser.add_argument('--priority-file', type=str, help='Path to JSON file with priority movies list')
    
    args = parser.parse_args()
    
    if args.test:
        if not args.movie_id:
            print("Error: --movie-id is required when using --test")
            sys.exit(1)
        
        importer = CastDataImporter(test_mode=True)
        success = importer.test_single_movie(args.movie_id)
        sys.exit(0 if success else 1)
    
    elif args.priority_file:
        importer = CastDataImporter()
        success = importer.process_priority_list(args.priority_file)
        sys.exit(0 if success else 1)
    
    else:
        importer = CastDataImporter()
        success = importer.process_all_movies_shows()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()