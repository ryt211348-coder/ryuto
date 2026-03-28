"""トレンド分析ロジック - Apify収集データを自動集計（API不要）."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta


def filter_by_period(videos, period):
    """期間フィルター."""
    now = datetime.now()
    cutoffs = {
        "1week": timedelta(days=7),
        "3months": timedelta(days=90),
        "6months": timedelta(days=180),
        "1year": timedelta(days=365),
    }
    if period == "over1year":
        cutoff_date = now - timedelta(days=365)
        return [v for v in videos if _parse_date(v.get("created_at", "")) < cutoff_date]

    delta = cutoffs.get(period)
    if not delta:
        return videos
    cutoff_date = now - delta
    return [v for v in videos if _parse_date(v.get("created_at", "")) >= cutoff_date]


def filter_by_views(videos, min_views):
    """再生数フィルター."""
    if min_views <= 0:
        return videos
    return [v for v in videos if (v.get("views") or 0) >= min_views]


def _parse_date(date_str):
    """日付文字列をパース."""
    if not date_str:
        return datetime.min
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%s"]:
        try:
            if fmt == "%s":
                return datetime.fromtimestamp(int(date_str))
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError, OSError):
            continue
    return datetime.min


def analyze_trends(videos, period="3months", min_views=0):
    """収集データからトレンドを自動分析.

    Args:
        videos: 正規化済み動画データリスト
        period: 期間フィルター
        min_views: 最低再生数

    Returns:
        分析結果辞書
    """
    # フィルター適用
    filtered = filter_by_period(videos, period)
    filtered = filter_by_views(filtered, min_views)

    if not filtered:
        return {"error": "条件に合う動画がありません", "total_videos": 0}

    # --- ハッシュタグ集計 ---
    hashtag_counter = Counter()
    hashtag_views = defaultdict(int)
    for v in filtered:
        for h in v.get("hashtags", []):
            if h:
                hashtag_counter[h] += 1
                hashtag_views[h] += v.get("views", 0)

    hot_keywords = []
    for tag, count in hashtag_counter.most_common(20):
        avg_views = hashtag_views[tag] // count if count > 0 else 0
        hot_keywords.append({
            "keyword": f"#{tag}",
            "count": count,
            "total_views": hashtag_views[tag],
            "avg_views": avg_views,
            "volume": "大" if count >= 5 else "中" if count >= 2 else "小",
        })

    # --- 人気動画ランキング ---
    sorted_videos = sorted(filtered, key=lambda v: v.get("views", 0), reverse=True)
    trending_videos = []
    for i, v in enumerate(sorted_videos[:15]):
        engagement = (v.get("likes", 0) + v.get("comments", 0) + v.get("shares", 0))
        engagement_rate = (engagement / v["views"] * 100) if v.get("views") else 0
        trending_videos.append({
            "rank": i + 1,
            "url": v.get("url", ""),
            "author": v.get("author", ""),
            "description": (v.get("description", "") or "")[:100],
            "views": v.get("views", 0),
            "likes": v.get("likes", 0),
            "comments": v.get("comments", 0),
            "shares": v.get("shares", 0),
            "engagement_rate": round(engagement_rate, 2),
            "duration": v.get("duration", 0),
            "created_at": v.get("created_at", ""),
            "platform": v.get("platform", ""),
            "hashtags": v.get("hashtags", [])[:5],
        })

    # --- アカウント別分析 ---
    account_data = defaultdict(lambda: {
        "videos": [], "total_views": 0, "total_likes": 0,
        "total_comments": 0, "platform": "",
    })
    for v in filtered:
        author = v.get("author", "unknown")
        account_data[author]["videos"].append(v)
        account_data[author]["total_views"] += v.get("views", 0)
        account_data[author]["total_likes"] += v.get("likes", 0)
        account_data[author]["total_comments"] += v.get("comments", 0)
        account_data[author]["platform"] = v.get("platform", "")

    account_insights = []
    for author, data in sorted(account_data.items(),
                                key=lambda x: x[1]["total_views"], reverse=True)[:10]:
        vids = data["videos"]
        dates = [_parse_date(v.get("created_at", "")) for v in vids]
        valid_dates = [d for d in dates if d != datetime.min]

        last_post = max(valid_dates).strftime("%Y-%m-%d") if valid_dates else "-"
        if len(valid_dates) >= 2:
            span_days = (max(valid_dates) - min(valid_dates)).days or 1
            monthly_posts = round(len(vids) / (span_days / 30), 1)
        else:
            monthly_posts = len(vids)

        avg_views = data["total_views"] // len(vids) if vids else 0
        best_video = max(vids, key=lambda v: v.get("views", 0))

        account_insights.append({
            "account_name": author,
            "platform": data["platform"],
            "video_count": len(vids),
            "total_views": data["total_views"],
            "avg_views": avg_views,
            "total_likes": data["total_likes"],
            "total_comments": data["total_comments"],
            "last_post_date": last_post,
            "monthly_posts": monthly_posts,
            "best_video_url": best_video.get("url", ""),
            "best_video_views": best_video.get("views", 0),
            "best_video_desc": (best_video.get("description", "") or "")[:80],
        })

    # --- エンゲージメント高い動画 ---
    high_engagement = sorted(
        [v for v in filtered if v.get("views", 0) > 0],
        key=lambda v: (
            (v.get("likes", 0) + v.get("comments", 0) + v.get("shares", 0))
            / v["views"]
        ),
        reverse=True,
    )[:10]

    high_engagement_list = []
    for v in high_engagement:
        eng = v.get("likes", 0) + v.get("comments", 0) + v.get("shares", 0)
        rate = eng / v["views"] * 100 if v.get("views") else 0
        high_engagement_list.append({
            "url": v.get("url", ""),
            "author": v.get("author", ""),
            "description": (v.get("description", "") or "")[:80],
            "views": v.get("views", 0),
            "engagement_rate": round(rate, 2),
            "likes": v.get("likes", 0),
            "comments": v.get("comments", 0),
        })

    # --- 統計サマリー ---
    total_views = sum(v.get("views", 0) for v in filtered)
    total_likes = sum(v.get("likes", 0) for v in filtered)
    total_comments = sum(v.get("comments", 0) for v in filtered)
    avg_views = total_views // len(filtered) if filtered else 0

    period_text = {
        "1week": "直近1週間", "3months": "直近3ヶ月",
        "6months": "直近6ヶ月", "1year": "直近1年",
        "over1year": "1年以上前",
    }.get(period, period)

    return {
        "total_videos": len(filtered),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_views": avg_views,
        "period": period_text,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "trending_videos": trending_videos,
        "hot_keywords": hot_keywords,
        "account_insights": account_insights,
        "high_engagement": high_engagement_list,
    }
