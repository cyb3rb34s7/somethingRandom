import pandas as pd
from pytrends.request import TrendReq
import json
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_trending_sports() -> List[str]:
    """
    Fetch trending sports topics from Google Trends.
    
    Returns:
        List[str]: A list of trending sports topics.
    """
    # Initialize PyTrends
    try:
        pytrend = TrendReq(hl='en-US', tz=300)
        logger.info("Successfully connected to Google Trends API")
    except Exception as e:
        logger.error(f"Failed to connect to Google Trends API: {e}")
        return fallback_sports_topics()
    
    try:
        # Get trending searches for US
        trending_df = pytrend.trending_searches(pn='united_states')
        trending_topics = trending_df[0].tolist()
        logger.info(f"Retrieved {len(trending_topics)} trending topics")
        
        # Define sports-related keywords for filtering
        sports_keywords = [
            'football', 'soccer', 'basketball', 'tennis', 'baseball', 
            'golf', 'cricket', 'rugby', 'volleyball', 'hockey',
            'nfl', 'nba', 'mlb', 'nhl', 'ufc', 'wwe', 
            'olympics', 'world cup', 'championship', 'tournament',
            'match', 'game', 'player', 'team', 'athlete', 'league'
        ]
        
        # Filter for sports-related topics
        sports_topics = []
        for topic in trending_topics:
            if any(keyword.lower() in topic.lower() for keyword in sports_keywords):
                sports_topics.append(topic)
        
        logger.info(f"Filtered to {len(sports_topics)} sports-related topics")
        
        # If we don't find any sports topics, use fallback
        if not sports_topics:
            logger.warning("No sports-related topics found in trending searches, using fallback")
            sports_topics = fallback_sports_topics()
        
        return sports_topics
    
    except Exception as e:
        logger.error(f"Error fetching trending sports: {e}")
        return fallback_sports_topics()

def fallback_sports_topics() -> List[str]:
    """
    Fallback method for when trending searches don't contain sports.
    
    Returns:
        List[str]: A list of predefined sports topics.
    """
    logger.info("Using fallback sports topics")
    # List of popular sports personalities and events
    sports_terms = [
        'NFL', 'NBA', 'MLB', 'NHL', 'UFC', 
        'LeBron James', 'Cristiano Ronaldo', 'Tom Brady', 'Serena Williams',
        'Soccer', 'Basketball', 'Baseball', 'Tennis', 'Golf'
    ]
    
    return sports_terms[:10]  # Limit to top 10

def classify_topic(topic: str) -> str:
    """
    Classify a topic as a sports personality or sporting event.
    
    Args:
        topic (str): The topic to classify.
        
    Returns:
        str: Either "sports_personality" or "sporting_event".
    """
    # Names of well-known sports leagues and events
    event_keywords = [
        'nfl', 'nba', 'mlb', 'nhl', 'ufc', 'wwe', 
        'olympics', 'world cup', 'championship', 'tournament',
        'open', 'series', 'cup', 'league', 'grand prix', 'game', 'match'
    ]
    
    # Check if it's an event
    if any(keyword.lower() in topic.lower() for keyword in event_keywords):
        return "sporting_event"
    
    # If not an event, assume it's a personality
    return "sports_personality"

def generate_youtube_queries(topic: str, topic_type: str) -> List[Dict[str, Any]]:
    """
    Generate YouTube queries based on topic type.
    
    Args:
        topic (str): The topic to generate queries for.
        topic_type (str): The type of the topic.
        
    Returns:
        List[Dict[str, Any]]: A list of structured query dictionaries.
    """
    queries = []
    
    if topic_type == "sports_personality":
        subcategories = [
            "Highlights", 
            "Best Goals/Plays", 
            "Training Drills", 
            "Funny Moments", 
            "Behind the Scenes"
        ]
    else:  # sporting_event
        subcategories = [
            "Highlights", 
            "Best Moments", 
            "Trophy Ceremony", 
            "Match Analysis", 
            "Game-Winning Play"
        ]
    
    for subcategory in subcategories:
        query = {
            "subcategory": subcategory,
            "query_term": f"{topic} {subcategory}",
            "maxResults": 8,
            "filters": [
                {"name": "videoType", "values": ["any"]},
                {"name": "region", "values": ["US"]}
            ]
        }
        queries.append(query)
    
    return queries

def get_trending_sports_json() -> str:
    """
    Fetch trending sports topics and format as JSON.
    
    Returns:
        str: A JSON string containing structured data.
    """
    sports_topics = fetch_trending_sports()
    
    output = []
    for topic in sports_topics:
        topic_type = classify_topic(topic)
        youtube_queries = generate_youtube_queries(topic, topic_type)
        
        topic_data = {
            "type": topic_type,
            "primary_topic": topic,
            "youtube_queries": youtube_queries
        }
        
        output.append(topic_data)
    
    return json.dumps(output, indent=4)

if __name__ == "__main__":
    try:
        trending_sports_json = get_trending_sports_json()
        print(trending_sports_json)
        
        # Save to file
        with open('trending_sports.json', 'w') as f:
            f.write(trending_sports_json)
        logger.info("Successfully saved trending sports data to 'trending_sports.json'")
    except Exception as e:
        logger.error(f"An error occurred in the main execution: {e}")
