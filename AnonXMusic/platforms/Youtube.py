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
        self.base_video_url = "https://www.googleapis.com/youtube/v3/videos"
        self.base_search_url = "https://www.googleapis.com/youtube/v3/search"
        self.regex = r"(?:youtube\.com|youtu\.be)"

    async def _fetch_json(self, url: str, params: dict):
        """Helper to make async API requests"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                return await response.json()

    async def _get_video_details(self, query: str, limit: int = 5) -> Union[dict, None]:
        """Search videos using Google Cloud YouTube Data API"""
        if not YT_API_KEY:
            logger.error("YT_API_KEY not set in config file.")
            return None

        params = {
            "part": "snippet",
            "q": query,
            "maxResults": limit,
            "type": "video",
            "key": YT_API_KEY,
        }

        data = await self._fetch_json(self.base_search_url, params)

        if "items" not in data or not data["items"]:
            logger.error(f"No search results found for {query}")
            return None

        # First result
        item = data["items"][0]
        vid_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"]["high"]["url"]
        channel = item["snippet"]["channelTitle"]

        # Fetch duration via videos.list
        dur_params = {
            "part": "contentDetails",
            "id": vid_id,
            "key": YT_API_KEY
        }
        dur_data = await self._fetch_json(self.base_video_url, dur_params)
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
            "link": f"https://www.youtube.com/watch?v={vid_id}",
        }

    def _parse_duration(self, iso_duration):
        """Convert ISO8601 duration (PT4M30S) -> MM:SS"""
        pattern = re.compile(r"PT(?:(\d+)M)?(?:(\d+)S)?")
        match = pattern.match(iso_duration)
        if not match:
            return "0:00"
        minutes = int(match.group(1) or 0)
        seconds = int(match.group(2) or 0)
        return f"{minutes}:{seconds:02d}"

    async def exists(self, link: str):
        """Check if link is valid YouTube"""
        return bool(re.search(self.regex, link))

    async def details(self, link_or_query: str):
        """Return title, duration, thumbnail, and video ID"""
        result = await self._get_video_details(link_or_query)
        if not result:
            raise ValueError("No suitable video found.")

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

    async def thumbnail(self, query: str):
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("Video not found.")
        return result["thumbnails"][0]["url"]

    async def video_url(self, query: str):
        result = await self._get_video_details(query)
        if not result:
            raise ValueError("Video not found.")
        return result["link"]

# -------------------------------
# 🔹 Test Example
# -------------------------------
async def main():
    yt = YouTubeAPI()
    result = await yt.details("Arijit Singh Tum Hi Ho")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
        
