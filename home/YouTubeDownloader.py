#!/usr/bin/env python3
import os
import sys
import yt_dlp

def download_audio(url, output_path=None):
    """
    Download audio from a YouTube video in WAV format.
    
    Args:
        url (str): YouTube video URL
        output_path (str, optional): Directory to save the audio. Defaults to current directory.
    
    Returns:
        str: Path to the downloaded audio file
    """
    if output_path is None:
        output_path = os.getcwd()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',  # Bitrate (not used for WAV, but needed for the parameter)
        }],
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'verbose': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace('.webm', '.wav').replace('.m4a', '.wav')
            return filename
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_audio_downloader.py <youtube_url> [output_path]")
        sys.exit(1)
    
    url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Downloading audio from: {url}")
    result = download_audio(url, output_path)
    
    if result:
        print(f"Download complete! Audio saved to: {result}")
    else:
        print("Download failed!")