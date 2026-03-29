"""TikTok/Instagramキーワード検索 - リアルデータ取得."""

import json
import subprocess
import sys
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta


# キャッシュディレクトリ
CACHE_DIR = Path(__file__).parent.parent / ".search_cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(keyword, platform, period):
    raw = f"{keyword}:{platform}:{period}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(keyword, platform, period):
    """キャッシュからデータを取得(1時間有効)."""
    key = _cache_key(keyword, platform, period)
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if time.time() - data.get("ts", 0) < 3600:
            return data.get("results")
    return None


def _cache_set(keyword, platform, period, results):
    key = _cache_key(keyword, platform, period)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({
        "ts": time.time(),
        "keyword": keyword,
        "results": results
    }, ensure_ascii=False))


def _period_to_days(period):
    return {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365}.get(period, 30)


def search_tiktok_videos(keyword, period="1m", count=10):
    """yt-dlpでTikTokキーワード検索し、実在する動画データを返す."""
    cached = _cache_get(keyword, "tiktok", period)
    if cached:
        return cached

    # yt-dlpのTikTok検索(直接URLベース)
    search_url = f"https://www.tiktok.com/search/video?q={keyword}"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json", "--flat-playlist",
        "--no-download", "--no-warnings",
        "--playlist-end", str(count * 3),  # 多めに取得してフィルタ
        search_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if not result.stdout:
        return []

    max_days = _period_to_days(period)
    cutoff = datetime.now() - timedelta(days=max_days)
    videos = []

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            # 日付フィルタ
            upload_date = d.get("upload_date", "")
            if upload_date:
                try:
                    dt = datetime.strptime(upload_date, "%Y%m%d")
                    if dt < cutoff:
                        continue
                except ValueError:
                    pass

            view_count = int(d.get("view_count", 0) or 0)
            like_count = int(d.get("like_count", 0) or 0)
            comment_count = int(d.get("comment_count", 0) or 0)
            share_count = int(d.get("repost_count", 0) or d.get("share_count", 0) or 0)

            # サムネイル取得
            thumbnail = d.get("thumbnail", "")
            if not thumbnail and d.get("thumbnails"):
                thumbnail = d["thumbnails"][0].get("url", "")

            # アカウント情報
            uploader = d.get("uploader", "") or d.get("channel", "")
            uploader_id = d.get("uploader_id", "") or d.get("channel_id", "")
            uploader_url = d.get("uploader_url", "") or d.get("channel_url", "")
            follower_count = int(d.get("channel_follower_count", 0) or 0)

            # 動画URL
            video_url = d.get("webpage_url", "") or d.get("url", "")
            video_id = d.get("id", "")

            videos.append({
                "id": video_id,
                "title": (d.get("title", "") or d.get("description", ""))[:120],
                "description": d.get("description", ""),
                "url": video_url,
                "platform": "tiktok",
                "views": view_count,
                "likes": like_count,
                "comments": comment_count,
                "shares": share_count,
                "duration": int(d.get("duration", 0) or 0),
                "upload_date": upload_date,
                "thumbnail": thumbnail,
                "account": {
                    "name": uploader,
                    "id": uploader_id,
                    "url": uploader_url,
                    "followers": follower_count,
                },
            })
        except (json.JSONDecodeError, ValueError, KeyError):
            continue

    # 再生数でソート、上位count件
    videos.sort(key=lambda x: x["views"], reverse=True)
    videos = videos[:count]

    if videos:
        _cache_set(keyword, "tiktok", period, videos)

    return videos


def search_instagram_posts(keyword, period="1m", count=10):
    """yt-dlpでInstagramハッシュタグ検索し、実在する投稿データを返す."""
    cached = _cache_get(keyword, "instagram", period)
    if cached:
        return cached

    tag = keyword.replace(" ", "").replace("　", "")
    search_url = f"https://www.instagram.com/explore/tags/{tag}/"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json", "--flat-playlist",
        "--no-download", "--no-warnings",
        "--playlist-end", str(count * 3),
        search_url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if not result.stdout:
        return []

    max_days = _period_to_days(period)
    cutoff = datetime.now() - timedelta(days=max_days)
    posts = []

    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            upload_date = d.get("upload_date", "")
            if upload_date:
                try:
                    dt = datetime.strptime(upload_date, "%Y%m%d")
                    if dt < cutoff:
                        continue
                except ValueError:
                    pass

            view_count = int(d.get("view_count", 0) or 0)
            like_count = int(d.get("like_count", 0) or 0)
            comment_count = int(d.get("comment_count", 0) or 0)

            thumbnail = d.get("thumbnail", "")
            if not thumbnail and d.get("thumbnails"):
                thumbnail = d["thumbnails"][0].get("url", "")

            uploader = d.get("uploader", "") or d.get("channel", "")
            uploader_id = d.get("uploader_id", "") or d.get("channel_id", "")
            uploader_url = d.get("uploader_url", "") or d.get("channel_url", "")
            follower_count = int(d.get("channel_follower_count", 0) or 0)

            video_url = d.get("webpage_url", "") or d.get("url", "")

            posts.append({
                "id": d.get("id", ""),
                "title": (d.get("title", "") or d.get("description", ""))[:120],
                "description": d.get("description", ""),
                "url": video_url,
                "platform": "instagram",
                "views": view_count,
                "likes": like_count,
                "comments": comment_count,
                "shares": 0,
                "duration": int(d.get("duration", 0) or 0),
                "upload_date": upload_date,
                "thumbnail": thumbnail,
                "account": {
                    "name": uploader,
                    "id": uploader_id,
                    "url": uploader_url,
                    "followers": follower_count,
                },
            })
        except (json.JSONDecodeError, ValueError, KeyError):
            continue

    posts.sort(key=lambda x: x["views"], reverse=True)
    posts = posts[:count]

    if posts:
        _cache_set(keyword, "instagram", period, posts)

    return posts


def search_videos(keyword, platform="both", period="1m", count=10):
    """TikTok/Instagram両方を検索して統合結果を返す."""
    results = []

    if platform in ("both", "tiktok"):
        results.extend(search_tiktok_videos(keyword, period, count))

    if platform in ("both", "instagram"):
        results.extend(search_instagram_posts(keyword, period, count))

    results.sort(key=lambda x: x["views"], reverse=True)
    return results[:count]


def get_keyword_volume(keyword, platform="both", period="1m"):
    """キーワードのリアルボリューム(動画数・総再生数)を取得する.

    yt-dlpでTikTok検索を行い、指定期間内の動画数と総再生数を集計。
    """
    cache_key_str = f"vol:{keyword}:{platform}:{period}"
    cached = _cache_get(cache_key_str, platform, period)
    if cached:
        return cached

    max_days = _period_to_days(period)
    cutoff = datetime.now() - timedelta(days=max_days)
    total_views = 0
    total_likes = 0
    video_count = 0
    top_views = 0

    def _parse_results(stdout):
        nonlocal total_views, total_likes, video_count, top_views
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                upload_date = d.get("upload_date", "")
                if upload_date:
                    try:
                        dt = datetime.strptime(upload_date, "%Y%m%d")
                        if dt < cutoff:
                            continue
                    except ValueError:
                        pass
                views = int(d.get("view_count", 0) or 0)
                likes = int(d.get("like_count", 0) or 0)
                total_views += views
                total_likes += likes
                video_count += 1
                if views > top_views:
                    top_views = views
            except (json.JSONDecodeError, ValueError):
                continue

    if platform in ("both", "tiktok"):
        search_url = f"https://www.tiktok.com/search/video?q={keyword}"
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json", "--flat-playlist",
            "--no-download", "--no-warnings",
            "--playlist-end", "50",
            search_url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.stdout:
                _parse_results(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    if platform in ("both", "instagram"):
        tag = keyword.replace(" ", "").replace("　", "")
        search_url = f"https://www.instagram.com/explore/tags/{tag}/"
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json", "--flat-playlist",
            "--no-download", "--no-warnings",
            "--playlist-end", "50",
            search_url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if result.stdout:
                _parse_results(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    result_data = {
        "keyword": keyword,
        "period": period,
        "platform": platform,
        "video_count": video_count,
        "total_views": total_views,
        "total_likes": total_likes,
        "top_views": top_views,
        "avg_views": total_views // video_count if video_count > 0 else 0,
    }

    if video_count > 0:
        _cache_set(cache_key_str, platform, period, result_data)

    return result_data


def get_bulk_volumes(keywords, platform="both", period="1m"):
    """複数キーワードのボリュームを一括取得する."""
    results = []
    for kw in keywords:
        vol = get_keyword_volume(kw, platform, period)
        results.append(vol)
    return results
