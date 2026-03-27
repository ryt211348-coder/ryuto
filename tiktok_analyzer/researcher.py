"""TikTok リサーチャー - キーワードでTikTok動画を検索・収集する."""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests as http_requests
from rich.console import Console

console = Console()


@dataclass
class TikTokVideo:
    """リサーチで取得した動画データ."""
    video_id: str = ""
    url: str = ""
    title: str = ""
    description: str = ""
    transcript: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    duration: int = 0
    upload_date: str = ""
    upload_timestamp: int = 0
    account_name: str = ""
    account_url: str = ""
    account_id: str = ""
    thumbnail: str = ""


@dataclass
class TikTokAccount:
    """TikTokアカウント情報."""
    username: str = ""
    display_name: str = ""
    url: str = ""
    follower_count: int = 0
    following_count: int = 0
    like_count: int = 0
    video_count: int = 0
    bio: str = ""
    first_post_date: str = ""
    recent_month_views: int = 0
    avatar: str = ""


def search_tiktok_videos(keyword: str, min_views: int = 500_000,
                         period_months: int = 3, max_results: int = 30) -> list[TikTokVideo]:
    """TikTokでキーワード検索し、条件に合う動画を返す."""
    videos = []

    # 方法1: ScrapeCreators API で検索
    sc_videos = _search_scrapecreators(keyword, max_results)
    if sc_videos:
        videos.extend(sc_videos)

    # 方法2: TikTokApi で検索
    if len(videos) < max_results:
        try:
            api_videos = _search_tiktokapi(keyword, max_results - len(videos))
            videos.extend(api_videos)
        except Exception as e:
            console.print(f"  [dim]TikTokApi検索: {e}[/dim]")

    # 方法3: Web検索でTikTok動画を探す
    if len(videos) < 5:
        web_videos = _search_web_fallback(keyword, max_results)
        # 重複排除
        existing_ids = {v.video_id for v in videos}
        for v in web_videos:
            if v.video_id not in existing_ids:
                videos.append(v)
                existing_ids.add(v.video_id)

    # フィルタリング
    cutoff = datetime.now() - timedelta(days=period_months * 30)
    filtered = []
    for v in videos:
        # 再生数フィルタ
        if v.views < min_views:
            continue
        # 期間フィルタ
        if v.upload_timestamp:
            vdate = datetime.fromtimestamp(v.upload_timestamp)
            if vdate < cutoff:
                continue
        elif v.upload_date:
            parsed = _parse_date(v.upload_date)
            if parsed and parsed < cutoff:
                continue
        filtered.append(v)

    # 再生数順でソート
    filtered.sort(key=lambda v: v.views, reverse=True)
    return filtered[:max_results]


def get_video_transcript(video_url: str) -> str:
    """動画の文字起こしを取得する."""
    # ScrapeCreators APIで取得
    text = _get_transcript_scrapecreators(video_url)
    if text:
        return text

    # yt-dlp字幕で取得
    text = _get_transcript_ytdlp(video_url)
    if text:
        return text

    return ""


def get_account_info(account_url: str) -> Optional[TikTokAccount]:
    """TikTokアカウントの情報を取得する."""
    username = _parse_username(account_url)
    if not username:
        return None

    account = TikTokAccount(username=username, url=f"https://www.tiktok.com/@{username}")

    # ScrapeCreators APIでアカウント情報取得
    sc_info = _get_account_scrapecreators(username)
    if sc_info:
        return sc_info

    # TikTokApiで取得
    try:
        api_info = _get_account_tiktokapi(username)
        if api_info:
            return api_info
    except Exception:
        pass

    # yt-dlpでフォールバック
    ytdlp_info = _get_account_ytdlp(account_url)
    if ytdlp_info:
        return ytdlp_info

    return account


# ===== ScrapeCreators API =====

def _search_scrapecreators(keyword: str, max_results: int = 30) -> list[TikTokVideo]:
    """ScrapeCreators APIでTikTok動画を検索する."""
    api_key = os.environ.get("SCRAPECREATORS_API_KEY", "")
    if not api_key:
        return []

    videos = []
    try:
        resp = http_requests.get(
            "https://api.scrapecreators.com/v2/tiktok/search/videos",
            headers={"x-api-key": api_key},
            params={"query": keyword, "count": min(max_results, 30)},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", data.get("videos", data.get("items", [])))
            if isinstance(items, list):
                for item in items:
                    v = _parse_scrapecreators_video(item)
                    if v:
                        videos.append(v)
            console.print(f"  [green]ScrapeCreators: {len(videos)}本取得[/green]")
        else:
            console.print(f"  [dim]ScrapeCreators検索: HTTP {resp.status_code}[/dim]")
    except Exception as e:
        console.print(f"  [dim]ScrapeCreators検索: {e}[/dim]")

    return videos


def _parse_scrapecreators_video(item: dict) -> Optional[TikTokVideo]:
    """ScrapeCreatorsの動画データをTikTokVideoに変換する."""
    if not isinstance(item, dict):
        return None

    stats = item.get("stats", item.get("statistics", {}))
    author = item.get("author", item.get("user", {}))
    video_data = item.get("video", {})

    vid_id = str(item.get("id", item.get("video_id", "")))
    if not vid_id:
        return None

    username = ""
    if isinstance(author, dict):
        username = author.get("uniqueId", author.get("username", ""))
    elif isinstance(author, str):
        username = author

    v = TikTokVideo(
        video_id=vid_id,
        url=f"https://www.tiktok.com/@{username}/video/{vid_id}" if username else "",
        title=item.get("desc", item.get("description", item.get("title", "")))[:100],
        description=item.get("desc", item.get("description", "")),
        views=int(stats.get("playCount", stats.get("views", stats.get("play_count", 0))) or 0),
        likes=int(stats.get("diggCount", stats.get("likes", stats.get("like_count", 0))) or 0),
        comments=int(stats.get("commentCount", stats.get("comments", 0)) or 0),
        shares=int(stats.get("shareCount", stats.get("shares", 0)) or 0),
        duration=int(video_data.get("duration", item.get("duration", 0)) or 0),
        upload_timestamp=int(item.get("createTime", item.get("create_time", 0)) or 0),
        account_name=username,
        account_url=f"https://www.tiktok.com/@{username}" if username else "",
        account_id=username,
        thumbnail=video_data.get("cover", item.get("thumbnail", "")),
    )

    if v.upload_timestamp:
        try:
            v.upload_date = datetime.fromtimestamp(v.upload_timestamp).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            pass

    return v


def _get_transcript_scrapecreators(video_url: str) -> str:
    """ScrapeCreators APIで文字起こしを取得する."""
    api_key = os.environ.get("SCRAPECREATORS_API_KEY", "")
    if not api_key:
        return ""

    try:
        resp = http_requests.get(
            "https://api.scrapecreators.com/v1/tiktok/video/transcript",
            headers={"x-api-key": api_key},
            params={"url": video_url, "language": "ja", "use_ai_as_fallback": "true"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            raw = data.get("transcript", "")
            if isinstance(raw, str) and raw.strip():
                if "WEBVTT" in raw or "-->" in raw:
                    return _parse_vtt(raw)
                return raw.strip()
            if isinstance(raw, list):
                texts = [item.get("text", "") for item in raw if isinstance(item, dict)]
                return " ".join(texts).strip()
    except Exception:
        pass
    return ""


def _get_account_scrapecreators(username: str) -> Optional[TikTokAccount]:
    """ScrapeCreators APIでアカウント情報を取得する."""
    api_key = os.environ.get("SCRAPECREATORS_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = http_requests.get(
            "https://api.scrapecreators.com/v2/tiktok/user/info",
            headers={"x-api-key": api_key},
            params={"username": username},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            user = data.get("data", data.get("user", data))
            stats = user.get("stats", user.get("statistics", {}))

            return TikTokAccount(
                username=username,
                display_name=user.get("nickname", user.get("display_name", username)),
                url=f"https://www.tiktok.com/@{username}",
                follower_count=int(stats.get("followerCount", stats.get("followers", 0)) or 0),
                following_count=int(stats.get("followingCount", stats.get("following", 0)) or 0),
                like_count=int(stats.get("heartCount", stats.get("likes", stats.get("heart", 0))) or 0),
                video_count=int(stats.get("videoCount", stats.get("videos", 0)) or 0),
                bio=user.get("signature", user.get("bio", "")),
                avatar=user.get("avatarThumb", user.get("avatar", "")),
            )
    except Exception:
        pass
    return None


# ===== TikTokApi =====

def _search_tiktokapi(keyword: str, max_results: int = 20) -> list[TikTokVideo]:
    """TikTokApi (Playwright) で動画を検索する."""
    from TikTokApi import TikTokApi

    videos = []

    async def _search():
        async with TikTokApi() as api:
            await api.create_sessions(num_sessions=1, sleep_after=5)
            async for video in api.search.videos(keyword, count=max_results):
                vd = video.as_dict
                stats = vd.get("stats", {})
                author = vd.get("author", {})
                username = author.get("uniqueId", "")
                vid_id = str(vd.get("id", ""))
                create_time = int(vd.get("createTime", 0) or 0)

                v = TikTokVideo(
                    video_id=vid_id,
                    url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
                    title=vd.get("desc", "")[:100],
                    description=vd.get("desc", ""),
                    views=int(stats.get("playCount", 0) or 0),
                    likes=int(stats.get("diggCount", 0) or 0),
                    comments=int(stats.get("commentCount", 0) or 0),
                    shares=int(stats.get("shareCount", 0) or 0),
                    duration=int(vd.get("video", {}).get("duration", 0) or 0),
                    upload_timestamp=create_time,
                    account_name=username,
                    account_url=f"https://www.tiktok.com/@{username}",
                    account_id=username,
                    thumbnail=vd.get("video", {}).get("cover", ""),
                )
                if create_time:
                    try:
                        v.upload_date = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
                    except (ValueError, OSError):
                        pass
                videos.append(v)

    asyncio.run(_search())
    console.print(f"  [green]TikTokApi: {len(videos)}本取得[/green]")
    return videos


def _get_account_tiktokapi(username: str) -> Optional[TikTokAccount]:
    """TikTokApiでアカウント情報を取得する."""
    from TikTokApi import TikTokApi

    result = None

    async def _fetch():
        nonlocal result
        async with TikTokApi() as api:
            await api.create_sessions(num_sessions=1, sleep_after=5)
            user = api.user(username)
            info = await user.info()
            user_data = info.get("userInfo", info)
            user_info = user_data.get("user", {})
            stats = user_data.get("stats", {})

            result = TikTokAccount(
                username=username,
                display_name=user_info.get("nickname", username),
                url=f"https://www.tiktok.com/@{username}",
                follower_count=int(stats.get("followerCount", 0) or 0),
                following_count=int(stats.get("followingCount", 0) or 0),
                like_count=int(stats.get("heartCount", stats.get("heart", 0)) or 0),
                video_count=int(stats.get("videoCount", 0) or 0),
                bio=user_info.get("signature", ""),
                avatar=user_info.get("avatarThumb", ""),
            )

    asyncio.run(_fetch())
    return result


# ===== Web Search Fallback =====

def _search_web_fallback(keyword: str, max_results: int = 20) -> list[TikTokVideo]:
    """Web検索でTikTok動画を探すフォールバック."""
    videos = []
    search_query = f"site:tiktok.com {keyword} スキンケア"

    try:
        # Google検索をHTTPリクエストで試行
        resp = http_requests.get(
            "https://www.google.com/search",
            params={"q": search_query, "num": 20},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            # TikTok動画URLを抽出
            urls = re.findall(r'https://www\.tiktok\.com/@[\w.]+/video/(\d+)', resp.text)
            usernames = re.findall(r'https://www\.tiktok\.com/@([\w.]+)/video/', resp.text)

            for vid_id, username in zip(urls, usernames):
                v = TikTokVideo(
                    video_id=vid_id,
                    url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
                    account_name=username,
                    account_url=f"https://www.tiktok.com/@{username}",
                    account_id=username,
                )
                videos.append(v)

            if videos:
                console.print(f"  [green]Web検索: {len(videos)}件のURL取得[/green]")
    except Exception as e:
        console.print(f"  [dim]Web検索: {e}[/dim]")

    return videos[:max_results]


# ===== yt-dlp Fallback =====

def _get_transcript_ytdlp(video_url: str) -> str:
    """yt-dlpで字幕を取得する."""
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp())
    base = tmp_dir / "sub"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--write-auto-subs", "--write-subs",
        "--sub-langs", "ja,jpn,ja-JP",
        "--sub-format", "vtt/srt/best",
        "--skip-download",
        "-o", str(base) + ".%(ext)s",
        "--no-warnings", "--quiet",
        video_url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""

    for ext in ["vtt", "srt"]:
        for f in tmp_dir.glob(f"sub*.{ext}"):
            text = _parse_vtt(f.read_text(encoding="utf-8"))
            if text and len(text.strip()) > 5:
                return text.strip()

    return ""


def _get_account_ytdlp(account_url: str) -> Optional[TikTokAccount]:
    """yt-dlpでアカウント情報を取得する."""
    username = _parse_username(account_url)
    if not username:
        return None

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json", "--flat-playlist",
        "--playlist-items", "1:5",
        "--no-download", "--no-warnings",
        account_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0 or not result.stdout:
        return None

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not videos:
        return None

    account = TikTokAccount(
        username=username,
        url=f"https://www.tiktok.com/@{username}",
    )

    # 最初の動画からアカウント情報を推定
    first = videos[0]
    account.display_name = first.get("uploader", first.get("channel", username))

    return account


# ===== ユーティリティ =====

def _parse_username(url: str) -> str:
    """URLからユーザー名を抽出する."""
    url = url.strip().rstrip("/")
    if "@" in url:
        parts = url.split("@")
        return parts[-1].split("/")[0].split("?")[0]
    return url


def _parse_date(date_str: str) -> Optional[datetime]:
    """日付文字列をdatetimeに変換."""
    if not date_str:
        return None
    if date_str.isdigit() and len(date_str) >= 10:
        try:
            return datetime.fromtimestamp(int(date_str))
        except (ValueError, OSError):
            pass
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(date_str[:19], fmt)
        except ValueError:
            continue
    return None


def _parse_vtt(vtt_content: str) -> str:
    """VTT/SRTからテキストを抽出する."""
    lines = vtt_content.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:") or line.startswith("NOTE"):
            continue
        if "-->" in line or re.match(r"^\d+$", line) or re.match(r"^\d{2}:\d{2}", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line and line not in text_lines:
            text_lines.append(line)
    return " ".join(text_lines).strip()


def format_video_for_display(video: TikTokVideo) -> dict:
    """TikTokVideoをフロント表示用に整形する."""
    return {
        "video_id": video.video_id,
        "url": video.url,
        "title": video.title,
        "description": video.description,
        "transcript": video.transcript,
        "views": video.views,
        "likes": video.likes,
        "comments": video.comments,
        "shares": video.shares,
        "duration": video.duration,
        "upload_date": video.upload_date,
        "account_name": video.account_name,
        "account_url": video.account_url,
        "thumbnail": video.thumbnail,
    }


def format_account_for_display(account: TikTokAccount) -> dict:
    """TikTokAccountをフロント表示用に整形する."""
    return {
        "username": account.username,
        "display_name": account.display_name,
        "url": account.url,
        "follower_count": account.follower_count,
        "following_count": account.following_count,
        "like_count": account.like_count,
        "video_count": account.video_count,
        "bio": account.bio,
        "first_post_date": account.first_post_date,
        "recent_month_views": account.recent_month_views,
        "avatar": account.avatar,
    }
