import json
from pytrends.request import TrendReq
from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY

class TrendingFetcher:
    def __init__(self):
        self.pytrends = TrendReq(hl="en-US", tz=360)
        self.youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    def fetch_google_trends(self):
        """Fetch trending topics from Google Trends (US Region)"""
        self.pytrends.build_payload(kw_list=[], cat=20, geo="US", timeframe="now 1-d")
        trends = self.pytrends.trending_searches(pn="united_states")
        return trends[0].tolist()

    def fetch_youtube_trends(self):
        """Fetch trending topics from YouTube (US Region)"""
        request = self.youtube.videos().list(
            part="snippet",
            chart="mostPopular",
            regionCode="US",
            videoCategoryId="17"  # Sports Category
        )
        response = request.execute()
        return [video["snippet"]["title"] for video in response.get("items", [])]

    def categorize_trends(self, trends):
        """Categorize trends as sporting_event or sports_personality"""
        categorized_trends = []
        for trend in trends:
            if any(keyword in trend.lower() for keyword in ["final", "cup", "league", "championship"]):
                categorized_trends.append({"type": "sporting_event", "primary_topic": trend})
            else:
                categorized_trends.append({"type": "sports_personality", "primary_topic": trend})
        return categorized_trends

    def get_trending_sports_topics(self):
        """Main function to fetch & categorize trending sports topics"""
        google_trends = self.fetch_google_trends()
        youtube_trends = self.fetch_youtube_trends()

        all_trends = list(set(google_trends + youtube_trends))  # Merge & Remove Duplicates
        return self.categorize_trends(all_trends)


if __name__ == "__main__":
    fetcher = TrendingFetcher()
    sports_trends = fetcher.get_trending_sports_topics()
    print(json.dumps(sports_trends, indent=4))