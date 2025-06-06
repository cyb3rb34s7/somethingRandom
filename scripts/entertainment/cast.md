Here's the final code adapted for PostgreSQL using the psycopg2 library with your TMDb Bearer token:

```python
import requests
import os
import time
import json
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API authorization
TMDB_BEARER_TOKEN = os.getenv('TMDB_BEARER_TOKEN')

# Database configuration for PostgreSQL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

class CastDataImporter:
    def __init__(self, tmdb_bearer_token=TMDB_BEARER_TOKEN):
        self.tmdb_bearer_token = tmdb_bearer_token
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.headers = {
            "Authorization": f"Bearer {self.tmdb_bearer_token}",
            "Content-Type": "application/json"
        }
        self.conn = None
        self.cursor = None
        
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
            return True
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            return False
    
    def close_db_connection(self):
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def create_cast_table(self):
        """Create the cast tables if they don't exist"""
        try:
            # Create cast_details table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cast_details (
                cast_id SERIAL PRIMARY KEY,
                primary_topic_id INTEGER REFERENCES primary_topic(primary_topic_id),
                name TEXT,
                character TEXT,
                tmdb_id INTEGER,
                imdb_id TEXT,
                gender INTEGER,
                birthday DATE,
                age INTEGER,
                place_of_birth TEXT,
                biography TEXT,
                popularity REAL,
                profile_path TEXT,
                known_for_department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create cast_images table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cast_images (
                image_id SERIAL PRIMARY KEY,
                cast_id INTEGER REFERENCES cast_details(cast_id) ON DELETE CASCADE,
                image_url TEXT
            )
            ''')
            
            # Create cast_alt_names table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cast_alt_names (
                alt_name_id SERIAL PRIMARY KEY,
                cast_id INTEGER REFERENCES cast_details(cast_id) ON DELETE CASCADE,
                alt_name TEXT
            )
            ''')
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_movies_and_shows(self):
        """Get movies and shows from primary_topic table"""
        try:
            self.cursor.execute('''
            SELECT pt.primary_topic_id, pt.name, ts.source_id, ts.source_name, ts.source_id_type
            FROM primary_topic pt
            JOIN topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
            WHERE pt.type IN ('movie', 'show')
            ''')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching movies and shows: {str(e)}")
            return []
    
    def calculate_age(self, birth_date_str):
        """Calculate age from birth date string"""
        if not birth_date_str:
            return None
            
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        except:
            return None
    
    def fetch_cast_from_tmdb(self, tmdb_id, primary_topic_id, cast_limit=6):
        """Fetch cast details from TMDb"""
        try:
            # Get movie credits (cast and crew)
            endpoint = f"{self.tmdb_base_url}/movie/{tmdb_id}/credits"
            response = requests.get(endpoint, headers=self.headers)
            
            # If movie endpoint fails, try TV show endpoint
            if response.status_code != 200:
                endpoint = f"{self.tmdb_base_url}/tv/{tmdb_id}/credits"
                response = requests.get(endpoint, headers=self.headers)
            
            response.raise_for_status()
            credits_data = response.json()
            
            if 'cast' not in credits_data or not credits_data['cast']:
                print(f"No cast information found for TMDb ID: {tmdb_id}")
                return []
                
            # Process cast data (limit to top 6 cast members)
            cast_details = []
            for actor in credits_data.get('cast', [])[:cast_limit]:
                # Get detailed person info for each cast member
                person_endpoint = f"{self.tmdb_base_url}/person/{actor['id']}"
                person_params = {"append_to_response": "external_ids,images"}
                person_response = requests.get(person_endpoint, headers=self.headers, params=person_params)
                
                if person_response.status_code != 200:
                    continue
                    
                person_data = person_response.json()
                
                # Extract external IDs
                external_ids = person_data.get('external_ids', {})
                imdb_id = external_ids.get('imdb_id')
                
                # Get profile images
                profile_images = []
                if 'profiles' in person_data.get('images', {}):
                    profile_images = [f"{self.image_base_url}{img['file_path']}" 
                                     for img in person_data['images']['profiles'][:5]]  # Limit to 5 images
                
                # Calculate age
                age = self.calculate_age(person_data.get('birthday'))
                
                cast_member = {
                    "primary_topic_id": primary_topic_id,
                    "name": person_data.get('name', actor.get('name')),
                    "character": actor.get('character'),
                    "tmdb_id": actor.get('id'),
                    "imdb_id": imdb_id,
                    "gender": person_data.get('gender'),
                    "birthday": person_data.get('birthday'),
                    "age": age,
                    "place_of_birth": person_data.get('place_of_birth'),
                    "biography": person_data.get('biography'),
                    "popularity": person_data.get('popularity'),
                    "profile_path": f"{self.image_base_url}{person_data.get('profile_path')}" if person_data.get('profile_path') else None,
                    "additional_images": profile_images,
                    "known_for_department": person_data.get('known_for_department'),
                    "also_known_as": person_data.get('also_known_as', [])
                }
                
                cast_details.append(cast_member)
                
                # Respect API rate limits
                time.sleep(0.25)
                
            return cast_details
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from TMDb: {str(e)}")
            return []
    
    def fetch_cast_from_imdb_id(self, imdb_id, primary_topic_id, cast_limit=6):
        """Convert IMDb ID to TMDb ID and fetch cast details"""
        try:
            # First find the TMDb ID using the IMDb ID
            find_endpoint = f"{self.tmdb_base_url}/find/{imdb_id}"
            params = {"external_source": "imdb_id"}
            response = requests.get(find_endpoint, headers=self.headers, params=params)
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
                print(f"No movie/show found with IMDb ID: {imdb_id}")
                return []
                
            # Now use the TMDb ID to fetch cast details
            return self.fetch_cast_from_tmdb(tmdb_id, primary_topic_id, cast_limit)
            
        except requests.exceptions.RequestException as e:
            print(f"Error converting IMDb ID to TMDb ID: {str(e)}")
            return []
    
    def insert_cast_data(self, cast_details):
        """Insert cast details into the database"""
        try:
            for cast_member in cast_details:
                # Convert birthday string to proper date format for PostgreSQL
                birthday = cast_member['birthday']
                
                # Insert into cast_details table
                self.cursor.execute('''
                INSERT INTO cast_details (
                    primary_topic_id, name, character, tmdb_id, imdb_id,
                    gender, birthday, age, place_of_birth, biography,
                    popularity, profile_path, known_for_department
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING cast_id
                ''', (
                    cast_member['primary_topic_id'],
                    cast_member['name'],
                    cast_member['character'],
                    cast_member['tmdb_id'],
                    cast_member['imdb_id'],
                    cast_member['gender'],
                    birthday,
                    cast_member['age'],
                    cast_member['place_of_birth'],
                    cast_member['biography'],
                    cast_member['popularity'],
                    cast_member['profile_path'],
                    cast_member['known_for_department']
                ))
                
                # Get the inserted cast_id
                cast_id = self.cursor.fetchone()[0]
                
                # Insert additional images
                for image_url in cast_member.get('additional_images', []):
                    self.cursor.execute('''
                    INSERT INTO cast_images (cast_id, image_url)
                    VALUES (%s, %s)
                    ''', (cast_id, image_url))
                
                # Insert alternative names
                for alt_name in cast_member.get('also_known_as', []):
                    self.cursor.execute('''
                    INSERT INTO cast_alt_names (cast_id, alt_name)
                    VALUES (%s, %s)
                    ''', (cast_id, alt_name))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting cast data: {str(e)}")
            self.conn.rollback()
            return False
    
    def process_all_movies_shows(self):
        """Process all movies and shows to fetch and store cast data"""
        if not self.connect_to_db():
            return False
            
        if not self.create_cast_table():
            self.close_db_connection()
            return False
            
        movies_shows = self.get_movies_and_shows()
        total_processed = 0
        
        for item in movies_shows:
            primary_topic_id, name, source_id, source_name, source_id_type = item
            print(f"Processing {name} (ID: {primary_topic_id})")
            
            cast_details = []
            
            # Check source type and fetch cast accordingly
            if source_name.lower() == 'tmdb' and source_id_type.lower() == 'tmdb_id':
                cast_details = self.fetch_cast_from_tmdb(source_id, primary_topic_id)
            elif source_name.lower() == 'imdb' and source_id_type.lower() == 'imdb_id':
                cast_details = self.fetch_cast_from_imdb_id(source_id, primary_topic_id)
            
            if cast_details:
                if self.insert_cast_data(cast_details):
                    total_processed += 1
                    print(f"Successfully processed {name} - added {len(cast_details)} cast members")
            
            # Respect API rate limits between movies/shows
            time.sleep(1)
        
        self.close_db_connection()
        print(f"Completed processing {total_processed} movies/shows")
        return True

# Execute the script
if __name__ == "__main__":
    importer = CastDataImporter()
    importer.process_all_movies_shows()
```

### Setup Instructions:

1. Install the required Python packages:
```bash
pip install requests python-dotenv psycopg2
```

2. Create a `.env` file with the following contents:
```
# TMDb API
TMDB_BEARER_TOKEN=your_bearer_token_here

# PostgreSQL Database
DB_HOST=your_postgresql_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_username
DB_PASSWORD=your_database_password
```

3. Run the script:
```bash
python cast_importer.py
```

### Key PostgreSQL-specific Changes:

1. Using `psycopg2` instead of `sqlite3` for database connectivity
2. Changed SQL syntax to use PostgreSQL's parameter style (`%s` instead of `?`)
3. Using `SERIAL` instead of `INTEGER PRIMARY KEY AUTOINCREMENT` for auto-incrementing IDs
4. Added proper referential integrity constraints with `REFERENCES` and `ON DELETE CASCADE`
5. Using PostgreSQL's native `DATE` type for birthday
6. Using `RETURNING cast_id` to get the ID of the newly inserted cast record
7. Proper connection string format for PostgreSQL

This script will connect to your PostgreSQL database, create the necessary tables if they don't exist, fetch movie/show information from your existing tables, retrieve cast details from TMDb using your Bearer token, and insert the data into the new cast tables.