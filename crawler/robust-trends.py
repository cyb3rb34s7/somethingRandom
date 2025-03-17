"""
trending_fetcher.py - Module for fetching trending sports topics from Google Trends.

This module handles:
1. Connection to Google Trends via PyTrends
2. Fetching trending sports topics with proper categorization
3. Error handling and retry logic
4. Structuring the output as JSON for the query generator
"""

import json
import time
import random
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from pytrends.request import TrendReq
import spacy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load spaCy model for entity recognition - with fallback options
try:
    # First try to load the model directly
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("SpaCy model not found, attempting to download...")
    try:
        # Try to download using spaCy's CLI
        import subprocess
        result = subprocess.run(
            ["python", "-m", "spacy", "download", "en_core_web_sm"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.warning(f"Automatic download failed: {result.stderr}")
            logger.info("Trying alternative download method...")
            # Try pip install as alternative
            subprocess.run(
                ["pip", "install", "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.5.0/en_core_web_sm-3.5.0-py3-none-any.whl"],
                check=False
            )
        
        # Try loading again
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        logger.warning(f"Could not download spaCy model: {str(e)}")
        logger.info("Falling back to using a simple rule-based approach without NLP")
        # Create a minimal placeholder to avoid errors
        nlp = None

class TrendingFetcher:
    """Class to fetch trending sports topics from Google Trends."""
    
    # Constants
    SPORTS_CATEGORY_ID = 20  # Google Trends category ID for Sports
    MAX_RETRIES = 5
    INITIAL_BACKOFF = 2  # seconds
    MAX_TOPICS = 20
    
    # Known major sporting events - will be used to aid classification
    KNOWN_SPORTING_EVENTS = [
        "nba", "nfl", "mlb", "nhl", "premier league", "la liga", "bundesliga", 
        "serie a", "ligue 1", "champions league", "europa league", "world cup",
        "olympics", "super bowl", "wimbledon", "us open", "french open", 
        "australian open", "masters", "pga", "ufc", "formula 1", "f1", "nascar",
        "stanley cup", "world series", "finals", "championship", "playoff",
        "grand prix", "tournament", "open", "cup", "match", "game", "series"
    ]
    
    def __init__(self, hl: str = "en-US", tz: int = 240, geo: str = "US", timeout: int = 10):
        """
        Initialize the TrendingFetcher.
        
        Args:
            hl: Language (default: en-US)
            tz: Timezone offset (default: 240 - US Eastern)
            geo: Geographic location (default: US)
            timeout: Request timeout in seconds
        """
        self.hl = hl
        self.tz = tz
        self.geo = geo
        self.timeout = timeout
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        self._initialize_pytrends()
    
    def _initialize_pytrends(self) -> None:
        """Initialize PyTrends with random user agent to avoid blocking."""
        user_agent = random.choice(self.user_agents)
        
        # Create a requests session with custom headers
        custom_requests_session = requests.Session()
        custom_requests_session.headers.update({
            'User-Agent': user_agent,
            'Accept-Language': self.hl,
            'Accept': 'application/json'
        })
        
        # Initialize PyTrends with our custom session
        self.pytrends = TrendReq(
            hl=self.hl,
            tz=self.tz,
            geo=self.geo,
            timeout=self.timeout,
            requests_args={'verify': True},
            retries=2,
            backoff_factor=0.5,
            requests_kwargs={'headers': custom_requests_session.headers}
        )
        logger.info(f"Initialized PyTrends with locale {self.hl}, timezone {self.tz}, geo {self.geo}")
    
    def _is_sporting_event(self, topic: str) -> bool:
        """
        Determine if a topic is a sporting event rather than a personality.
        
        Args:
            topic: The topic to classify
            
        Returns:
            True if the topic appears to be a sporting event, False otherwise
        """
        # Check if any known sporting event terms are in the topic
        topic_lower = topic.lower()
        for event in self.KNOWN_SPORTING_EVENTS:
            if event in topic_lower:
                return True
        
        # If spaCy is available, use NLP-based classification
        if nlp:
            try:
                # Use spaCy for entity recognition
                doc = nlp(topic)
                
                # If it contains an EVENT or ORG entity and not a PERSON entity, likely an event
                has_event_or_org = any(ent.label_ in ["EVENT", "ORG"] for ent in doc.ents)
                has_person = any(ent.label_ == "PERSON" for ent in doc.ents)
                
                if has_event_or_org and not has_person:
                    return True
                    
                # If contains PERSON, likely a personality
                if has_person:
                    return False
                    
                # Default fallback - check for plural words which often indicate events
                # (e.g., "Finals", "Playoffs", "Championships")
                tokens = [token for token in doc if token.pos_ == "NOUN"]
                plural_count = sum(1 for token in tokens if token.tag_ == "NNS")
                
                return plural_count > 0
            except Exception as e:
                logger.warning(f"Error using spaCy for classification: {str(e)}")
                # Fall through to simple rule-based approach
        
        # Simple rule-based fallback approach if spaCy is unavailable or fails
        # Check if the topic contains words that typically indicate events
        event_indicators = ["championship", "match", "game", "series", "cup", "open", 
                         "finals", "playoffs", "tournament", "vs", "versus"]
        
        if any(indicator in topic_lower for indicator in event_indicators):
            return True
            
        # Check for team names (often have multiple capital letters)
        words = topic.split()
        capital_count = sum(1 for word in words if len(word) > 1 and word[0].isupper())
        
        # If more than one capitalized word and no event indicators, likely a personality
        if capital_count > 1:
            return False
            
        # Default to personality if uncertain (safer assumption)
        return False
    
    def _exponential_backoff(self, attempt: int) -> None:
        """
        Implement exponential backoff for retries.
        
        Args:
            attempt: The current attempt number (0-indexed)
        """
        if attempt == 0:
            return
            
        backoff_time = self.INITIAL_BACKOFF * (2 ** (attempt - 1))
        # Add jitter to avoid thundering herd problem
        jitter = random.uniform(0, 0.5 * backoff_time)
        sleep_time = backoff_time + jitter
        
        logger.info(f"Backing off for {sleep_time:.2f} seconds before retry {attempt}")
        time.sleep(sleep_time)
    
    def fetch_trending_sports(self) -> List[Dict[str, Any]]:
        """
        Fetch trending sports topics from Google Trends.
        
        Returns:
            List of dictionaries containing trending sports topics with structure:
            [
                {
                    "type": "sports_personality" or "sporting_event",
                    "primary_topic": "Topic Name"
                },
                ...
            ]
        """
        trending_topics = []
        attempt = 0
        
        while attempt < self.MAX_RETRIES:
            try:
                # Reset PyTrends connection with a new random user agent
                if attempt > 0:
                    self._initialize_pytrends()
                
                # Apply exponential backoff for retries
                self._exponential_backoff(attempt)
                
                # Get real-time trending searches
                trending_searches_df = self.pytrends.trending_searches(pn=self.geo)
                
                # Get daily trending searches
                try:
                    daily_trends = self.pytrends.daily_trends(geo=self.geo)
                    daily_topics = []
                    if 'trendingSearches' in daily_trends:
                        for trend in daily_trends['trendingSearches']:
                            if 'title' in trend:
                                daily_topics.append(trend['title']['query'])
                except Exception as e:
                    logger.warning(f"Could not fetch daily trends: {str(e)}")
                    daily_topics = []
                
                # Get today's trending searches
                trending_topics_list = trending_searches_df[0].tolist() + daily_topics
                
                # Filter for sports-related topics
                sports_topics = self._filter_sports_topics(trending_topics_list)
                
                # Classify and structure the results
                for topic in sports_topics[:self.MAX_TOPICS]:
                    is_event = self._is_sporting_event(topic)
                    trending_topics.append({
                        "type": "sporting_event" if is_event else "sports_personality",
                        "primary_topic": topic
                    })
                
                logger.info(f"Successfully fetched {len(trending_topics)} trending sports topics")
                return trending_topics
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error on attempt {attempt+1}: {str(e)}")
                attempt += 1
                
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt+1}: {str(e)}")
                attempt += 1
                
        logger.error("Failed to fetch trending topics after maximum retries")
        return []
    
    def _filter_sports_topics(self, topics: List[str]) -> List[str]:
        """
        Filter topics to keep only sports-related ones.
        
        Args:
            topics: List of trending topics
            
        Returns:
            List of sports-related topics
        """
        sports_topics = []
        
        # 1. First try to use Google Trends' category filtering
        try:
            for topic in topics:
                # Skip if topic is too short (likely not meaningful)
                if len(topic) < 3:
                    continue
                    
                # Build payload for category suggestions
                self.pytrends.build_payload([topic], cat=0)
                
                # Get category suggestions
                category_suggestions = self.pytrends.categories()
                
                # Add a small delay to avoid rate limiting
                time.sleep(random.uniform(1.0, 2.0))
                
                # Check if any of the suggested categories are related to sports
                is_sports_related = False
                if category_suggestions:
                    for category in category_suggestions:
                        category_path = category.get('path', '')
                        if '/sports' in category_path.lower():
                            is_sports_related = True
                            break
                
                if is_sports_related:
                    sports_topics.append(topic)
        except Exception as e:
            logger.warning(f"Error using category filtering: {str(e)}")
        
        # 2. If we couldn't get enough sports topics or category filtering failed, 
        # use a fallback approach with known sports terms
        if len(sports_topics) < 5:
            sports_keywords = [
                "nba", "nfl", "mlb", "soccer", "football", "basketball", "baseball",
                "tennis", "golf", "hockey", "rugby", "cricket", "olympics", "ufc",
                "boxing", "mma", "formula 1", "racing", "athlete", "player", "team",
                "match", "game", "tournament", "championship", "league", "cup"
            ]
            
            for topic in topics:
                topic_lower = topic.lower()
                if any(keyword in topic_lower for keyword in sports_keywords):
                    if topic not in sports_topics:
                        sports_topics.append(topic)
        
        logger.info(f"Filtered {len(sports_topics)} sports topics from {len(topics)} trending topics")
        return sports_topics
    
    def save_to_json(self, output_file: str = "trending_sports.json") -> str:
        """
        Fetch trending sports topics and save to JSON file.
        
        Args:
            output_file: Path to output JSON file
            
        Returns:
            Path to the saved JSON file
        """
        trending_sports = self.fetch_trending_sports()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(trending_sports, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(trending_sports)} trending sports topics to {output_file}")
        return output_file


if __name__ == "__main__":
    # Example usage
    fetcher = TrendingFetcher()
    trends = fetcher.fetch_trending_sports()
    print(json.dumps(trends, indent=2))
    
    # Save to file
    output_file = fetcher.save_to_json()
    print(f"Saved trending sports topics to {output_file}")