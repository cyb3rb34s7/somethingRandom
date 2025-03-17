import json
from pytrends.request import TrendReq

class TrendingFetcher:
    def __init__(self):
        self.pytrends = TrendReq(hl="en-US", tz=360)

    def fetch_google_trends(self):
        """Fetch trending topics from Google Trends (US Region)"""
        self.pytrends.build_payload(kw_list=[], cat=20, geo="US", timeframe="now 1-d")
        trends = self.pytrends.trending_searches(pn="united_states")
        return trends[0].tolist()

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
        return self.categorize_trends(google_trends)


if __name__ == "__main__":
    fetcher = TrendingFetcher()
    sports_trends = fetcher.get_trending_sports_topics()
    print(json.dumps(sports_trends, indent=4))