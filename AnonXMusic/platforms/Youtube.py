import asyncio
import aiohttp
import json
import re
from typing import Union
from AnonXMusic import LOGGER
from AnonXMusic.utils.formatters import time_to_seconds
from config import YT_API_KEY

logger = LOGGER(__name__)

class YouTubeAPI:
    def __init__(self):
        self.search_url = "https://www.googleapis.com/youtube/v3/search"
        self.videos_url = "https://www.googleapis.com/youtube/v3/videos"
        self.regex = r"(?:youtube\.com|youtu\.be)"

    # -------------------------------
    # 🔹 Helper: Fetch JSON
    # -------------------------------
    async def _fetch_json(self, url: str, params: dict):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    return data
        except Exception as e:
            logger.error(f"Network error: {e}")
            return {}

    # -------------------------------
    # 🔹 Search / Get Video Info
    # -------------------------------
    async def _get_video_details(self, query: str, limit: int = 5) -> Union[dict, None]:
        """Search for YouTube videos using Google Cloud YouTube Data API"""
        if not YT_API_KEY:
            logger.error("❌ Missing YT_API_KEY in config file.")
            return None

        params = {
            "part": "snippet",
            "q": query,
            "maxResults": limit,
            "type": "video",
            "key": YT_API_KEY,
        }

        data = await self._fetch_json(self.search_url, params)

        if "items" not in data or not data["items"]:
            logger.error(f"No results found for query: {query}")
            return None

        # Pick first video
        item = data["items"][0]
        vid_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]
        thumbnail = item["snippet"]["thumbnails"]["high"]["url"]
        video_link = f"https://www.youtube.com/watch?v={vid_id}"

        # Fetch duration info
        dur_params = {
            "part": "contentDetails",
            "id": vid_id,
            "key": YT_API_KEY
        }
        dur_data = await self._fetch_json(self.videos_url, dur_params)

        duration = "0:00"
        try:
            iso_duration = dur_data["items"][0]["contentDetails"]["duration"]
            duration = self._parse_duration(iso_duration)
        except Exception:
            pass

        return {
            "id": vid_id,
            "title": title,
            "channel": channel,
            "duration": duration,
            "thumbnails": [{"url": thumbnail}],
            "link": video_link,
        }

    # -------------------------------
    # 🔹 Duration Parser
    # -------------------------------
    def _parse_duration(self, iso_duration):
        """Convert ISO8601 duration (PT4M30S) to MM:SS"""
        pattern = re.compile(r"PT(?:(\d+)M)?(?:(\d+)S)?")
        match = pattern.match(iso_duration)
        if not match:
            return "0:00"
        minutes = int(match.group(1) or 0)
        seconds = int(match.group(2) or 0)
        return f"{minutes}:{seconds:02d}"

    # -------------------------------
    # 🔹 Utility: Check YouTube Link
    # -------------------------------
    async def exists(self, link: str):
        """Check if link belongs to YouTube"""
        return bool(re.search(self.regex, link))

    # -------------------------------
    # 🔹 Core Methods
    # -------------------------------
    async def details(self, query: str):
        """Return title, duration, thumbnail, and video ID"""
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("No video found.")

        title = result["title"]
        duration_min = result["duration"]
        duration_sec = int(time_to_seconds(duration_min))
        thumbnail = result["thumbnails"][0]["url"]
        vidid = result["id"]

        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, query: str):
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("Video not found.")
        return result["title"]

    async def duration(self, query: str):
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("Video not found.")
        return result["duration"]

    async def thumbnail(self, query: str):
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("Video not found.")
        return result["thumbnails"][0]["url"]

    async def track(self, query: str):
        """Return a full video info dict"""
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("Video not found.")

        return {
            "title": result["title"],
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result["duration"],
            "thumb": result["thumbnails"][0]["url"],
            "channel": result["channel"]
        }, result["id"]

# -------------------------------
# 🔹 Example Test (Run Directly)
# -------------------------------
async def main():
    yt = YouTubeAPI()
    print("🔍 Searching 'Arijit Singh Tum Hi Ho' ...")
    title, dur, sec, thumb, vid = await yt.details("Arijit Singh Tum Hi Ho")
    print(f"\n🎵 Title: {title}\n🕒 Duration: {dur}\n🖼️ Thumbnail: {thumb}\n📺 ID: {vid}")

if __name__ == "__main__":
    asyncio.run(main())
        
