"""レストラン比較ツール - Webインターフェース.

食べログ・ホットペッパー・Google口コミを総合的に比較し、
口コミ件数と評価の信頼性スコアで最適なレストランを提案する。
"""

import copy

from flask import Flask, render_template, request, jsonify

from restaurant_finder.mock_data import MOCK_RESTAURANTS, GENRES, ATMOSPHERES, AREAS
from restaurant_finder.scorer import compute_overall_score, rank_restaurants

app = Flask(__name__)


@app.route("/")
@app.route("/restaurant")
def restaurant_index():
    """レストラン検索ページを表示."""
    return render_template("restaurant.html")


@app.route("/api/restaurant/options")
def get_options():
    """フィルタ用の選択肢を返す."""
    return jsonify({
        "genres": GENRES,
        "atmospheres": ATMOSPHERES,
        "areas": AREAS,
    })


@app.route("/api/restaurant/search", methods=["POST"])
def search_restaurants():
    """レストランを検索・フィルタリング・スコア順で返す."""
    data = request.get_json() or {}

    area = data.get("area", "")
    genre = data.get("genre", "")
    atmosphere = data.get("atmosphere", "")
    budget_min = data.get("budget_min", 0)
    budget_max = data.get("budget_max", 0)
    party_size = data.get("party_size", 0)
    reservation_status = data.get("reservation_status", "")
    has_private_room = data.get("has_private_room", False)
    sort_by = data.get("sort_by", "score")  # "score", "price_low", "price_high", "review_count"

    # フィルタリング
    results = []
    for r in MOCK_RESTAURANTS:
        # エリアフィルタ
        if area and r["area"] != area:
            continue
        # ジャンルフィルタ
        if genre and r["genre"] != genre:
            continue
        # 雰囲気フィルタ
        if atmosphere and atmosphere not in r.get("atmosphere_tags", []):
            continue
        # 予算フィルタ
        if budget_min and r["price_max"] < budget_min:
            continue
        if budget_max and r["price_min"] > budget_max:
            continue
        # 人数フィルタ
        if party_size and r["capacity"] < party_size:
            continue
        # 予約状況フィルタ
        if reservation_status and r["reservation_status"] != reservation_status:
            continue
        # 個室フィルタ
        if has_private_room and not r.get("has_private_room", False):
            continue

        # ディープコピーしてスコアを付与
        item = copy.deepcopy(r)
        item["overall_score"] = compute_overall_score(item.get("reviews", []))
        results.append(item)

    # ソート
    if sort_by == "price_low":
        results.sort(key=lambda x: x["price_min"])
    elif sort_by == "price_high":
        results.sort(key=lambda x: x["price_max"], reverse=True)
    elif sort_by == "review_count":
        results.sort(
            key=lambda x: sum(rv["review_count"] for rv in x.get("reviews", [])),
            reverse=True,
        )
    else:
        # デフォルト: 信頼性スコア順
        results.sort(key=lambda x: x["overall_score"], reverse=True)

    return jsonify({
        "count": len(results),
        "restaurants": results,
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)
