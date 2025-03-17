"""
Module for fetching trending sports topics from Google Trends and YouTube Trending.
"""

import json
import requests
from typing import List, Dict, Any
from pytrends.request import TrendReq

class TrendingFetcher:
    """Fetches trending sports topics from Google Trends and YouTube."""
    
    def __init__(self, youtube_api_key: str, region: str = "US", max_results: int = 20):
        """Initialize the TrendingFetcher with API keys and settings."""
        self.youtube_api_key = youtube_api_key
        self.region = region
        self.max_results = max_results
        self.pytrends = TrendReq(hl='en-US', tz=360)
    
    def fetch_google_trends(self) -> List[Dict[str, str]]:
        """Fetch trending sports topics from Google Trends."""
        # Get trending searches for the specified region
        trending_searches = self.pytrends.trending_searches(pn=self.region)
        trending_searches_list = trending_searches[0].tolist()
        
        # Filter for sports-related topics
        sports_keywords = ['nba', 'nfl', 'mlb', 'soccer', 'football', 'basketball', 
                          'tennis', 'golf', 'hockey', 'baseball', 'ufc', 'boxing']
        
        sports_topics = []
        for topic in trending_searches_list:
            # Simple check if the topic contains any sports keywords
            if any(keyword in topic.lower() for keyword in sports_keywords):
                topic_type = "sporting_event" if any(event in topic.lower() for event in 
                            ['game', 'match', 'tournament', 'championship', 'final']) else "sports_personality"
                sports_topics.append({
                    "type": topic_type,
                    "primary_topic": topic
                })
        
        return sports_topics
    
    def fetch_youtube_trends(self) -> List[Dict[str, str]]:
        """Fetch trending sports videos from YouTube."""
        api_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "videoCategoryId": "17",  # Sports category ID
            "regionCode": self.region,
            "maxResults": 25,  # Reasonable default to find sports content
            "key": self.youtube_api_key
        }
        
        response = requests.get(api_url, params=params)
        if response.status_code != 200:
            print(f"YouTube API error: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        
        # Extract video titles and classify them
        sports_topics = []
        for item in data.get('items', []):
            title = item['snippet']['title']
            
            # Simple classification based on title keywords
            topic_type = "sporting_event" if any(event in title.lower() for event in 
                        ['game', 'match', 'tournament', 'championship', 'final']) else "sports_personality"
            
            sports_topics.append({
                "type": topic_type,
                "primary_topic": title
            })
            
        return sports_topics
    
    def fetch_trending_topics(self) -> List[Dict[str, str]]:
        """Fetch and combine trending sports topics from all sources."""
        # Get topics from both sources
        google_topics = self.fetch_google_trends()
        youtube_topics = self.fetch_youtube_trends()
        
        # Combine and remove duplicates
        all_topics = google_topics + youtube_topics
        unique_topics = []
        seen_topics = set()
        
        for topic in all_topics:
            topic_name = topic["primary_topic"].lower()
            if topic_name not in seen_topics:
                seen_topics.add(topic_name)
                unique_topics.append(topic)
        
        # Return up to max_results topics
        return unique_topics[:self.max_results]

# Example usage
if __name__ == "__main__":
    fetcher = TrendingFetcher(youtube_api_key="YOUR_YOUTUBE_API_KEY")
    trending_topics = fetcher.fetch_trending_topics()
    print(json.dumps(trending_topics, indent=2))