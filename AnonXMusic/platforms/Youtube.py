import aiohttp
import asyncio
import json

# ⬇️ Yahan apna Google Cloud YouTube API Key daalo
API_KEY = "YOUR_GOOGLE_CLOUD_API_KEY"

# ---------------------------
# ✅ YouTube API Class
# ---------------------------
class YouTubeAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_search_url = "https://www.googleapis.com/youtube/v3/search"
        self.base_video_url = "https://www.googleapis.com/youtube/v3/videos"

    async def search_videos(self, query: str, limit: int = 5):
        """Search videos using YouTube Data API v3"""
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": limit,
            "key": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_search_url, params=params) as resp:
                data = await resp.json()

        if "items" not in data:
            print("❌ API Error:", data)
            return []

        results = []
        for item in data["items"]:
            vid_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            thumbnail = item["snippet"]["thumbnails"]["high"]["url"]

            results.append({
                "video_id": vid_id,
                "title": title,
                "channel": channel,
                "thumbnail": thumbnail,
            })

        return results

    async def get_video_details(self, video_id: str):
        """Fetch single video details including duration, views, etc."""
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_video_url, params=params) as resp:
                data = await resp.json()

        if "items" not in data or not data["items"]:
            print("❌ Video not found or invalid ID")
            return None

        video = data["items"][0]
        snippet = video["snippet"]
        stats = video["statistics"]
        content = video["contentDetails"]

        return {
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "publishedAt": snippet["publishedAt"],
            "duration": content["duration"],
            "views": stats.get("viewCount", 0),
            "likes": stats.get("likeCount", 0),
            "description": snippet["description"],
        }

# ---------------------------
# 🔹 Example Usage
# ---------------------------
async def main():
    yt = YouTubeAPI(API_KEY)

    # 🔍 Search videos
    print("Searching for: Arijit Singh songs...\n")
    results = await yt.search_videos("Arijit Singh songs", limit=3)
    for i, vid in enumerate(results, start=1):
        print(f"{i}. {vid['title']} ({vid['video_id']})")

    # 📄 Get details of the first result
    if results:
        video_id = results[0]["video_id"]
        print("\nFetching details for:", video_id)
        details = await yt.get_video_details(video_id)
        print(json.dumps(details, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
            
