import os
import time
import json
import psycopg2
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
API_KEY = 'YOUR_API_KEY'
CHANNEL_ID = 'UCWOA1ZGywLbqmigxE4Qlvuw'  # Netflix YouTube channel ID
DB_NAME = 'youtube_data'
DB_USER = 'postgres'
DB_PASSWORD = 'your_password'
DB_HOST = 'localhost'
DB_PORT = '5432'

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Connect to PostgreSQL database
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
cursor = conn.cursor()

def create_table_if_not_exists():
    """Create the table if it doesn't exist."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS netflix_youtube_videos (
        id SERIAL PRIMARY KEY,
        video_id VARCHAR(20) NOT NULL UNIQUE,
        title TEXT NOT NULL,
        description TEXT,
        published_at TIMESTAMP NOT NULL,
        thumbnail_url TEXT,
        view_count BIGINT,
        like_count BIGINT,
        comment_count BIGINT,
        duration VARCHAR(20),
        tags TEXT[],
        category_id INTEGER,
        channel_id VARCHAR(30) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_video_id ON netflix_youtube_videos(video_id);
    CREATE INDEX IF NOT EXISTS idx_published_at ON netflix_youtube_videos(published_at);
    """)
    conn.commit()

def get_all_video_ids_from_channel():
    """Get all video IDs from the Netflix channel using playlistItems endpoint."""
    # First, get the uploads playlist ID for the channel
    channel_response = youtube.channels().list(
        part="contentDetails",
        id=CHANNEL_ID
    ).execute()
    
    uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    # Fetch all video IDs from the uploads playlist
    video_ids = []
    next_page_token = None
    
    while True:
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        for item in playlist_response["items"]:
            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        
        next_page_token = playlist_response.get("nextPageToken")
        
        if not next_page_token:
            break
        
        # Sleep to avoid hitting API rate limits
        time.sleep(0.5)
        
        # Notify progress
        print(f"Fetched {len(video_ids)} video IDs so far...")
    
    return video_ids

def get_video_details(video_ids, batch_size=50):
    """Get detailed information for a list of video IDs in batches."""
    all_videos = []
    
    # Process in batches to respect API limits
    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i:i+batch_size]
        
        try:
            # Get video details
            videos_response = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(batch)
            ).execute()
            
            all_videos.extend(videos_response["items"])
            
            print(f"Processed {len(all_videos)}/{len(video_ids)} videos...")
            
            # Sleep to avoid hitting API rate limits
            time.sleep(1)
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            # If we hit quota limits, wait longer
            if e.resp.status == 403:
                print("Quota exceeded. Waiting longer...")
                time.sleep(60)
            continue
    
    return all_videos

def insert_videos_into_db(videos):
    """Insert video data into PostgreSQL database."""
    for video in videos:
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        content_details = video.get("contentDetails", {})
        
        # Extract tags or use empty array
        tags = snippet.get("tags", [])
        if tags is None:
            tags = []
        
        # Format published date
        published_at = snippet.get("publishedAt")
        if published_at:
            published_at = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        
        try:
            cursor.execute("""
            INSERT INTO netflix_youtube_videos 
            (video_id, title, description, published_at, thumbnail_url, 
             view_count, like_count, comment_count, duration, tags, 
             category_id, channel_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (video_id) 
            DO UPDATE SET 
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                thumbnail_url = EXCLUDED.thumbnail_url,
                view_count = EXCLUDED.view_count,
                like_count = EXCLUDED.like_count,
                comment_count = EXCLUDED.comment_count,
                duration = EXCLUDED.duration,
                tags = EXCLUDED.tags,
                category_id = EXCLUDED.category_id,
                updated_at = CURRENT_TIMESTAMP
            """, (
                video.get("id"),
                snippet.get("title"),
                snippet.get("description"),
                published_at,
                snippet.get("thumbnails", {}).get("high", {}).get("url"),
                int(statistics.get("viewCount", 0)) if statistics.get("viewCount") else 0,
                int(statistics.get("likeCount", 0)) if statistics.get("likeCount") else 0,
                int(statistics.get("commentCount", 0)) if statistics.get("commentCount") else 0,
                content_details.get("duration"),
                tags,
                int(snippet.get("categoryId", 0)) if snippet.get("categoryId") else None,
                snippet.get("channelId")
            ))
            
        except Exception as e:
            print(f"Error inserting video {video.get('id')}: {e}")
            conn.rollback()
            continue
    
    # Commit after all insertions
    conn.commit()

def main():
    try:
        # Create table if not exists
        create_table_if_not_exists()
        
        # Get all video IDs from channel
        print("Fetching all video IDs from Netflix channel...")
        video_ids = get_all_video_ids_from_channel()
        print(f"Found {len(video_ids)} videos from Netflix channel")
        
        # Get detailed information for each video
        print("Fetching detailed information for all videos...")
        videos = get_video_details(video_ids)
        
        # Insert into database
        print("Inserting videos into database...")
        insert_videos_into_db(videos)
        
        print(f"Successfully processed {len(videos)} videos from Netflix channel")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()