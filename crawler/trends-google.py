"""
Module for fetching trending sports topics from Google Trends.
"""

import json
from pytrends.request import TrendReq
from typing import List, Dict

class TrendingFetcher:
    """Fetches trending sports topics from Google Trends."""
    
    def __init__(self, region: str = "US", max_results: int = 20):
        """Initialize the TrendingFetcher."""
        self.region = region
        self.max_results = max_results
        self.pytrends = TrendReq(hl='en-US', tz=360)
        
        # Sports keywords to filter trending topics
        self.sports_keywords = [
            'nba', 'nfl', 'mlb', 'nhl', 'soccer', 'football', 'basketball', 
            'tennis', 'golf', 'hockey', 'baseball', 'ufc', 'boxing',
            'cricket', 'olympics', 'wrestling', 'formula 1', 'f1',
            'premier league', 'la liga', 'bundesliga', 'serie a'
        ]
        
        # Event keywords to classify topics
        self.event_keywords = [
            'game', 'match', 'tournament', 'championship', 'final',
            'series', 'cup', 'open', 'grand prix', 'playoffs'
        ]
    
    def fetch_trending_topics(self) -> List[Dict[str, str]]:
        """
        Fetch trending sports topics from Google Trends.
        Returns list of dicts with 'type' and 'primary_topic'.
        """
        # Get trending searches for the specified region
        trending_searches = self.pytrends.trending_searches(pn=self.region)
        
        # Convert to list
        trending_searches_list = trending_searches[0].tolist()
        
        # Filter and classify sports topics
        sports_topics = []
        for topic in trending_searches_list:
            topic_lower = topic.lower()
            
            # Check if topic is sports-related
            if any(keyword in topic_lower for keyword in self.sports_keywords):
                # Classify as event or personality
                if any(event in topic_lower for event in self.event_keywords):
                    topic_type = "sporting_event"
                else:
                    topic_type = "sports_personality"
                
                sports_topics.append({
                    "type": topic_type,
                    "primary_topic": topic
                })
                
                # Stop once we reach max_results
                if len(sports_topics) >= self.max_results:
                    break
        
        return sports_topics

# Example usage
if __name__ == "__main__":
    fetcher = TrendingFetcher()
    trending_topics = fetcher.fetch_trending_topics()
    print(json.dumps(trending_topics, indent=2))