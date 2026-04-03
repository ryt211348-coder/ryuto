"""
TikTok video data fetcher using only `requests` (no browser/Playwright needed).

Approach:
  1. Fetch the user's profile page HTML from TikTok
  2. Extract the secUid from the embedded __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON
  3. Call TikTok's internal /api/post/item_list/ endpoint with the secUid
  4. Paginate through all videos collecting metadata

Requirements: requests, beautifulsoup4 (both usually pre-installed)

IMPORTANT: This will NOT work in environments where TikTok domains
(www.tiktok.com) are blocked by a proxy or firewall. In that case,
use the yt-dlp approach (Method B) from a machine with direct internet access.
"""

import json
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class TikTokVideo:
    video_id: str
    title: str
    url: str
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    duration: int
    upload_date: str
    description: str


# ─── Method A: Pure requests (no browser needed) ───────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.tiktok.com/",
}


def get_sec_uid(username: str, session: Optional[requests.Session] = None) -> str:
    """
    Fetch a TikTok user's secUid by scraping their profile page.

    The secUid is embedded in a <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">
    tag as JSON data.
    """
    s = session or requests.Session()
    url = f"https://www.tiktok.com/@{username}"
    resp = s.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    # Parse the embedded JSON
    soup = BeautifulSoup(resp.text, "html.parser")
    script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")

    if not script_tag or not script_tag.string:
        # Fallback: try regex extraction
        match = re.search(
            r'"secUid"\s*:\s*"([^"]+)"', resp.text
        )
        if match:
            return match.group(1)
        raise ValueError(
            f"Could not extract secUid for @{username}. "
            "TikTok may be returning a captcha or empty page."
        )

    data = json.loads(script_tag.string)

    # Navigate the JSON structure to find secUid
    try:
        user_detail = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]
        sec_uid = user_detail["userInfo"]["user"]["secUid"]
        return sec_uid
    except (KeyError, TypeError):
        pass

    # Fallback: search recursively
    match = re.search(r'"secUid"\s*:\s*"([^"]+)"', script_tag.string)
    if match:
        return match.group(1)

    raise ValueError(f"secUid not found in page data for @{username}")


def fetch_user_videos_via_api(
    username: str,
    sec_uid: Optional[str] = None,
    max_videos: int = 300,
    session: Optional[requests.Session] = None,
) -> list[TikTokVideo]:
    """
    Fetch a user's videos using TikTok's internal /api/post/item_list/ endpoint.

    This endpoint returns up to 35 videos per request and supports cursor-based
    pagination.
    """
    s = session or requests.Session()

    if not sec_uid:
        sec_uid = get_sec_uid(username, session=s)
        print(f"Extracted secUid for @{username}: {sec_uid[:30]}...")

    api_url = "https://www.tiktok.com/api/post/item_list/"
    cursor = 0
    all_videos = []

    while len(all_videos) < max_videos:
        params = {
            "aid": "1988",
            "count": "35",
            "cursor": str(cursor),
            "secUid": sec_uid,
            "device_platform": "web_pc",
        }

        api_headers = {
            **HEADERS,
            "Referer": f"https://www.tiktok.com/@{username}",
        }

        resp = s.get(api_url, headers=api_headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("itemList", [])
        if not items:
            break

        for item in items:
            stats = item.get("stats", {})
            desc = item.get("desc", "")
            vid_id = item.get("id", "")
            create_time = item.get("createTime", 0)

            # Convert Unix timestamp to date string
            if isinstance(create_time, (int, float)) and create_time > 0:
                upload_date = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
            else:
                upload_date = str(create_time)

            video = TikTokVideo(
                video_id=vid_id,
                title=desc[:100],
                url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
                view_count=stats.get("playCount", 0),
                like_count=stats.get("diggCount", 0),
                comment_count=stats.get("commentCount", 0),
                share_count=stats.get("shareCount", 0),
                duration=item.get("video", {}).get("duration", 0),
                upload_date=upload_date,
                description=desc,
            )
            all_videos.append(video)

        print(f"  Fetched {len(items)} videos (total: {len(all_videos)})")

        if not data.get("hasMore", False):
            break

        cursor = data.get("cursor", cursor + 35)
        time.sleep(1)  # Rate limiting: be polite

    return all_videos


# ─── Method B: yt-dlp fallback (works if yt-dlp can reach TikTok) ──────────────

def fetch_user_videos_via_ytdlp(
    username: str,
    sec_uid: Optional[str] = None,
) -> list[TikTokVideo]:
    """
    Fetch videos using yt-dlp.

    If the normal URL fails with "Unable to extract secondary user ID",
    try providing the sec_uid and using the tiktokuser:SEC_UID format.
    """
    import subprocess
    import sys

    # Determine URL format
    if sec_uid:
        # Use the sec_uid format which bypasses the username lookup
        url = f"tiktokuser:{sec_uid}"
    else:
        url = f"https://www.tiktok.com/@{username}"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--no-warnings",
        url,
    ]

    print(f"Running: {' '.join(cmd[:6])} ...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0 and not result.stdout:
        error_msg = result.stderr.strip().split("\n")[-1] if result.stderr else "Unknown error"
        raise RuntimeError(f"yt-dlp failed: {error_msg}")

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            vid_id = str(data.get("id", ""))
            create_time = data.get("upload_date", "")
            # yt-dlp returns upload_date as YYYYMMDD
            if len(create_time) == 8:
                create_time = f"{create_time[:4]}-{create_time[4:6]}-{create_time[6:]}"

            video = TikTokVideo(
                video_id=vid_id,
                title=(data.get("description", "") or data.get("title", ""))[:100],
                url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
                view_count=int(data.get("view_count", 0) or 0),
                like_count=int(data.get("like_count", 0) or 0),
                comment_count=int(data.get("comment_count", 0) or 0),
                share_count=int(data.get("share_count", 0) or 0),
                duration=int(data.get("duration", 0) or 0),
                upload_date=create_time,
                description=data.get("description", "") or data.get("title", ""),
            )
            videos.append(video)
        except (json.JSONDecodeError, ValueError):
            continue

    return videos


# ─── Method C: Scrape profile page HTML for embedded video data ─────────────────

def fetch_user_videos_from_html(username: str) -> list[TikTokVideo]:
    """
    Scrape the profile page HTML for embedded video data.

    TikTok embeds the first ~30 videos in the __UNIVERSAL_DATA_FOR_REHYDRATION__
    script tag. This method extracts them without needing the API endpoint.
    Limited to ~30 most recent videos.
    """
    s = requests.Session()
    url = f"https://www.tiktok.com/@{username}"
    resp = s.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    script_tag = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")

    if not script_tag or not script_tag.string:
        raise ValueError("Could not find embedded data in profile page")

    data = json.loads(script_tag.string)

    # Try to find video items in the embedded data
    try:
        item_list = (
            data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        )
        # The profile page may also have video list under a different key
    except (KeyError, TypeError):
        pass

    # Search for itemList in the data
    videos_raw = []
    data_str = json.dumps(data)

    # Try common paths where videos might be stored
    try:
        user_module = data.get("__DEFAULT_SCOPE__", {})
        for key in user_module:
            module = user_module[key]
            if isinstance(module, dict):
                if "itemList" in module:
                    videos_raw = module["itemList"]
                    break
    except (AttributeError, TypeError):
        pass

    videos = []
    for item in videos_raw:
        stats = item.get("stats", {})
        desc = item.get("desc", "")
        vid_id = item.get("id", "")
        create_time = item.get("createTime", 0)

        if isinstance(create_time, (int, float)) and create_time > 0:
            upload_date = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
        else:
            upload_date = str(create_time)

        video = TikTokVideo(
            video_id=vid_id,
            title=desc[:100],
            url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
            view_count=stats.get("playCount", 0),
            like_count=stats.get("diggCount", 0),
            comment_count=stats.get("commentCount", 0),
            share_count=stats.get("shareCount", 0),
            duration=item.get("video", {}).get("duration", 0),
            upload_date=upload_date,
            description=desc,
        )
        videos.append(video)

    return videos


# ─── Main: try all methods ──────────────────────────────────────────────────────

def fetch_videos(username: str, max_videos: int = 300) -> list[TikTokVideo]:
    """
    Try all available methods to fetch TikTok videos for a user.

    Order of attempts:
      1. Requests-based API call (Method A) - fastest, no browser needed
      2. Profile page HTML scraping (Method C) - limited to ~30 videos
      3. yt-dlp (Method B) - most robust, works with sec_uid workaround
    """
    # Method A: Direct API
    print(f"\n=== Trying Method A: Direct API (requests) for @{username} ===")
    try:
        videos = fetch_user_videos_via_api(username, max_videos=max_videos)
        if videos:
            print(f"Success! Got {len(videos)} videos via direct API.")
            return videos
    except Exception as e:
        print(f"Method A failed: {e}")

    # Method C: HTML scrape
    print(f"\n=== Trying Method C: HTML scraping for @{username} ===")
    try:
        videos = fetch_user_videos_from_html(username)
        if videos:
            print(f"Success! Got {len(videos)} videos from HTML.")
            return videos
    except Exception as e:
        print(f"Method C failed: {e}")

    # Method B: yt-dlp
    print(f"\n=== Trying Method B: yt-dlp for @{username} ===")
    try:
        videos = fetch_user_videos_via_ytdlp(username)
        if videos:
            print(f"Success! Got {len(videos)} videos via yt-dlp.")
            return videos
    except Exception as e:
        print(f"Method B failed: {e}")

    # Method B with sec_uid workaround (if we got sec_uid from Method A attempt)
    print(f"\n=== Trying Method B: yt-dlp with sec_uid workaround ===")
    try:
        sec_uid = get_sec_uid(username)
        videos = fetch_user_videos_via_ytdlp(username, sec_uid=sec_uid)
        if videos:
            print(f"Success! Got {len(videos)} videos via yt-dlp+sec_uid.")
            return videos
    except Exception as e:
        print(f"Method B (sec_uid) failed: {e}")

    print("\nAll methods failed. See suggestions below.")
    return []


if __name__ == "__main__":
    import sys

    username = sys.argv[1] if len(sys.argv) > 1 else "misakism13"
    videos = fetch_videos(username)

    if videos:
        print(f"\n{'='*80}")
        print(f"Found {len(videos)} videos for @{username}")
        print(f"{'='*80}\n")

        for i, v in enumerate(videos[:10], 1):
            print(f"{i:3d}. [{v.upload_date}] {v.title[:60]}")
            print(f"     Views: {v.view_count:>12,} | Likes: {v.like_count:>10,} | "
                  f"Comments: {v.comment_count:>8,} | Shares: {v.share_count:>8,} | "
                  f"Duration: {v.duration}s")
            print()

        # Save to JSON
        output_file = f"tiktok_{username}_videos.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(v) for v in videos], f, ensure_ascii=False, indent=2)
        print(f"Saved all {len(videos)} videos to {output_file}")
    else:
        print("\nNo videos fetched. Possible causes:")
        print("  - TikTok domains blocked by proxy/firewall")
        print("  - Account is private")
        print("  - TikTok is returning CAPTCHA")
        print("\nWorkarounds:")
        print("  1. Run this script from a machine with direct internet access")
        print("  2. Use a VPN or proxy that allows TikTok traffic")
        print("  3. Provide a sec_uid directly if you have one:")
        print("     fetch_user_videos_via_api('misakism13', sec_uid='YOUR_SEC_UID')")
        print("  4. Use yt-dlp with: yt-dlp --dump-json --flat-playlist tiktokuser:SEC_UID")
