import os
import json
import time
import logging
import requests
import psycopg2
import urllib3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@dataclass
class ProcessingStats:
    """Class to track processing statistics"""
    total_processed: int = 0
    imdb_found: int = 0
    tmdb_found: int = 0
    not_found: int = 0
    errors: int = 0
    skipped: int = 0

class TMDBIMDBFetcher:
    def __init__(self, db_config: Dict, tmdb_bearer_token: str):
        self.db_config = db_config
        self.tmdb_bearer_token = tmdb_bearer_token
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.stats = ProcessingStats()
        
        # Setup HTTP headers for Bearer token authentication
        self.headers = {
            'Authorization': f'Bearer {tmdb_bearer_token}',
            'Content-Type': 'application/json'
        }
        
        # Setup logging
        self.setup_logging()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.25  # 4 requests per second max
    
    def setup_logging(self):
        """Setup comprehensive logging system"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Generate timestamp for log files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Main logger
        self.logger = logging.getLogger('tmdb_imdb_fetcher')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Main log file handler
        main_handler = logging.FileHandler(f'logs/tmdb_imdb_fetcher_{timestamp}.log')
        main_handler.setLevel(logging.INFO)
        main_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        self.logger.addHandler(main_handler)
        
        # Error log file handler
        error_handler = logging.FileHandler(f'logs/tmdb_imdb_errors_{timestamp}.log')
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - ERROR - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.info("Logging system initialized")
    
    def get_db_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            self.logger.debug("Database connection established")
            return conn
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def rate_limit(self):
        """Implement rate limiting for API calls"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_tmdb(self, name: str, media_type: str) -> Optional[Dict]:
        """Search TMDB for a movie/show by name"""
        self.rate_limit()
        
        # Map our types to TMDB types
        tmdb_type = 'movie' if media_type == 'movie' else 'tv'
        
        url = f"{self.tmdb_base_url}/search/{tmdb_type}"
        params = {
            'query': name,
            'language': 'en-US'
        }
        
        try:
            self.logger.debug(f"Searching TMDB for '{name}' as {tmdb_type}")
            response = requests.get(url, params=params, headers=self.headers, 
                                  timeout=10, verify=False)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if results:
                # Return the first result with the highest popularity
                best_match = max(results, key=lambda x: x.get('popularity', 0))
                self.logger.debug(f"Found TMDB match for '{name}': ID {best_match.get('id')}")
                return best_match
            else:
                self.logger.debug(f"No TMDB results found for '{name}'")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"TMDB API request failed for '{name}': {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error searching TMDB for '{name}': {str(e)}")
            return None
    
    def get_imdb_id_from_tmdb(self, tmdb_id: int, media_type: str) -> Optional[str]:
        """Get IMDB ID from TMDB ID"""
        self.rate_limit()
        
        tmdb_type = 'movie' if media_type == 'movie' else 'tv'
        url = f"{self.tmdb_base_url}/{tmdb_type}/{tmdb_id}/external_ids"
        
        try:
            self.logger.debug(f"Getting external IDs for TMDB ID {tmdb_id}")
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            response.raise_for_status()
            
            data = response.json()
            imdb_id = data.get('imdb_id')
            
            if imdb_id:
                self.logger.debug(f"Found IMDB ID {imdb_id} for TMDB ID {tmdb_id}")
                return imdb_id
            else:
                self.logger.debug(f"No IMDB ID found for TMDB ID {tmdb_id}")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Failed to get external IDs for TMDB ID {tmdb_id}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting external IDs for TMDB ID {tmdb_id}: {str(e)}")
            return None
    
    def get_primary_topics_without_imdb_tmdb(self) -> List[Tuple]:
        """Get primary topics that don't have IMDB or TMDB sources"""
        query = """
        SELECT DISTINCT pt.primary_topic_id, pt.type, pt.name
        FROM bingeplus_external.primary_topics pt
        WHERE pt.type IN ('movie', 'show')
        AND pt.primary_topic_id NOT IN (
            SELECT DISTINCT ts.primary_topic_id 
            FROM bingeplus_external.topic_sources ts 
            WHERE ts.source_name IN ('imdb', 'tmdb')
        )
        ORDER BY pt.primary_topic_id
        """
        
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
            self.logger.info(f"Found {len(results)} primary topics without IMDB/TMDB sources")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to fetch primary topics: {str(e)}")
            raise
    
    def insert_topic_source(self, primary_topic_id: int, source_id: str, 
                           source_name: str, source_id_type: str) -> bool:
        """Insert a new topic source"""
        query = """
        INSERT INTO bingeplus_external.topic_sources 
        (primary_topic_id, source_id, source_name, source_id_type)
        VALUES (%s, %s, %s, %s)
        """
        
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (primary_topic_id, source_id, source_name, source_id_type))
                    conn.commit()
            
            self.logger.info(f"Inserted {source_name} source for primary_topic_id {primary_topic_id}: {source_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to insert topic source for primary_topic_id {primary_topic_id}: {str(e)}")
            return False
    
    def process_primary_topic(self, primary_topic_id: int, topic_type: str, name: str) -> Dict:
        """Process a single primary topic to find and insert IMDB/TMDB IDs"""
        self.logger.info(f"Processing primary_topic_id {primary_topic_id}: '{name}' ({topic_type})")
        
        result = {
            'primary_topic_id': primary_topic_id,
            'name': name,
            'type': topic_type,
            'imdb_found': False,
            'tmdb_found': False,
            'error': None
        }
        
        try:
            # Search TMDB
            tmdb_result = self.search_tmdb(name, topic_type)
            
            if not tmdb_result:
                self.logger.warning(f"No TMDB results found for '{name}' (ID: {primary_topic_id})")
                result['error'] = 'No TMDB results found'
                self.stats.not_found += 1
                return result
            
            tmdb_id = tmdb_result.get('id')
            
            # Try to get IMDB ID first (preferred)
            imdb_id = self.get_imdb_id_from_tmdb(tmdb_id, topic_type)
            
            if imdb_id:
                # Insert IMDB source
                if self.insert_topic_source(primary_topic_id, imdb_id, 'imdb', 'imdb_id'):
                    result['imdb_found'] = True
                    self.stats.imdb_found += 1
                    self.logger.info(f"Successfully added IMDB ID {imdb_id} for '{name}'")
                else:
                    result['error'] = 'Failed to insert IMDB source'
                    self.stats.errors += 1
            else:
                # No IMDB ID found, use TMDB ID instead
                if self.insert_topic_source(primary_topic_id, str(tmdb_id), 'tmdb', 'tmdb_id'):
                    result['tmdb_found'] = True
                    self.stats.tmdb_found += 1
                    self.logger.info(f"Successfully added TMDB ID {tmdb_id} for '{name}' (no IMDB ID available)")
                else:
                    result['error'] = 'Failed to insert TMDB source'
                    self.stats.errors += 1
            
        except Exception as e:
            self.logger.error(f"Error processing primary_topic_id {primary_topic_id} ('{name}'): {str(e)}")
            result['error'] = str(e)
            self.stats.errors += 1
        
        self.stats.total_processed += 1
        return result
    
    def generate_summary(self, results: List[Dict], start_time: datetime):
        """Generate a comprehensive summary of the processing"""
        end_time = datetime.now()
        duration = end_time - start_time
        
        summary = f"""
=== TMDB/IMDB ID Fetcher Summary ===
Execution Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {duration}

STATISTICS:
- Total Processed: {self.stats.total_processed}
- IMDB IDs Found: {self.stats.imdb_found}
- TMDB IDs Found: {self.stats.tmdb_found}
- Not Found: {self.stats.not_found}
- Errors: {self.stats.errors}
- Success Rate: {((self.stats.imdb_found + self.stats.tmdb_found) / max(self.stats.total_processed, 1)) * 100:.2f}%

BREAKDOWN BY RESULT:
"""
        
        # Group results by outcome
        imdb_successes = [r for r in results if r['imdb_found']]
        tmdb_successes = [r for r in results if r['tmdb_found']]
        failures = [r for r in results if r.get('error')]
        
        if imdb_successes:
            summary += f"\nIMDB IDs Added ({len(imdb_successes)}):\n"
            for result in imdb_successes:
                summary += f"  - ID {result['primary_topic_id']}: {result['name']}\n"
        
        if tmdb_successes:
            summary += f"\nTMDB IDs Added ({len(tmdb_successes)}):\n"
            for result in tmdb_successes:
                summary += f"  - ID {result['primary_topic_id']}: {result['name']}\n"
        
        if failures:
            summary += f"\nFailed/Not Found ({len(failures)}):\n"
            for result in failures:
                summary += f"  - ID {result['primary_topic_id']}: {result['name']} - {result['error']}\n"
        
        # Log summary
        self.logger.info(summary)
        
        # Save summary to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = f"logs/summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(summary)
        
        print(f"\nSummary saved to: {summary_file}")
        return summary
    
    def run(self):
        """Main execution method"""
        start_time = datetime.now()
        self.logger.info("=== Starting TMDB/IMDB ID Fetcher Script ===")
        
        try:
            # Get primary topics that need processing
            primary_topics = self.get_primary_topics_without_imdb_tmdb()
            
            if not primary_topics:
                self.logger.info("No primary topics found that need processing")
                return
            
            self.logger.info(f"Starting to process {len(primary_topics)} primary topics")
            
            results = []
            
            # Process each primary topic
            for i, (primary_topic_id, topic_type, name) in enumerate(primary_topics, 1):
                self.logger.info(f"Progress: {i}/{len(primary_topics)}")
                
                result = self.process_primary_topic(primary_topic_id, topic_type, name)
                results.append(result)
                
                # Add a small delay between processing to be respectful to the API
                if i % 10 == 0:
                    self.logger.info(f"Processed {i} items, taking a short break...")
                    time.sleep(2)
            
            # Generate summary
            self.generate_summary(results, start_time)
            
        except Exception as e:
            self.logger.error(f"Script execution failed: {str(e)}")
            raise
        finally:
            self.logger.info("=== Script execution completed ===")

def main():
    """Main function"""
    # Load environment variables
    load_dotenv()
    
    # Database configuration from environment variables
    DB_CONFIG = {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': int(os.getenv('DB_PORT', 5432))
    }
    
    # TMDB Bearer token from environment
    TMDB_BEARER_TOKEN = os.getenv('TMDB_BEARER_TOKEN')
    
    # Validate configuration
    if not TMDB_BEARER_TOKEN:
        print("ERROR: TMDB_BEARER_TOKEN not found in environment variables")
        print("Please add TMDB_BEARER_TOKEN=your_token_here to your .env file")
        return
    
    required_db_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_db_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return
    
    try:
        # Create and run the fetcher
        fetcher = TMDBIMDBFetcher(DB_CONFIG, TMDB_BEARER_TOKEN)
        fetcher.run()
        
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        print(f"Script failed with error: {str(e)}")

if __name__ == "__main__":
    main()