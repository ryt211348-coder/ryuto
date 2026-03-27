"""リサーチツール用APIルート."""

import random
from flask import Blueprint, render_template, jsonify, request

from .keywords_food import FOOD_TAXONOMY
from .keywords_beauty import BEAUTY_TAXONOMY

research_bp = Blueprint("research", __name__)

# 期間フィルターの倍率 (直近ほどボリューム高め)
PERIOD_MULTIPLIERS = {
    "1week": 1.5,
    "1month": 1.2,
    "3months": 1.0,
    "6months": 0.85,
    "1year": 0.7,
}

# プラットフォーム補正
PLATFORM_MULTIPLIERS = {
    "both": 1.0,
    "tiktok": 0.65,
    "instagram": 0.55,
}


def _apply_filters(volume, period, platform):
    """期間・プラットフォームに応じてボリュームを補正."""
    p_mult = PERIOD_MULTIPLIERS.get(period, 1.0)
    pl_mult = PLATFORM_MULTIPLIERS.get(platform, 1.0)
    # 少しランダム性を加えてリアルに見せる
    jitter = random.uniform(0.9, 1.1)
    return int(volume * p_mult * pl_mult * jitter)


def _build_level1(taxonomy, period, platform):
    """Level 1: 最上位カテゴリ一覧を返す."""
    nodes = []
    for name, data in taxonomy.items():
        nodes.append({
            "name": name,
            "volume": _apply_filters(data["volume"], period, platform),
            "has_children": bool(data.get("children")),
            "child_count": len(data.get("children", {})),
        })
    nodes.sort(key=lambda x: x["volume"], reverse=True)
    return nodes


def _build_level2(taxonomy, category, period, platform):
    """Level 2: 指定カテゴリの子ノード一覧を返す."""
    cat_data = taxonomy.get(category, {})
    children = cat_data.get("children", {})
    nodes = []
    for name, data in children.items():
        nodes.append({
            "name": name,
            "volume": _apply_filters(data["volume"], period, platform),
            "has_children": bool(data.get("children")),
            "child_count": len(data.get("children", {})),
            "parent": category,
        })
    nodes.sort(key=lambda x: x["volume"], reverse=True)
    return nodes


def _build_level3(taxonomy, category, subcategory, period, platform):
    """Level 3: 最下層の具体キーワード一覧を返す."""
    cat_data = taxonomy.get(category, {})
    sub_data = cat_data.get("children", {}).get(subcategory, {})
    children = sub_data.get("children", {})
    nodes = []
    for name, data in children.items():
        vol = data if isinstance(data, int) else data.get("volume", 0)
        nodes.append({
            "name": name,
            "volume": _apply_filters(vol, period, platform),
            "has_children": False,
            "parent": subcategory,
            "grandparent": category,
        })
    nodes.sort(key=lambda x: x["volume"], reverse=True)
    return nodes


def _get_taxonomy(genre):
    if genre == "food":
        return FOOD_TAXONOMY
    elif genre == "beauty":
        return BEAUTY_TAXONOMY
    return {}


# サンプル動画データ生成
def _generate_sample_videos(keyword, period, platform, count=20):
    """キーワードに関連するサンプル動画データを生成."""
    platforms = ["tiktok", "instagram"] if platform == "both" else [platform]
    videos = []
    for i in range(count):
        plat = random.choice(platforms)
        days_map = {"1week": 7, "1month": 30, "3months": 90, "6months": 180, "1year": 365}
        max_days = days_map.get(period, 30)
        days_ago = random.randint(0, max_days)
        views = random.randint(10000, 5000000)
        videos.append({
            "id": f"vid_{i}_{random.randint(1000,9999)}",
            "platform": plat,
            "title": f"【{keyword}】バズり動画 #{i+1}",
            "views": views,
            "likes": int(views * random.uniform(0.03, 0.15)),
            "comments": int(views * random.uniform(0.005, 0.03)),
            "shares": int(views * random.uniform(0.01, 0.05)),
            "days_ago": days_ago,
            "account": f"@creator_{random.randint(100,999)}",
            "account_followers": random.randint(1000, 1000000),
            "engagement_rate": round(random.uniform(2.0, 15.0), 1),
            "hashtags": [keyword, f"#{keyword}おすすめ", "#バズり", "#おすすめ"],
        })
    videos.sort(key=lambda x: x["views"], reverse=True)
    return videos


def _generate_sample_accounts(keyword, period, platform, count=15):
    """キーワードに関連するサンプルアカウントデータを生成."""
    platforms = ["tiktok", "instagram"] if platform == "both" else [platform]
    accounts = []
    for i in range(count):
        plat = random.choice(platforms)
        followers = random.randint(5000, 2000000)
        growth = round(random.uniform(-5.0, 50.0), 1)
        accounts.append({
            "id": f"acc_{i}",
            "platform": plat,
            "username": f"@{keyword.replace(' ', '_')}_{random.randint(10,99)}",
            "display_name": f"{keyword}マスター{i+1}",
            "followers": followers,
            "following": random.randint(100, 5000),
            "posts": random.randint(50, 2000),
            "avg_views": random.randint(5000, 500000),
            "engagement_rate": round(random.uniform(1.5, 12.0), 1),
            "growth_rate": growth,
            "top_keyword": keyword,
            "related_keywords": [keyword, f"{keyword}レビュー", f"{keyword}おすすめ"],
        })
    accounts.sort(key=lambda x: x["growth_rate"], reverse=True)
    return accounts


# --- ルート定義 ---

@research_bp.route("/research")
def research_page():
    return render_template("research.html")


@research_bp.route("/api/research/keywords")
def get_keywords():
    """マインドマップ用キーワードデータを返す."""
    genre = request.args.get("genre", "food")  # food or beauty
    level = int(request.args.get("level", 1))
    category = request.args.get("category", "")
    subcategory = request.args.get("subcategory", "")
    period = request.args.get("period", "1month")
    platform = request.args.get("platform", "both")

    taxonomy = _get_taxonomy(genre)

    if level == 1:
        nodes = _build_level1(taxonomy, period, platform)
    elif level == 2 and category:
        nodes = _build_level2(taxonomy, category, period, platform)
    elif level == 3 and category and subcategory:
        nodes = _build_level3(taxonomy, category, subcategory, period, platform)
    else:
        nodes = []

    return jsonify({"genre": genre, "level": level, "period": period,
                     "platform": platform, "nodes": nodes})


@research_bp.route("/api/research/videos")
def get_videos():
    """キーワードに関連する動画一覧を返す."""
    keyword = request.args.get("keyword", "")
    period = request.args.get("period", "1month")
    platform = request.args.get("platform", "both")
    count = min(int(request.args.get("count", 20)), 50)

    videos = _generate_sample_videos(keyword, period, platform, count)
    return jsonify({"keyword": keyword, "videos": videos})


@research_bp.route("/api/research/accounts")
def get_accounts():
    """キーワードに関連するアカウント一覧を返す."""
    keyword = request.args.get("keyword", "")
    period = request.args.get("period", "1month")
    platform = request.args.get("platform", "both")
    count = min(int(request.args.get("count", 15)), 30)

    accounts = _generate_sample_accounts(keyword, period, platform, count)
    return jsonify({"keyword": keyword, "accounts": accounts})
