"""Apify TikTok Search APIを使ったリアルデータ取得."""

import json
import os
import hashlib
import time
import requests
from pathlib import Path


CACHE_DIR = Path(__file__).parent.parent / ".search_cache"
CACHE_DIR.mkdir(exist_ok=True)

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "novi~tiktok-search-api"  # 無料枠で使えるActor


def _get_api_token():
    token = os.environ.get("APIFY_API_TOKEN", "")
    if not token:
        config_path = Path(__file__).parent.parent / ".api_config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                token = data.get("apify_api_token", "")
            except Exception:
                pass
    return token


def _cache_key(prefix, keyword, period):
    raw = f"{prefix}:{keyword}:{period}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(prefix, keyword, period, ttl=3600):
    key = _cache_key(prefix, keyword, period)
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if time.time() - data.get("ts", 0) < ttl:
            return data.get("results")
    return None


def _cache_set(prefix, keyword, period, results):
    key = _cache_key(prefix, keyword, period)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({
        "ts": time.time(),
        "results": results
    }, ensure_ascii=False))


def _period_to_apify(period):
    """期間をApifyのdatePostedパラメータに変換."""
    return {
        "1w": "last_7_days",
        "1m": "last_30_days",
        "3m": "last_90_days",
        "6m": "last_180_days",
        "1y": "all_time",
    }.get(period, "last_30_days")


def search_tiktok(keyword, period="1m", count=10, sort_by="relevance"):
    """Apify経由でTikTokキーワード検索（同期実行）."""
    cached = _cache_get("search", keyword, period)
    if cached:
        return cached

    token = _get_api_token()
    if not token:
        return []

    run_input = {
        "query": keyword,
        "datePosted": _period_to_apify(period),
        "sortBy": sort_by,
        "region": "JP",
        "maxResults": count,
    }

    try:
        # 同期実行してデータセットを直接取得
        resp = requests.post(
            f"{APIFY_BASE}/acts/{ACTOR_ID}/run-sync-get-dataset-items",
            params={"token": token},
            json=run_input,
            timeout=120,
        )

        if resp.status_code != 200 and resp.status_code != 201:
            print(f"Apify error: {resp.status_code} - {resp.text[:300]}")
            return []

        items = resp.json()
        if not isinstance(items, list):
            items = items.get("items", []) or items.get("data", []) or []

    except Exception as e:
        print(f"Apify request failed: {e}")
        return []

    videos = []
    for item in items:
        try:
            # Apifyの出力形式に対応
            stats = item.get("statistics") or item.get("stats") or {}
            author = item.get("author") or item.get("authorMeta") or {}
            video_info = item.get("video") or item.get("videoMeta") or {}

            video_id = str(item.get("id") or item.get("aweme_id") or "")
            author_id = str(author.get("unique_id") or author.get("uniqueId") or author.get("id") or "")

            views = int(stats.get("play_count") or stats.get("playCount") or item.get("playCount") or item.get("views") or 0)
            likes = int(stats.get("digg_count") or stats.get("diggCount") or item.get("diggCount") or item.get("likes") or 0)
            comments = int(stats.get("comment_count") or stats.get("commentCount") or item.get("commentCount") or item.get("comments") or 0)
            shares = int(stats.get("share_count") or stats.get("shareCount") or item.get("shareCount") or item.get("shares") or 0)

            create_time = item.get("create_time") or item.get("createTime") or item.get("createTimeISO") or ""
            if isinstance(create_time, (int, float)):
                from datetime import datetime
                create_time = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
            elif isinstance(create_time, str) and "T" in create_time:
                create_time = create_time[:10]

            # サムネイル
            cover = ""
            if isinstance(video_info.get("cover"), dict):
                cover = (video_info["cover"].get("url_list") or [""])[0]
            elif isinstance(video_info.get("cover"), str):
                cover = video_info["cover"]
            if not cover:
                cover = item.get("cover") or item.get("thumbnail") or ""

            # URL
            url = item.get("url") or item.get("webVideoUrl") or f"https://www.tiktok.com/@{author_id}/video/{video_id}"

            followers = int(author.get("follower_count") or author.get("followerCount") or author.get("fans") or 0)
            avatar = ""
            if isinstance(author.get("avatar_thumb"), dict):
                avatar = (author["avatar_thumb"].get("url_list") or [""])[0]
            elif isinstance(author.get("avatar"), str):
                avatar = author["avatar"]

            videos.append({
                "id": video_id,
                "title": (item.get("desc") or item.get("text") or item.get("description") or "")[:120],
                "url": url,
                "platform": "tiktok",
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "duration": int(video_info.get("duration") or item.get("duration") or 0),
                "upload_date": create_time,
                "thumbnail": cover,
                "account": {
                    "name": author.get("nickname") or author.get("name") or "",
                    "id": author_id,
                    "url": f"https://www.tiktok.com/@{author_id}",
                    "followers": followers,
                    "avatar": avatar,
                },
            })
        except Exception as e:
            print(f"Parse error: {e}")
            continue

    videos.sort(key=lambda x: x["views"], reverse=True)
    result = videos[:count]

    if result:
        _cache_set("search", keyword, period, result)

    return result


def search_tiktok_keyword_raw(keyword, period="1m"):
    """デバッグ: APIの生レスポンスを返す."""
    token = _get_api_token()
    if not token:
        return {"error": "Apify API token not set"}

    run_input = {
        "query": keyword,
        "datePosted": _period_to_apify(period),
        "sortBy": "relevance",
        "region": "JP",
        "maxResults": 3,
    }

    try:
        resp = requests.post(
            f"{APIFY_BASE}/acts/{ACTOR_ID}/run-sync-get-dataset-items",
            params={"token": token},
            json=run_input,
            timeout=60,
        )
        return {"status": resp.status_code, "response": resp.json() if resp.status_code in (200, 201) else resp.text[:500]}
    except Exception as e:
        return {"error": str(e)}


def search_videos(keyword, platform="both", period="1m", count=10):
    """キーワード検索でリアル動画データを取得."""
    return search_tiktok(keyword, period, count)


def get_keyword_volume(keyword, platform="both", period="1m"):
    """キーワードのリアルボリューム取得."""
    cached = _cache_get("vol", keyword, period)
    if cached:
        return cached

    videos = search_tiktok(keyword, period, count=20, sort_by="relevance")

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
        _cache_set("vol", keyword, period, result)

    return result


def get_bulk_volumes(keywords, platform="both", period="1m"):
    """複数キーワードのボリュームを一括取得."""
    return [get_keyword_volume(kw, platform, period) for kw in keywords]
