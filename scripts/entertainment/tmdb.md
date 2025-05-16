I'd be happy to write a Python script to help you fetch movie cast details using TMDB or IMDb IDs. The TMDb API is generally easier to work with as it has better documentation and doesn't require scraping. Let's create a comprehensive script that can fetch cast details from both sources.

Here's a Python script that will allow you to fetch cast details from TMDb and IMDb:

```python
import requests
import os
import time
import json
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys - store these in a .env file for security
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
IMDB_API_KEY = os.getenv('IMDB_API_KEY')  # For certain IMDb API services if available

class MovieCastFetcher:
    def __init__(self, tmdb_api_key=TMDB_API_KEY, imdb_api_key=IMDB_API_KEY):
        self.tmdb_api_key = tmdb_api_key
        self.imdb_api_key = imdb_api_key
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        
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
    
    def fetch_from_tmdb_by_tmdb_id(self, tmdb_id):
        """Fetch cast details using TMDb ID"""
        try:
            # Get movie credits (cast and crew)
            endpoint = f"{self.tmdb_base_url}/movie/{tmdb_id}/credits"
            params = {"api_key": self.tmdb_api_key, "language": "en-US"}
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            
            credits_data = response.json()
            
            if 'cast' not in credits_data:
                return {"error": "No cast information found", "tmdb_id": tmdb_id}
                
            # Process cast data
            cast_details = []
            for actor in credits_data.get('cast', []):
                # Get detailed person info for each cast member
                person_endpoint = f"{self.tmdb_base_url}/person/{actor['id']}"
                person_params = {"api_key": self.tmdb_api_key, "language": "en-US", "append_to_response": "external_ids,images"}
                person_response = requests.get(person_endpoint, params=person_params)
                
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
                    "also_known_as": person_data.get('also_known_as')
                }
                
                cast_details.append(cast_member)
                
                # Respect API rate limits
                time.sleep(0.25)
                
            return {"cast": cast_details, "tmdb_id": tmdb_id}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching data from TMDb: {str(e)}", "tmdb_id": tmdb_id}
    
    def fetch_from_tmdb_by_imdb_id(self, imdb_id):
        """Convert IMDb ID to TMDb ID and fetch cast details"""
        try:
            # First find the TMDb ID using the IMDb ID
            find_endpoint = f"{self.tmdb_base_url}/find/{imdb_id}"
            params = {"api_key": self.tmdb_api_key, "language": "en-US", "external_source": "imdb_id"}
            response = requests.get(find_endpoint, params=params)
            response.raise_for_status()
            
            find_data = response.json()
            
            # Check if we found a movie match
            movie_results = find_data.get('movie_results', [])
            if not movie_results:
                return {"error": f"No movie found with IMDb ID: {imdb_id}"}
                
            tmdb_id = movie_results[0]['id']
            
            # Now use the TMDb ID to fetch cast details
            return self.fetch_from_tmdb_by_tmdb_id(tmdb_id)
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Error converting IMDb ID to TMDb ID: {str(e)}", "imdb_id": imdb_id}
    
    def save_to_json(self, data, filename):
        """Save data to a JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Data saved to {filename}")

    def fetch_cast(self, movie_id, id_type="tmdb"):
        """Main function to fetch cast details"""
        if id_type.lower() == "tmdb":
            result = self.fetch_from_tmdb_by_tmdb_id(movie_id)
        elif id_type.lower() == "imdb":
            result = self.fetch_from_tmdb_by_imdb_id(movie_id)
        else:
            return {"error": "Invalid ID type. Use 'tmdb' or 'imdb'."}
        
        # Save the result to a JSON file
        if 'error' not in result:
            filename = f"cast_{movie_id}_{id_type}.json"
            self.save_to_json(result, filename)
        
        return result

# Example usage
if __name__ == "__main__":
    fetcher = MovieCastFetcher()
    
    # Example TMDb ID: 550 (Fight Club)
    tmdb_result = fetcher.fetch_cast("550", "tmdb")
    
    # Example IMDb ID: tt0137523 (Fight Club)
    imdb_result = fetcher.fetch_cast("tt0137523", "imdb")
    
    # Process multiple IDs
    movie_ids = [
        {"id": "550", "type": "tmdb"},
        {"id": "tt0137523", "type": "imdb"},
        # Add more movies as needed
    ]
    
    results = {}
    for movie in movie_ids:
        movie_id = movie["id"]
        id_type = movie["type"]
        print(f"Fetching cast for {id_type} ID: {movie_id}")
        results[movie_id] = fetcher.fetch_cast(movie_id, id_type)
        time.sleep(1)  # Respect API rate limits
    
    # Save all results to a single JSON file
    fetcher.save_to_json(results, "all_movie_casts.json")
```

Would you like me to explain the code or would you like additional functionality added to the script?