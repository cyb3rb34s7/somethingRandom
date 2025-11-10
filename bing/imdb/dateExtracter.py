import os
import re
import time
import logging
import warnings
import psycopg2
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, List, Tuple, Dict

# Disable SSL warnings
warnings.filterwarnings('ignore')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ShowDateUpdater:
    def __init__(self, primary_topic_ids: Optional[List[int]] = None):
        """
        Initialize the Show Date Updater
        
        Args:
            primary_topic_ids: Optional list of specific primary_topic_ids to process.
                             If None, processes all shows.
        """
        self.primary_topic_ids = primary_topic_ids
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        self.setup_logging()
        
        # Load environment variables
        load_dotenv()
        self.tmdb_bearer_token = os.getenv('TMDB_BEARER_TOKEN')
        self.schema_name = os.getenv('SCHEMA_NAME', 'Bingeplus_schema')
        
        # Database connection parameters
        self.db_params = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT', 5432),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # TMDB API configuration
        self.tmdb_headers = {
            'Authorization': f'Bearer {self.tmdb_bearer_token}',
            'Content-Type': 'application/json'
        }
        self.tmdb_base_url = 'https://api.themoviedb.org/3'
        
        # Statistics
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'date_from_episode': 0,
            'date_from_season': 0,
            'date_from_first_air': 0
        }
        
        self.conn = None
        self.cursor = None
    
    def setup_logging(self):
        """Setup multiple log files with timestamps"""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # Log file paths
        self.log_files = {
            'main': os.path.join(log_dir, f'main_process_{self.timestamp}.log'),
            'api': os.path.join(log_dir, f'api_calls_{self.timestamp}.log'),
            'date_resolution': os.path.join(log_dir, f'date_resolution_{self.timestamp}.log'),
            'errors': os.path.join(log_dir, f'errors_{self.timestamp}.log'),
            'database': os.path.join(log_dir, f'database_operations_{self.timestamp}.log')
        }
        
        # Create loggers
        self.loggers = {}
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        for log_name, log_file in self.log_files.items():
            logger = logging.getLogger(log_name)
            logger.setLevel(logging.DEBUG)
            
            # File handler
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter(log_format, datefmt=date_format)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            
            # Also add console handler for main logger
            if log_name == 'main':
                ch = logging.StreamHandler()
                ch.setLevel(logging.INFO)
                ch.setFormatter(formatter)
                logger.addHandler(ch)
            
            self.loggers[log_name] = logger
    
    def log(self, logger_name: str, level: str, message: str):
        """Helper method to log to specific logger"""
        logger = self.loggers.get(logger_name)
        if logger:
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(message)
    
    def connect_database(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            self.log('main', 'info', '=' * 80)
            self.log('main', 'info', 'CONNECTING TO DATABASE')
            self.log('main', 'info', '=' * 80)
            self.log('database', 'info', f'Connection parameters: host={self.db_params["host"]}, database={self.db_params["database"]}, user={self.db_params["user"]}')
            
            self.conn = psycopg2.connect(**self.db_params)
            self.cursor = self.conn.cursor()
            
            self.log('main', 'info', '✓ Database connection established successfully')
            self.log('database', 'info', '✓ Connection successful')
            return True
            
        except Exception as e:
            self.log('main', 'error', f'✗ Failed to connect to database: {str(e)}')
            self.log('errors', 'error', f'Database connection failed: {str(e)}')
            return False
    
    def parse_show_name(self, name: str) -> str:
        """
        Remove season indicators from show name
        
        Examples:
            "The Witcher Season 3" -> "The Witcher"
            "Breaking Bad S5" -> "Breaking Bad"
            "Game of Thrones" -> "Game of Thrones"
        """
        original_name = name
        
        # Patterns to remove
        patterns = [
            r'\s+Season\s+\d+',
            r'\s+season\s+\d+',
            r'\s+SEASON\s+\d+',
            r'\s+S\d+',
            r'\s+s\d+',
            r'\s+\(Season\s+\d+\)',
            r'\s+-\s+Season\s+\d+',
        ]
        
        parsed_name = name
        for pattern in patterns:
            parsed_name = re.sub(pattern, '', parsed_name, flags=re.IGNORECASE)
        
        parsed_name = parsed_name.strip()
        
        if parsed_name != original_name:
            self.log('main', 'debug', f'Parsed name: "{original_name}" -> "{parsed_name}"')
        
        return parsed_name
    
    def call_tmdb_api(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make TMDB API call with logging
        
        Args:
            endpoint: API endpoint (e.g., '/find/tt0944947')
            params: Optional query parameters
            
        Returns:
            JSON response or None if failed
        """
        url = f'{self.tmdb_base_url}{endpoint}'
        
        self.log('api', 'info', f'REQUEST: GET {url}')
        if params:
            self.log('api', 'info', f'PARAMS: {params}')
        
        try:
            response = requests.get(
                url,
                headers=self.tmdb_headers,
                params=params,
                verify=False,
                timeout=10
            )
            
            self.log('api', 'info', f'RESPONSE: Status Code {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.log('api', 'debug', f'RESPONSE DATA: {data}')
                return data
            elif response.status_code == 429:
                self.log('api', 'warning', 'Rate limit hit, waiting 2 seconds...')
                self.log('errors', 'warning', f'Rate limit hit for endpoint: {endpoint}')
                time.sleep(2)
                return self.call_tmdb_api(endpoint, params)
            else:
                self.log('api', 'error', f'API call failed: {response.status_code} - {response.text}')
                self.log('errors', 'error', f'API error for {endpoint}: {response.status_code} - {response.text}')
                return None
                
        except Exception as e:
            self.log('api', 'error', f'Exception during API call: {str(e)}')
            self.log('errors', 'error', f'Exception for {endpoint}: {str(e)}')
            return None
    
    def convert_imdb_to_tmdb(self, imdb_id: str) -> Optional[int]:
        """
        Convert IMDB ID to TMDB ID
        
        Args:
            imdb_id: IMDB ID (e.g., 'tt0944947')
            
        Returns:
            TMDB ID or None if not found
        """
        self.log('api', 'info', f'Converting IMDB ID to TMDB ID: {imdb_id}')
        
        # Ensure IMDB ID has 'tt' prefix
        if not imdb_id.startswith('tt'):
            imdb_id = f'tt{imdb_id}'
        
        data = self.call_tmdb_api(f'/find/{imdb_id}', {'external_source': 'imdb_id'})
        
        if data and 'tv_results' in data and len(data['tv_results']) > 0:
            tmdb_id = data['tv_results'][0]['id']
            self.log('api', 'info', f'✓ Found TMDB ID: {tmdb_id} for IMDB ID: {imdb_id}')
            return tmdb_id
        else:
            self.log('api', 'warning', f'✗ No TMDB ID found for IMDB ID: {imdb_id}')
            self.log('errors', 'warning', f'IMDB to TMDB conversion failed for: {imdb_id}')
            return None
    
    def get_latest_season_date(self, tmdb_id: int, show_name: str) -> Optional[Tuple[str, str]]:
        """
        Get the latest air date for a show with fallback logic:
        1. Try to get last episode's air date
        2. Fall back to latest season premiere date
        3. Fall back to first_air_date
        
        Args:
            tmdb_id: TMDB show ID
            show_name: Name of the show (for logging)
            
        Returns:
            Tuple of (date, source) or None if all attempts fail
            source can be: 'last_episode', 'season_premiere', 'first_air_date'
        """
        self.log('date_resolution', 'info', '=' * 80)
        self.log('date_resolution', 'info', f'RESOLVING DATE FOR: {show_name} (TMDB ID: {tmdb_id})')
        self.log('date_resolution', 'info', '=' * 80)
        
        # Step 1: Get TV show details
        show_data = self.call_tmdb_api(f'/tv/{tmdb_id}')
        
        if not show_data:
            self.log('date_resolution', 'error', f'✗ Failed to fetch show details for TMDB ID: {tmdb_id}')
            return None
        
        number_of_seasons = show_data.get('number_of_seasons', 0)
        last_air_date = show_data.get('last_air_date')
        first_air_date = show_data.get('first_air_date')
        
        self.log('date_resolution', 'info', f'Show details: {number_of_seasons} seasons')
        self.log('date_resolution', 'info', f'First air date: {first_air_date}')
        self.log('date_resolution', 'info', f'Last air date: {last_air_date}')
        
        if number_of_seasons == 0:
            self.log('date_resolution', 'warning', '✗ Show has 0 seasons')
            if first_air_date:
                self.log('date_resolution', 'info', f'✓ Using first_air_date as fallback: {first_air_date}')
                return (first_air_date, 'first_air_date')
            else:
                self.log('date_resolution', 'error', '✗ No date information available')
                return None
        
        latest_season_number = number_of_seasons
        self.log('date_resolution', 'info', f'Latest season number: {latest_season_number}')
        
        # Step 2: Try to get last episode's air date from the latest season
        self.log('date_resolution', 'info', f'ATTEMPT 1: Fetching last episode air date from season {latest_season_number}')
        season_data = self.call_tmdb_api(f'/tv/{tmdb_id}/season/{latest_season_number}')
        
        if season_data:
            season_air_date = season_data.get('air_date')
            episodes = season_data.get('episodes', [])
            
            self.log('date_resolution', 'info', f'Season {latest_season_number} has {len(episodes)} episodes')
            self.log('date_resolution', 'info', f'Season premiere date: {season_air_date}')
            
            # Try to find the last aired episode
            last_episode_date = None
            if episodes:
                # Filter episodes that have air dates and sort by episode number
                aired_episodes = [ep for ep in episodes if ep.get('air_date')]
                
                if aired_episodes:
                    # Get the last episode with an air date
                    last_episode = aired_episodes[-1]
                    last_episode_date = last_episode.get('air_date')
                    episode_number = last_episode.get('episode_number')
                    episode_name = last_episode.get('name', 'Unknown')
                    
                    self.log('date_resolution', 'info', f'Last aired episode: S{latest_season_number}E{episode_number} - "{episode_name}"')
                    self.log('date_resolution', 'info', f'Last episode air date: {last_episode_date}')
                    
                    if last_episode_date:
                        self.log('date_resolution', 'info', f'✓ SUCCESS: Using last episode air date: {last_episode_date}')
                        return (last_episode_date, 'last_episode')
            
            # Step 3: Fall back to season premiere date
            if season_air_date:
                self.log('date_resolution', 'info', 'ATTEMPT 2: Last episode date not available')
                self.log('date_resolution', 'info', f'✓ FALLBACK: Using season premiere date: {season_air_date}')
                return (season_air_date, 'season_premiere')
        else:
            self.log('date_resolution', 'warning', f'✗ Failed to fetch season {latest_season_number} details')
        
        # Step 4: Fall back to first_air_date from show data
        if first_air_date:
            self.log('date_resolution', 'info', 'ATTEMPT 3: Season data not available')
            self.log('date_resolution', 'warning', f'✓ FINAL FALLBACK: Using first_air_date: {first_air_date}')
            return (first_air_date, 'first_air_date')
        
        # All attempts failed
        self.log('date_resolution', 'error', '✗ FAILED: All date resolution attempts failed')
        return None
    
    def update_show_date(self, primary_topic_id: int, date: str) -> bool:
        """
        Update the date in primary_topics table
        
        Args:
            primary_topic_id: ID of the record to update
            date: Date string in YYYY-MM-DD format
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = f"""
                UPDATE {self.schema_name}.primary_topics
                SET date = %s
                WHERE primary_topic_id = %s
            """
            
            self.log('database', 'info', f'Executing UPDATE for primary_topic_id: {primary_topic_id}')
            self.log('database', 'debug', f'Query: {query}')
            self.log('database', 'debug', f'Values: date={date}, primary_topic_id={primary_topic_id}')
            
            self.cursor.execute(query, (date, primary_topic_id))
            self.conn.commit()
            
            self.log('database', 'info', f'✓ Successfully updated primary_topic_id {primary_topic_id} with date {date}')
            return True
            
        except Exception as e:
            self.log('database', 'error', f'✗ Failed to update primary_topic_id {primary_topic_id}: {str(e)}')
            self.log('errors', 'error', f'Database update failed for {primary_topic_id}: {str(e)}')
            self.conn.rollback()
            return False
    
    def fetch_shows(self) -> List[Tuple]:
        """
        Fetch shows from database
        
        Returns:
            List of tuples: (primary_topic_id, name, imdb_id)
        """
        try:
            if self.primary_topic_ids:
                self.log('main', 'info', f'TEST MODE: Processing {len(self.primary_topic_ids)} specific records')
                self.log('database', 'info', f'Fetching specific primary_topic_ids: {self.primary_topic_ids}')
                
                query = f"""
                    SELECT pt.primary_topic_id, pt.name, ts.source_id
                    FROM {self.schema_name}.primary_topics pt
                    JOIN {self.schema_name}.topic_sources ts 
                        ON pt.primary_topic_id = ts.primary_topic_id
                    WHERE pt.type = 'show' 
                        AND ts.source_name = 'imdb'
                        AND pt.primary_topic_id = ANY(%s)
                    ORDER BY pt.primary_topic_id
                """
                self.cursor.execute(query, (self.primary_topic_ids,))
            else:
                self.log('main', 'info', 'FULL MODE: Processing all show records')
                self.log('database', 'info', 'Fetching all shows with IMDB IDs')
                
                query = f"""
                    SELECT pt.primary_topic_id, pt.name, ts.source_id
                    FROM {self.schema_name}.primary_topics pt
                    JOIN {self.schema_name}.topic_sources ts 
                        ON pt.primary_topic_id = ts.primary_topic_id
                    WHERE pt.type = 'show' 
                        AND ts.source_name = 'imdb'
                    ORDER BY pt.primary_topic_id
                """
                self.cursor.execute(query)
            
            results = self.cursor.fetchall()
            self.log('main', 'info', f'✓ Fetched {len(results)} show records from database')
            self.log('database', 'info', f'Query returned {len(results)} records')
            
            return results
            
        except Exception as e:
            self.log('main', 'error', f'✗ Failed to fetch shows from database: {str(e)}')
            self.log('errors', 'error', f'Database query failed: {str(e)}')
            return []
    
    def process_show(self, primary_topic_id: int, name: str, imdb_id: str) -> bool:
        """
        Process a single show: convert IMDB to TMDB, get latest date, update DB
        
        Args:
            primary_topic_id: Primary topic ID
            name: Show name
            imdb_id: IMDB ID
            
        Returns:
            True if successful, False otherwise
        """
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', f'PROCESSING: ID={primary_topic_id}, Name="{name}"')
        self.log('main', 'info', f'IMDB ID: {imdb_id}')
        self.log('main', 'info', '=' * 80)
        
        # Parse show name
        parsed_name = self.parse_show_name(name)
        
        # Convert IMDB to TMDB
        tmdb_id = self.convert_imdb_to_tmdb(imdb_id)
        
        if not tmdb_id:
            self.log('main', 'warning', f'✗ SKIPPED: Could not convert IMDB ID to TMDB ID')
            self.stats['skipped'] += 1
            return False
        
        # Add small delay to respect rate limits
        time.sleep(0.25)
        
        # Get latest season date
        date_result = self.get_latest_season_date(tmdb_id, parsed_name)
        
        if not date_result:
            self.log('main', 'error', f'✗ FAILED: Could not determine date for show')
            self.stats['failed'] += 1
            return False
        
        date, source = date_result
        
        # Track which method was used
        if source == 'last_episode':
            self.stats['date_from_episode'] += 1
            self.log('main', 'info', f'Date source: Last episode air date')
        elif source == 'season_premiere':
            self.stats['date_from_season'] += 1
            self.log('main', 'info', f'Date source: Season premiere date')
        elif source == 'first_air_date':
            self.stats['date_from_first_air'] += 1
            self.log('main', 'info', f'Date source: First air date (fallback)')
        
        self.log('main', 'info', f'Resolved date: {date}')
        
        # Update database
        if self.update_show_date(primary_topic_id, date):
            self.log('main', 'info', f'✓ SUCCESS: Updated primary_topic_id {primary_topic_id} with date {date}')
            self.stats['successful'] += 1
            return True
        else:
            self.log('main', 'error', f'✗ FAILED: Database update failed')
            self.stats['failed'] += 1
            return False
    
    def print_summary(self):
        """Print and log summary statistics"""
        self.log('main', 'info', '')
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', 'EXECUTION SUMMARY')
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', f'Total shows processed: {self.stats["total"]}')
        self.log('main', 'info', f'✓ Successful updates: {self.stats["successful"]}')
        self.log('main', 'info', f'✗ Failed: {self.stats["failed"]}')
        self.log('main', 'info', f'⊘ Skipped: {self.stats["skipped"]}')
        self.log('main', 'info', '')
        self.log('main', 'info', 'Date Resolution Breakdown:')
        self.log('main', 'info', f'  - From last episode: {self.stats["date_from_episode"]}')
        self.log('main', 'info', f'  - From season premiere: {self.stats["date_from_season"]}')
        self.log('main', 'info', f'  - From first air date: {self.stats["date_from_first_air"]}')
        self.log('main', 'info', '')
        self.log('main', 'info', 'Log files created:')
        for log_name, log_path in self.log_files.items():
            self.log('main', 'info', f'  - {log_name}: {log_path}')
        self.log('main', 'info', '=' * 80)
    
    def run(self):
        """Main execution method"""
        start_time = datetime.now()
        
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', 'SHOW DATE UPDATER - EXECUTION STARTED')
        self.log('main', 'info', f'Start time: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', '')
        
        # Connect to database
        if not self.connect_database():
            self.log('main', 'error', 'Exiting due to database connection failure')
            return
        
        self.log('main', 'info', '')
        
        # Fetch shows
        shows = self.fetch_shows()
        
        if not shows:
            self.log('main', 'warning', 'No shows to process')
            self.close()
            return
        
        self.stats['total'] = len(shows)
        self.log('main', 'info', '')
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', 'STARTING SHOW PROCESSING')
        self.log('main', 'info', '=' * 80)
        self.log('main', 'info', '')
        
        # Process each show
        for idx, (primary_topic_id, name, imdb_id) in enumerate(shows, 1):
            self.log('main', 'info', f'Progress: {idx}/{self.stats["total"]}')
            self.process_show(primary_topic_id, name, imdb_id)
            self.log('main', 'info', '')
            
            # Add delay between shows to respect rate limits
            if idx < self.stats['total']:
                time.sleep(0.5)
        
        # Print summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.log('main', 'info', '')
        self.log('main', 'info', f'End time: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.log('main', 'info', f'Total duration: {duration}')
        self.print_summary()
        
        # Close connections
        self.close()
    
    def close(self):
        """Close database connection and cleanup"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        
        self.log('main', 'info', 'Database connection closed')
        self.log('main', 'info', 'Execution completed')


def main(primary_topic_ids: Optional[List[int]] = None):
    """
    Main function to run the show date updater
    
    Args:
        primary_topic_ids: Optional list of specific primary_topic_ids to process.
                          If None, processes all shows.
                          
    Example usage:
        # Process all shows
        main()
        
        # Process specific shows (test mode)
        main([123, 456, 789])
    """
    updater = ShowDateUpdater(primary_topic_ids)
    updater.run()


if __name__ == '__main__':
    # Test mode: Process specific shows
    # Uncomment and add IDs to test with specific shows
    # main([123, 456, 789])
    
    # Full mode: Process all shows
    main()