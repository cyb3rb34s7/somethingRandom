"""
Downloads curated royalty-free music tracks and organizes them into mood
folders for the stitching pipeline.

Why this script uses Mixkit instead of old Pixabay CDN links:
- In this environment, pixabay.com/music is protected by a Cloudflare challenge.
- Most previously hardcoded cdn.pixabay.com/audio URLs now return HTTP 403.
- Mixkit mood pages are publicly accessible and expose direct MP3 asset URLs in
  JSON-LD metadata, with a free commercial-use license and no attribution
  required according to the site metadata and license page.

Run once before using the stitching pipeline:
    python tools/collect_music.py
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path

MUSIC_DIR = Path("music")
TRACKS_PER_MOOD = 4
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}

SOURCE_PAGES: dict[str, list[str]] = {
    "dark_thriller": [
        "https://mixkit.co/free-stock-music/mood/dark/",
    ],
    "epic_prestige": [
        "https://mixkit.co/free-stock-music/tag/cinematic/",
        "https://mixkit.co/free-stock-music/tag/trailer/",
    ],
    "upbeat_energetic": [
        "https://mixkit.co/free-stock-music/mood/energetic/",
    ],
    "atmospheric": [
        "https://mixkit.co/free-stock-music/mood/atmospheric/",
    ],
    "familiar_warm": [
        "https://mixkit.co/free-stock-music/mood/warm/",
    ],
    "nostalgic": [
        "https://mixkit.co/free-stock-music/mood/nostalgic/",
    ],
    "confident_bold": [
        "https://mixkit.co/free-stock-music/mood/confident/",
    ],
    "cinematic_neutral": [
        "https://mixkit.co/free-stock-music/mood/neutral/",
    ],
}


@dataclass
class Track:
    filename: str
    url: str
    title: str
    artist: str
    mood: str
    duration_seconds: int


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")
    return slug or "track"


def _parse_iso_duration(value: str) -> int:
    match = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    minutes = int(match.group(1) or 0)
    seconds = int(match.group(2) or 0)
    return minutes * 60 + seconds


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def _extract_tracks_from_mixkit_page(page_url: str, mood: str) -> list[Track]:
    html = _fetch_text(page_url)
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    discovered: list[Track] = []
    seen_urls: set[str] = set()

    for raw_block in blocks:
        try:
            data = json.loads(unescape(raw_block))
        except json.JSONDecodeError:
            continue

        graph = data.get("@graph") if isinstance(data, dict) else None
        nodes = graph if isinstance(graph, list) else [data]

        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") != "ItemList":
                continue

            for item in node.get("itemListElement", []):
                if not isinstance(item, dict) or item.get("@type") != "MusicRecording":
                    continue

                url = item.get("url", "")
                if not url.endswith(".mp3") or url in seen_urls:
                    continue

                title = item.get("name") or "Untitled Track"
                discovered.append(
                    Track(
                        filename="",
                        url=url,
                        title=title,
                        artist=item.get("byArtist") or "Mixkit",
                        mood=mood,
                        duration_seconds=_parse_iso_duration(item.get("duration", "")),
                    )
                )
                seen_urls.add(url)

    curated: list[Track] = []
    for index, track in enumerate(discovered[:TRACKS_PER_MOOD], start=1):
        curated.append(
            Track(
                filename=f"{index:02d}_{_slugify(track.title)}.mp3",
                url=track.url,
                title=track.title,
                artist=track.artist,
                mood=track.mood,
                duration_seconds=track.duration_seconds,
            )
        )

    return curated


def _build_catalog() -> list[Track]:
    catalog: list[Track] = []

    for mood, page_urls in SOURCE_PAGES.items():
        discovered: list[Track] = []
        seen_urls: set[str] = set()

        for page_url in page_urls:
            print(f"Discovering {mood} from {page_url}")
            for track in _extract_tracks_from_mixkit_page(page_url, mood):
                if track.url in seen_urls:
                    continue
                discovered.append(track)
                seen_urls.add(track.url)
                if len(discovered) == TRACKS_PER_MOOD:
                    break
            if len(discovered) == TRACKS_PER_MOOD:
                break

        if len(discovered) < TRACKS_PER_MOOD:
            raise RuntimeError(
                f"Could only curate {len(discovered)} tracks for {mood}; "
                f"expected {TRACKS_PER_MOOD}"
            )

        catalog.extend(
            Track(
                filename=f"{index:02d}_{_slugify(track.title)}.mp3",
                url=track.url,
                title=track.title,
                artist=track.artist,
                mood=track.mood,
                duration_seconds=track.duration_seconds,
            )
            for index, track in enumerate(discovered, start=1)
        )

    return catalog


def _download(track: Track, dest_dir: Path, retries: int = 3) -> bool:
    dest_path = dest_dir / track.filename

    if dest_path.exists():
        print(f"  ✓ Already exists — {track.filename}")
        return True

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(track.url, headers=REQUEST_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                if len(data) < 10_000:
                    raise ValueError(f"Response too small ({len(data)} bytes) — likely not an MP3")
                dest_path.write_bytes(data)
                size_kb = len(data) // 1024
                print(f"  ✓ Downloaded {track.filename} ({size_kb}KB)")
                return True

        except (urllib.error.URLError, ValueError, Exception) as e:
            print(f"  ✗ Attempt {attempt}/{retries} failed for {track.filename}: {e}")
            if attempt < retries:
                time.sleep(2 * attempt)

    print(f"  ✗ FAILED — {track.filename} could not be downloaded")
    return False


def _build_index(results: dict[str, list[dict]]) -> dict:
    return {
        "version": "1.0",
        "moods": {
            mood: tracks
            for mood, tracks in results.items()
            if tracks
        }
    }


def main():
    catalog = _build_catalog()

    print(f"\n{'='*60}")
    print("  Music Collector — Explainable Recommendation Pipeline")
    print("  Source: Mixkit free stock music pages")
    print(f"  Output: {MUSIC_DIR.resolve()}")
    print(f"  Tracks: {len(catalog)} across {len(set(t.mood for t in catalog))} moods")
    print(f"{'='*60}\n")

    MUSIC_DIR.mkdir(exist_ok=True)

    by_mood: dict[str, list[Track]] = {}
    for track in catalog:
        by_mood.setdefault(track.mood, []).append(track)

    results: dict[str, list[dict]] = {}
    total_success = 0
    total_fail = 0

    for mood, tracks in by_mood.items():
        mood_dir = MUSIC_DIR / mood
        mood_dir.mkdir(exist_ok=True)
        print(f"── {mood} ({len(tracks)} tracks)")

        results[mood] = []
        for track in tracks:
            success = _download(track, mood_dir)
            if success:
                results[mood].append({
                    "filename": track.filename,
                    "path": str(mood_dir / track.filename),
                    "title": track.title,
                    "artist": track.artist,
                    "duration_seconds": track.duration_seconds,
                })
                total_success += 1
            else:
                total_fail += 1
        print()

    index = _build_index(results)
    index_path = MUSIC_DIR / "music_index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"{'='*60}")
    print(f"  Done — {total_success} downloaded, {total_fail} failed")
    print(f"  Index written → {index_path}")

    if total_fail > 0:
        print(f"\n  {total_fail} tracks failed. Run the script again to retry.")
        print("  If failures persist, replace the URLs in CATALOG with fresh")
        print("  Pixabay CDN links from pixabay.com/music")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
