#!/usr/bin/env python3
"""
Date Only Enrichment Script
One-time script to fill dates in primary_topics table
"""

import psycopg2
import requests
import time
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class MovieShow:
    primary_topic_id: int
    name: str
    type: str
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    source_name: Optional[str] = None

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
    
    def find_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Find TMDB data using IMDB ID"""
        try:
            if not imdb_id.startswith('tt'):
                imdb_id = f"tt{imdb_id}"
            
            url = f"{self.base_url}/find/{imdb_id}"
            params = {"external_source": "imdb_id"}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('movie_results'):
                    return {'type': 'movie', 'id': data['movie_results'][0]['id']}
                elif data.get('tv_results'):
                    return {'type': 'tv', 'id': data['tv_results'][0]['id']}
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                return self.find_by_imdb_id(imdb_id)
            
            return None
        except:
            return None
    
    def search_by_name_and_type(self, name: str, media_type: str) -> Optional[Dict]:
        """Search TMDB by name and type"""
        try:
            if media_type.lower() == 'movie':
                endpoint = 'search/movie'
            else:
                endpoint = 'search/tv'
            
            url = f"{self.base_url}/{endpoint}"
            params = {"query": name, "include_adult": "false", "language": "en-US", "page": 1}
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    return {
                        'type': 'movie' if media_type.lower() == 'movie' else 'tv',
                        'id': results[0]['id']
                    }
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                return self.search_by_name_and_type(name, media_type)
            
            return None
        except:
            return None
    
    def get_release_date(self, tmdb_id: str, media_type: str) -> Optional[str]:
        """Get release date from TMDB"""
        try:
            if media_type == 'movie':
                url = f"{self.base_url}/movie/{tmdb_id}"
                date_field = 'release_date'
            else:
                url = f"{self.base_url}/tv/{tmdb_id}"
                date_field = 'first_air_date'
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return data.get(date_field, '').strip()
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                return self.get_release_date(tmdb_id, media_type)
            
            return None
        except:
            return None

class DatabaseManager:
    def __init__(self, connection_params: Dict[str, str]):
        self.connection_params = connection_params
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        self.conn = psycopg2.connect(**self.connection_params)
        self.cursor = self.conn.cursor()
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_items_missing_dates(self) -> List[MovieShow]:
        """Get items that don't have dates"""
        query = """
        SELECT DISTINCT 
            pt.primary_topic_id,
            pt.name,
            pt.type,
            ts.source_id,
            ts.source_name
        FROM bingeplus_external.primary_topics pt
        JOIN bingeplus_external.topic_sources ts ON pt.primary_topic_id = ts.primary_topic_id
        WHERE (pt.date IS NULL OR pt.date = '')
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
                    source_name=row[4]
                )
                
                if row[4] == 'tmdb':
                    item.tmdb_id = row[3]
                elif row[4] == 'imdb':
                    item.imdb_id = row[3]
                
                items.append(item)
            
            return items
        except Exception as e:
            print(f"Error fetching items: {e}")
            return []
    
    def update_date(self, primary_topic_id: int, release_date: str):
        """Update date in primary_topics table"""
        query = """
        UPDATE bingeplus_external.primary_topics 
        SET date = %s, updated_at = CURRENT_TIMESTAMP
        WHERE primary_topic_id = %s
        """
        self.cursor.execute(query, (release_date, primary_topic_id))
    
    def commit(self):
        """Commit transaction"""
        self.conn.commit()

class DateEnricher:
    def __init__(self, db_manager: DatabaseManager, tmdb_client: TMDBClient):
        self.db_manager = db_manager
        self.tmdb_client = tmdb_client
        self.successful = 0
        self.failed = 0
    
    def process_item(self, item: MovieShow) -> bool:
        """Process a single item for date"""
        try:
            print(f"Processing: {item.name} (ID: {item.primary_topic_id}, Source: {item.source_name})")
            
            tmdb_id = None
            media_type = 'movie' if item.type.lower() == 'movie' else 'tv'
            
            # Get TMDB ID based on source
            if item.source_name == 'tmdb' and item.tmdb_id:
                tmdb_id = item.tmdb_id
            elif item.source_name == 'imdb' and item.imdb_id:
                find_result = self.tmdb_client.find_by_imdb_id(item.imdb_id)
                if find_result:
                    tmdb_id = str(find_result['id'])
                    media_type = find_result['type']
            else:
                search_result = self.tmdb_client.search_by_name_and_type(item.name, item.type)
                if search_result:
                    tmdb_id = str(search_result['id'])
                    media_type = search_result['type']
            
            if not tmdb_id:
                print(f"  ❌ Could not find TMDB ID")
                return False
            
            # Get release date
            release_date = self.tmdb_client.get_release_date(tmdb_id, media_type)
            
            if not release_date:
                print(f"  ❌ No release date found")
                return False
            
            # Update database
            self.db_manager.update_date(item.primary_topic_id, release_date)
            print(f"  ✅ Updated date: {release_date}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    def run_enrichment(self):
        """Run the date enrichment process"""
        try:
            self.db_manager.connect()
            
            items = self.db_manager.get_items_missing_dates()
            
            if not items:
                print("No items missing dates")
                return
            
            print(f"Found {len(items)} items missing dates")
            
            for i, item in enumerate(items, 1):
                if self.process_item(item):
                    self.successful += 1
                else:
                    self.failed += 1
                
                # Commit every 10 items
                if i % 10 == 0:
                    self.db_manager.commit()
                    print(f"Progress: {i}/{len(items)} - Success: {self.successful}, Failed: {self.failed}")
                
                # Rate limiting
                time.sleep(0.25)
            
            # Final commit
            self.db_manager.commit()
            
            print(f"\nCompleted! Success: {self.successful}, Failed: {self.failed}")
            
        except Exception as e:
            print(f"Error in enrichment process: {e}")
        finally:
            self.db_manager.disconnect()

def main():
    """Main function"""
    # Validate environment variables
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'TMDB_BEARER_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing environment variables: {', '.join(missing_vars)}")
        return
    
    # Configuration
    DB_CONFIG = {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': os.getenv('DB_PORT')
    }
    
    TMDB_TOKEN = os.getenv('TMDB_BEARER_TOKEN')
    
    # Initialize components
    db_manager = DatabaseManager(DB_CONFIG)
    tmdb_client = TMDBClient(TMDB_TOKEN)
    enricher = DateEnricher(db_manager, tmdb_client)
    
    print("Starting date enrichment process...")
    enricher.run_enrichment()

if __name__ == "__main__":
    main()