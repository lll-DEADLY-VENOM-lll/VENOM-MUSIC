# --- START OF Youtube.py FILE (MODIFIED FOR GOOGLE API) ---

import asyncio
import os
import re
from typing import Union
import requests
import yt_dlp
import isodate  # <-- New library for parsing ISO 8601 durations

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from AnonXMusic import LOGGER
from config import YOUTUBE_API_KEY  # <-- Your new key from the config file

# Global session object to reuse network connections
SESSION = requests.Session()

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.api_base = "https://www.googleapis.com/youtube/v3/"
        
        if not YOUTUBE_API_KEY:
            LOGGER(__name__).error("YOUTUBE_API_KEY is not configured! Some functions will not work.")

    def _parse_duration(self, duration_iso):
        """Converts ISO 8601 duration to total seconds and an MM:SS formatted string."""
        if not duration_iso:
            return 0, "00:00"
        try:
            duration_obj = isodate.parse_duration(duration_iso)
            total_seconds = int(duration_obj.total_seconds())
            mins, secs = divmod(total_seconds, 60)
            return total_seconds, f"{mins:02d}:{secs:02d}"
        except isodate.ISO8601Error:
            return 0, "00:00"

    async def _fetch_from_api(self, endpoint, params):
        """A generic function to fetch data from the Google API."""
        params['key'] = YOUTUBE_API_KEY
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: SESSION.get(f"{self.api_base}{endpoint}", params=params, timeout=10)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            LOGGER(__name__).error(f"Error connecting to Google API: {e}")
            return None
        except Exception as e:
            LOGGER(__name__).error(f"Error processing data from API: {e}")
            return None

    def _extract_video_id(self, link: str):
        """Extracts the video ID from a YouTube link."""
        if 'youtu.be' in link:
            video_id = link.split('/')[-1].split('?')[0]
            return video_id
        match = re.search(r"v=([a-zA-Z0-9_-]{11})", link)
        return match.group(1) if match else None

    async def _get_video_details(self, query: str, is_id: bool = False):
        """Fetches video details from a video ID or a search query."""
        if is_id:
            params = {
                'part': 'snippet,contentDetails',
                'id': query,
            }
            data = await self._fetch_from_api('videos', params)
        else:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': 1,
            }
            data = await self._fetch_from_api('search', params)
        
        if not data or not data.get('items'):
            return None
        
        return data['items'][0]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        """Provides full video details (title, duration, thumbnail, ID)."""
        query = link if videoid else self._extract_video_id(link)
        if not query:
            # If no ID is found, treat it as a search query
            result_item = await self._get_video_details(link, is_id=False)
            if not result_item:
                raise ValueError("No video found on YouTube.")
            query = result_item['id']['videoId']
            # Now, get the full details using the found ID
            result_item = await self._get_video_details(query, is_id=True)
        else:
            result_item = await self._get_video_details(query, is_id=True)

        if not result_item:
            raise ValueError("Could not get details for the video ID.")

        snippet = result_item['snippet']
        content_details = result_item.get('contentDetails', {})
        
        title = snippet['title']
        vidid = result_item['id']
        thumbnail = snippet.get('thumbnails', {}).get('high', {}).get('url')

        duration_sec, duration_min = self._parse_duration(content_details.get('duration'))

        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        details_tuple = await self.details(link, videoid)
        return details_tuple[0]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        details_tuple = await self.details(link, videoid)
        return details_tuple[1]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        details_tuple = await self.details(link, videoid)
        return details_tuple[3]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """Provides a direct link for streaming using yt-dlp."""
        if videoid:
            link = self.base + link
            
        ydl_opts = {
            'format': 'best[height<=?720][width<=?1280]/best',
            'quiet': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                return 1, info['url']
        except Exception as e:
            LOGGER(__name__).error(f"Error extracting video link with yt-dlp: {e}")
            return 0, str(e)

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        """Provides a list of video IDs from a playlist."""
        if videoid:
            playlist_id = link
        else:
            match = re.search(r"list=([a-zA-Z0-9_-]+)", link)
            if not match:
                return []
            playlist_id = match.group(1)

        params = {
            'part': 'snippet',
            'playlistId': playlist_id,
            'maxResults': limit,
        }
        data = await self._fetch_from_api('playlistItems', params)
        
        video_ids = []
        if data and data.get('items'):
            for item in data['items']:
                video_ids.append(item['snippet']['resourceId']['videoId'])
        
        return video_ids

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None, # Kept for compatibility
        songvideo: Union[bool, str] = None, # Kept for compatibility
        format_id: Union[bool, str] = None, # Kept for compatibility
        title: Union[bool, str] = None,     # Kept for compatibility
    ) -> str:
        """
        Downloads audio or video using yt-dlp.
        This no longer uses an external proxy.
        """
        if videoid:
            link = self.base + link

        loop = asyncio.get_running_loop()

        def ytdl_download():
            video_id = self._extract_video_id(link) or f"temp_{os.urandom(4).hex()}"
            
            if video:
                # Download video
                filepath = os.path.join("downloads", f"{video_id}.mp4")
                ydl_opts = {
                    "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "outtmpl": filepath,
                    "quiet": True,
                    "merge_output_format": "mp4",
                    "nocheckcertificate": True,
                }
            else:
                # Download audio
                filepath = os.path.join("downloads", f"{video_id}.mp3")
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": filepath,
                    "quiet": True,
                    "nocheckcertificate": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                }
            
            if os.path.exists(filepath):
                return filepath, True

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([link])
                    return filepath, True
                except Exception as e:
                    LOGGER(__name__).error(f"yt-dlp download error: {e}")
                    return None, False

        downloaded_file, direct = await loop.run_in_executor(None, ytdl_download)
        
        return downloaded_file, direct