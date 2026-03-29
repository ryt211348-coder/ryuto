"""ScrapeCreators APIを使ったTikTokリアルデータ取得."""

import json
import os
import hashlib
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta


CACHE_DIR = Path(__file__).parent.parent / ".search_cache"
CACHE_DIR.mkdir(exist_ok=True)

API_BASE = "https://api.scrapecreators.com"


def _get_api_key():
    key = os.environ.get("SCRAPECREATORS_API_KEY", "")
    if not key:
        config_path = Path(__file__).parent.parent / ".api_config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                key = data.get("scrapecreators_api_key", "")
            except Exception:
                pass
    return key


def _cache_key(prefix, keyword, platform, period):
    raw = f"{prefix}:{keyword}:{platform}:{period}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(prefix, keyword, platform, period, ttl=3600):
    key = _cache_key(prefix, keyword, platform, period)
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if time.time() - data.get("ts", 0) < ttl:
            return data.get("results")
    return None


def _cache_set(prefix, keyword, platform, period, results):
    key = _cache_key(prefix, keyword, platform, period)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({
        "ts": time.time(),
        "results": results
    }, ensure_ascii=False))


def _period_to_date_posted(period):
    """期間をScrapeCreators APIのdate_postedパラメータに変換."""
    # ScrapeCreators APIはdate_postedでフィルタ
    mapping = {
        "1w": "this-week",
        "1m": "this-month",
        "3m": "last-three-months",
        "6m": "last-six-months",
        "1y": "all-time",
    }
    return mapping.get(period, "this-month")


def _period_to_days(period):
    return {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365}.get(period, 30)


def search_tiktok_keyword(keyword, period="1m", count=10, sort_by="relevance"):
    """ScrapeCreators APIでTikTokキーワード検索."""
    cached = _cache_get("search", keyword, "tiktok", period)
    if cached:
        return cached

    api_key = _get_api_key()
    if not api_key:
        return []

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }
    params = {
        "query": keyword,
        "date_posted": _period_to_date_posted(period),
        "sort_by": sort_by,
        "region": "JP",
    }

    all_videos = []
    cursor = None

    # ページネーションで必要数取得
    for _ in range(3):  # 最大3ページ
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(
                f"{API_BASE}/v1/tiktok/search/keyword",
                headers=headers,
                params=params,
                timeout=30,
            )
            if resp.status_code != 200:
                break

            data = resp.json()
            items = data.get("search_item_list") or data.get("data", {}).get("search_item_list") or []

            for item in items:
                info = item.get("aweme_info") or item
                stats = info.get("statistics") or info.get("stats") or {}
                author = info.get("author") or {}

                create_time = info.get("create_time", "")
                if isinstance(create_time, (int, float)):
                    create_time = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
                elif isinstance(create_time, str) and "T" in create_time:
                    create_time = create_time[:10]

                video_id = str(info.get("id") or info.get("aweme_id", ""))
                author_id = str(author.get("unique_id") or author.get("uid", ""))

                # サムネイル
                cover = ""
                video_obj = info.get("video") or {}
                if video_obj.get("cover"):
                    cover_data = video_obj["cover"]
                    if isinstance(cover_data, dict):
                        urls = cover_data.get("url_list", [])
                        cover = urls[0] if urls else ""
                    elif isinstance(cover_data, str):
                        cover = cover_data
                if not cover:
                    cover = video_obj.get("dynamic_cover", {}).get("url_list", [""])[0] if isinstance(video_obj.get("dynamic_cover"), dict) else ""

                all_videos.append({
                    "id": video_id,
                    "title": (info.get("desc") or "")[:120],
                    "description": info.get("desc") or "",
                    "url": f"https://www.tiktok.com/@{author_id}/video/{video_id}",
                    "platform": "tiktok",
                    "views": int(stats.get("play_count", 0) or 0),
                    "likes": int(stats.get("digg_count", 0) or 0),
                    "comments": int(stats.get("comment_count", 0) or 0),
                    "shares": int(stats.get("share_count", 0) or 0),
                    "duration": int(video_obj.get("duration", 0) or 0),
                    "upload_date": create_time,
                    "thumbnail": cover,
                    "account": {
                        "name": author.get("nickname", ""),
                        "id": author_id,
                        "url": f"https://www.tiktok.com/@{author_id}",
                        "followers": int(author.get("follower_count", 0) or 0),
                        "following": int(author.get("following_count", 0) or 0),
                        "total_likes": int(author.get("total_favorited", 0) or 0),
                        "avatar": (author.get("avatar_thumb", {}) or {}).get("url_list", [""])[0] if isinstance(author.get("avatar_thumb"), dict) else "",
                    },
                })

            cursor = data.get("cursor")
            if not cursor or len(all_videos) >= count:
                break

        except Exception as e:
            print(f"ScrapeCreators API error: {e}")
            break

    # 再生数でソート
    all_videos.sort(key=lambda x: x["views"], reverse=True)
    result = all_videos[:count]

    if result:
        _cache_set("search", keyword, "tiktok", period, result)

    return result


def search_videos(keyword, platform="both", period="1m", count=10):
    """キーワード検索でリアル動画データを取得."""
    if platform in ("both", "tiktok"):
        return search_tiktok_keyword(keyword, period, count)
    # Instagram検索はScrapeCreatorsでは未対応のためTikTokのみ
    return search_tiktok_keyword(keyword, period, count)


def get_keyword_volume(keyword, platform="both", period="1m"):
    """キーワードのリアルボリューム(動画数・総再生数)を取得."""
    cached = _cache_get("vol", keyword, platform, period)
    if cached:
        return cached

    videos = search_tiktok_keyword(keyword, period, count=30, sort_by="relevance")

    total_views = sum(v["views"] for v in videos)
    total_likes = sum(v["likes"] for v in videos)
    top_views = max((v["views"] for v in videos), default=0)

    result = {
        "keyword": keyword,
        "period": period,
        "platform": platform,
        "video_count": len(videos),
        "total_views": total_views,
        "total_likes": total_likes,
        "top_views": top_views,
        "avg_views": total_views // len(videos) if videos else 0,
    }

    if videos:
        _cache_set("vol", keyword, platform, period, result)

    return result


def get_bulk_volumes(keywords, platform="both", period="1m"):
    """複数キーワードのボリュームを一括取得."""
    return [get_keyword_volume(kw, platform, period) for kw in keywords]
