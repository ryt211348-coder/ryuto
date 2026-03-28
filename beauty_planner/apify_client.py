"""Apify連携モジュール - TikTok/Instagramデータ自動収集."""

import requests
import time


class ApifyClient:
    """Apify APIクライアント."""

    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, api_token):
        self.token = api_token

    def _run_actor(self, actor_id, run_input, timeout=300):
        """Actorを同期実行して結果を取得."""
        url = f"{self.BASE_URL}/acts/{actor_id}/runs"
        params = {"token": self.token}
        resp = requests.post(url, json=run_input, params=params, timeout=30)
        resp.raise_for_status()
        run_data = resp.json()["data"]
        run_id = run_data["id"]

        # 完了まで待機
        status_url = f"{self.BASE_URL}/actor-runs/{run_id}"
        start = time.time()
        while time.time() - start < timeout:
            r = requests.get(status_url, params=params, timeout=15)
            r.raise_for_status()
            status = r.json()["data"]["status"]
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"Apify Actor failed: {status}")
            time.sleep(3)
        else:
            raise TimeoutError("Apify Actor timed out")

        # 結果取得
        dataset_id = r.json()["data"]["defaultDatasetId"]
        items_url = f"{self.BASE_URL}/datasets/{dataset_id}/items"
        items_resp = requests.get(items_url, params=params, timeout=30)
        items_resp.raise_for_status()
        return items_resp.json()

    def scrape_tiktok_profile(self, usernames, max_videos=30):
        """TikTokアカウントの動画データを取得.

        Args:
            usernames: ユーザー名リスト (例: ["@tettei_re"])
            max_videos: アカウントあたりの最大取得動画数

        Returns:
            動画データのリスト
        """
        # clockworks/tiktok-scraper を使用
        actor_id = "clockworks~tiktok-scraper"
        run_input = {
            "profiles": [u.lstrip("@") for u in usernames],
            "resultsPerPage": max_videos,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        return self._run_actor(actor_id, run_input)

    def scrape_tiktok_hashtag(self, hashtags, max_videos=50):
        """TikTokハッシュタグ検索.

        Args:
            hashtags: ハッシュタグリスト (例: ["プチプラコスメ"])
            max_videos: ハッシュタグあたりの最大取得動画数

        Returns:
            動画データのリスト
        """
        actor_id = "clockworks~tiktok-scraper"
        run_input = {
            "hashtags": hashtags,
            "resultsPerPage": max_videos,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        return self._run_actor(actor_id, run_input)

    def scrape_tiktok_keyword(self, keyword, max_videos=50):
        """TikTokキーワード検索.

        Args:
            keyword: 検索キーワード
            max_videos: 最大取得動画数

        Returns:
            動画データのリスト
        """
        actor_id = "clockworks~tiktok-scraper"
        run_input = {
            "searchQueries": [keyword],
            "resultsPerPage": max_videos,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }
        return self._run_actor(actor_id, run_input)

    def scrape_instagram_profile(self, usernames, max_posts=30):
        """Instagramアカウントの投稿データを取得.

        Args:
            usernames: ユーザー名リスト
            max_posts: アカウントあたりの最大取得投稿数

        Returns:
            投稿データのリスト
        """
        actor_id = "apify~instagram-scraper"
        run_input = {
            "usernames": [u.lstrip("@") for u in usernames],
            "resultsLimit": max_posts,
            "resultsType": "posts",
        }
        return self._run_actor(actor_id, run_input)

    def scrape_instagram_hashtag(self, hashtag, max_posts=50):
        """Instagramハッシュタグ検索.

        Args:
            hashtag: ハッシュタグ
            max_posts: 最大取得投稿数

        Returns:
            投稿データのリスト
        """
        actor_id = "apify~instagram-scraper"
        run_input = {
            "hashtags": [hashtag.lstrip("#")],
            "resultsLimit": max_posts,
            "resultsType": "posts",
        }
        return self._run_actor(actor_id, run_input)


def normalize_tiktok_data(raw_items):
    """TikTokの生データを統一フォーマットに変換."""
    results = []
    for item in raw_items:
        results.append({
            "platform": "TikTok",
            "video_id": item.get("id", ""),
            "url": item.get("webVideoUrl", "") or item.get("url", ""),
            "author": item.get("authorMeta", {}).get("name", "") or item.get("author", ""),
            "author_name": item.get("authorMeta", {}).get("nickName", ""),
            "description": item.get("text", "") or item.get("description", ""),
            "views": item.get("playCount", 0) or item.get("views", 0),
            "likes": item.get("diggCount", 0) or item.get("likes", 0),
            "comments": item.get("commentCount", 0) or item.get("comments", 0),
            "shares": item.get("shareCount", 0) or item.get("shares", 0),
            "duration": item.get("videoMeta", {}).get("duration", 0) or item.get("duration", 0),
            "created_at": item.get("createTimeISO", "") or item.get("createTime", ""),
            "hashtags": [h.get("name", "") for h in item.get("hashtags", [])],
            "music": item.get("musicMeta", {}).get("musicName", ""),
            "download_url": item.get("videoUrl", ""),
        })
    return results


def normalize_instagram_data(raw_items):
    """Instagramの生データを統一フォーマットに変換."""
    results = []
    for item in raw_items:
        results.append({
            "platform": "Instagram",
            "video_id": item.get("id", ""),
            "url": item.get("url", ""),
            "author": item.get("ownerUsername", ""),
            "author_name": item.get("ownerFullName", ""),
            "description": item.get("caption", ""),
            "views": item.get("videoViewCount", 0) or item.get("viewCount", 0),
            "likes": item.get("likesCount", 0),
            "comments": item.get("commentsCount", 0),
            "shares": 0,
            "duration": item.get("videoDuration", 0),
            "created_at": item.get("timestamp", ""),
            "hashtags": item.get("hashtags", []),
            "music": "",
            "download_url": item.get("videoUrl", "") or item.get("displayUrl", ""),
        })
    return results
