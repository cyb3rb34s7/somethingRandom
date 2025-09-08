Looking at our finalized plan, I'll implement the Python code with the structure we discussed. Here are the code files:

psycopg2-binary==2.9.7
requests==2.31.0
python-dotenv==1.0.0

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password

# TMDB Configuration
TMDB_BEARER_TOKEN=your_tmdb_bearer_token

# Logging Configuration
ENABLE_FILE_LOGGING=true
LOG_LEVEL=INFO

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # TMDB Configuration
    TMDB_BEARER_TOKEN = os.getenv('TMDB_BEARER_TOKEN')
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    
    # Logging Configuration
    ENABLE_FILE_LOGGING = os.getenv('ENABLE_FILE_LOGGING', 'false').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # SSL Configuration
    SSL_VERIFY = False
    
    @classmethod
    def validate(cls):
        """Validate required environment variables"""
        required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'TMDB_BEARER_TOKEN']
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

import logging
import os
from datetime import datetime
from config.settings import Config

def setup_logger():
    """Setup logger with console and optional file logging"""
    
    # Create logs directory if it doesn't exist
    if Config.ENABLE_FILE_LOGGING:
        os.makedirs('logs', exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('metadata_fetcher')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if Config.ENABLE_FILE_LOGGING:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f'logs/metadata_fetcher_{timestamp}.log'
        
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"File logging enabled. Log file: {log_filename}")
    
    return logger

import psycopg2
import psycopg2.extras
from config.settings import Config
import logging

logger = logging.getLogger('metadata_fetcher')

class DatabaseManager:
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            return False
    
    def get_topic_data(self, primary_topic_id):
        """Get primary topic and source data"""
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
            SELECT 
                pt.name, 
                pt.type, 
                ts.source_id, 
                ts.source_name, 
                ts.source_id_type
            FROM bingeplus_external.primary_topics pt
            LEFT JOIN bingeplus_external.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
            WHERE pt.primary_topic_id = %s
            AND (ts.source_name IN ('tmdb', 'imdb') OR ts.source_name IS NULL)
            AND (ts.source_id_type IN ('tmdb_id', 'imdb_id') OR ts.source_id_type IS NULL)
            """
            
            cursor.execute(query, (primary_topic_id,))
            results = cursor.fetchall()
            
            if not results:
                logger.warning(f"No data found for primary_topic_id: {primary_topic_id}")
                return None
            
            # Process results
            topic_data = {
                'name': results[0]['name'],
                'type': results[0]['type'],
                'tmdb_id': None,
                'imdb_id': None
            }
            
            for row in results:
                if row['source_name'] == 'tmdb' and row['source_id_type'] == 'tmdb_id':
                    topic_data['tmdb_id'] = row['source_id']
                elif row['source_name'] == 'imdb' and row['source_id_type'] == 'imdb_id':
                    topic_data['imdb_id'] = row['source_id']
            
            logger.info(f"Retrieved topic data for ID {primary_topic_id}: {topic_data['name']}")
            return topic_data
            
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

import requests
import urllib3
from config.settings import Config
import logging

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('metadata_fetcher')

class TMDBService:
    def __init__(self):
        self.base_url = Config.TMDB_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {Config.TMDB_BEARER_TOKEN}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint):
        """Make API request to TMDB"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.info(f"Making TMDB API call: {url}")
            
            response = requests.get(url, headers=self.headers, verify=Config.SSL_VERIFY)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"TMDB API request failed: {str(e)}")
            return None
    
    def find_by_imdb_id(self, imdb_id):
        """Find TMDB content using IMDB ID"""
        endpoint = f"/find/{imdb_id}?external_source=imdb_id"
        result = self._make_request(endpoint)
        
        if result:
            # Check for movie or TV results
            if result.get('movie_results'):
                return result['movie_results'][0]['id'], 'movie'
            elif result.get('tv_results'):
                return result['tv_results'][0]['id'], 'tv'
        
        return None, None
    
    def search_content(self, name, content_type):
        """Search for content by name and type"""
        search_type = 'movie' if content_type == 'movie' else 'tv'
        endpoint = f"/search/{search_type}?query={name}"
        
        result = self._make_request(endpoint)
        
        if result and result.get('results'):
            first_result = result['results'][0]
            return first_result['id'], search_type
        
        return None, None
    
    def get_basic_info(self, tmdb_id, content_type):
        """Get basic movie/TV info"""
        endpoint = f"/{content_type}/{tmdb_id}"
        return self._make_request(endpoint)
    
    def get_credits(self, tmdb_id, content_type):
        """Get cast and crew information"""
        endpoint = f"/{content_type}/{tmdb_id}/credits"
        return self._make_request(endpoint)
    
    def get_keywords(self, tmdb_id, content_type):
        """Get keywords"""
        endpoint = f"/{content_type}/{tmdb_id}/keywords"
        return self._make_request(endpoint)
    
    def get_external_ids(self, tmdb_id, content_type):
        """Get external IDs including IMDB"""
        endpoint = f"/{content_type}/{tmdb_id}/external_ids"
        return self._make_request(endpoint)
    
    def get_metadata(self, topic_data):
        """Main method to fetch all metadata"""
        try:
            tmdb_id = topic_data.get('tmdb_id')
            imdb_id = topic_data.get('imdb_id')
            name = topic_data.get('name')
            content_type = topic_data.get('type')
            
            # Map content type
            api_type = 'movie' if content_type == 'movie' else 'tv'
            
            # Resolve TMDB ID
            if tmdb_id:
                logger.info(f"Using existing TMDB ID: {tmdb_id}")
                final_tmdb_id = tmdb_id
                final_type = api_type
            elif imdb_id:
                logger.info(f"Finding TMDB ID using IMDB ID: {imdb_id}")
                final_tmdb_id, final_type = self.find_by_imdb_id(imdb_id)
            else:
                logger.info(f"Searching for content: {name}")
                final_tmdb_id, final_type = self.search_content(name, content_type)
            
            if not final_tmdb_id:
                logger.error("Could not resolve TMDB ID")
                return None
            
            # Fetch all data
            basic_info = self.get_basic_info(final_tmdb_id, final_type)
            credits = self.get_credits(final_tmdb_id, final_type)
            keywords = self.get_keywords(final_tmdb_id, final_type)
            external_ids = self.get_external_ids(final_tmdb_id, final_type)
            
            # Build response
            return self._build_response(basic_info, credits, keywords, external_ids, final_type)
            
        except Exception as e:
            logger.error(f"Error fetching TMDB metadata: {str(e)}")
            return None
    
    def _build_response(self, basic_info, credits, keywords, external_ids, content_type):
        """Build the final JSON response"""
        if not basic_info:
            return None
        
        response = {}
        
        # Basic information
        response['title'] = basic_info.get('title') or basic_info.get('name', '')
        response['description'] = basic_info.get('overview', '')
        response['program_type'] = 'movie' if content_type == 'movie' else 'show'
        response['plot'] = basic_info.get('overview', '')
        
        # Release date
        release_date = basic_info.get('release_date') or basic_info.get('first_air_date', '')
        response['releasedate'] = release_date
        
        # Genres
        genres = [genre['name'] for genre in basic_info.get('genres', [])]
        response['genre'] = genres
        
        # Ratings
        response['tmdbRating'] = basic_info.get('vote_average', 0)
        response['tmdbVoteCount'] = basic_info.get('vote_count', 0)
        
        # Keywords
        if keywords:
            keyword_list = keywords.get('keywords', []) or keywords.get('results', [])
            response['keywords'] = [kw['name'] for kw in keyword_list]
        else:
            response['keywords'] = []
        
        # Country origin
        countries = basic_info.get('production_countries', []) or basic_info.get('origin_country', [])
        if countries:
            if isinstance(countries[0], dict):
                response['countryOrigin'] = countries[0].get('name', '')
            else:
                response['countryOrigin'] = countries[0]
        else:
            response['countryOrigin'] = ''
        
        # Cast and crew
        cast_list = []
        if credits:
            # Add main cast
            for person in credits.get('cast', [])[:10]:  # Limit to top 10 cast
                cast_list.append({
                    'castName': person.get('name', ''),
                    'castRole': 'actor'
                })
            
            # Add crew (director, writer, producer)
            crew_roles = ['Director', 'Writer', 'Producer', 'Executive Producer']
            for person in credits.get('crew', []):
                if person.get('job') in crew_roles:
                    role = person.get('job', '').lower()
                    cast_list.append({
                        'castName': person.get('name', ''),
                        'castRole': role
                    })
        
        response['cast'] = cast_list
        
        # Additional fields
        response['runtime'] = basic_info.get('runtime') or basic_info.get('episode_run_time', [None])[0]
        response['status'] = basic_info.get('status', '')
        response['originalLanguage'] = basic_info.get('original_language', '')
        response['popularity'] = basic_info.get('popularity', 0)
        response['budget'] = basic_info.get('budget', 0)
        response['revenue'] = basic_info.get('revenue', 0)
        response['tagline'] = basic_info.get('tagline', '')
        response['homepage'] = basic_info.get('homepage', '')
        response['posterPath'] = basic_info.get('poster_path', '')
        response['backdropPath'] = basic_info.get('backdrop_path', '')
        response['adult'] = basic_info.get('adult', False)
        response['tmdbId'] = basic_info.get('id')
        
        # External IDs
        if external_ids:
            response['imdbId'] = external_ids.get('imdb_id', '')
        else:
            response['imdbId'] = ''
        
        # Production companies
        companies = [company['name'] for company in basic_info.get('production_companies', [])]
        response['productionCompanies'] = companies
        
        # Spoken languages
        languages = [lang.get('english_name', lang.get('name', '')) for lang in basic_info.get('spoken_languages', [])]
        response['spokenLanguages'] = languages
        
        # TV specific fields
        if content_type == 'tv':
            response['numberOfSeasons'] = basic_info.get('number_of_seasons')
            response['numberOfEpisodes'] = basic_info.get('number_of_episodes')
        else:
            response['numberOfSeasons'] = None
            response['numberOfEpisodes'] = None
        
        return response

import json
import sys
from config.settings import Config
from utils.logger import setup_logger
from database.db_manager import DatabaseManager
from services.tmdb_service import TMDBService

def fetch_metadata(primary_topic_id):
    """Main function to fetch metadata for given primary_topic_id"""
    
    # Setup logger
    logger = setup_logger()
    logger.info(f"Starting metadata fetch for primary_topic_id: {primary_topic_id}")
    
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        if not db_manager.connect():
            error_response = {
                "error": "Database connection failed"
            }
            logger.error("Database connection failed")
            return error_response
        
        # Get topic data from database
        topic_data = db_manager.get_topic_data(primary_topic_id)
        if not topic_data:
            error_response = {
                "error": "Content not found in database",
                "primary_topic_id": primary_topic_id
            }
            logger.error(f"No data found for primary_topic_id: {primary_topic_id}")
            db_manager.close()
            return error_response
        
        # Initialize TMDB service
        tmdb_service = TMDBService()
        
        # Fetch metadata from TMDB
        tmdb_data = tmdb_service.get_metadata(topic_data)
        
        if not tmdb_data:
            error_response = {
                "error": "Content not found in TMDB",
                "primary_topic_info": {
                    "name": topic_data['name'],
                    "type": topic_data['type']
                }
            }
            logger.error("Failed to fetch TMDB metadata")
            db_manager.close()
            return error_response
        
        # Build final response
        response = {
            "tmdb": tmdb_data
        }
        
        logger.info(f"Successfully fetched metadata for: {tmdb_data.get('title', 'Unknown')}")
        db_manager.close()
        
        return response
        
    except ValueError as e:
        error_response = {
            "error": "Configuration error",
            "message": str(e)
        }
        logger.error(f"Configuration error: {str(e)}")
        return error_response
        
    except Exception as e:
        error_response = {
            "error": "Unexpected error occurred",
            "message": str(e)
        }
        logger.error(f"Unexpected error: {str(e)}")
        return error_response

def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: python main.py <primary_topic_id>")
        sys.exit(1)
    
    try:
        primary_topic_id = int(sys.argv[1])
    except ValueError:
        print("Error: primary_topic_id must be an integer")
        sys.exit(1)
    
    # Fetch metadata
    result = fetch_metadata(primary_topic_id)
    
    # Print JSON response
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

# Placeholder for future IMDB service implementation

class IMDBService:
    def __init__(self):
        pass
    
    def get_metadata(self, topic_data):
        """Future implementation for IMDB metadata fetching"""
        pass

# Placeholder for future UMD service implementation

class UMDService:
    def __init__(self):
        pass
    
    def get_metadata(self, topic_data):
        """Future implementation for UMD metadata fetching"""
        pass

Here's the complete implementation following our finalized plan:

## Project Structure Created:
- **main.py** - Entry point that takes primary_topic_id as input
- **config/settings.py** - Environment configuration using .env
- **utils/logger.py** - Logging setup with optional file logging
- **database/db_manager.py** - Database operations for bingeplus_external schema
- **services/tmdb_service.py** - TMDB API integration
- **services/imdb_service.py** - Placeholder for future IMDB implementation
- **services/umd_service.py** - Placeholder for future UMD implementation

## Key Features Implemented:

1. **Environment Configuration**: Uses .env file for all configurations
2. **Logging**: Structured logging with optional file saving (controlled by ENABLE_FILE_LOGGING env var)
3. **SSL Warnings Disabled**: urllib3 warnings disabled as requested
4. **Database Schema**: Uses bingeplus_external schema in queries
5. **Extensible Structure**: Easy to add IMDB and UMD services later
6. **Error Handling**: Comprehensive error handling with proper logging

## Usage:

1. Create `.env` file based on `.env.example`
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python main.py <primary_topic_id>`

The code follows the exact flow we discussed and maintains the JSON structure you specified. The architecture makes it easy to extend with IMDB and UMD services later by implementing similar service classes.