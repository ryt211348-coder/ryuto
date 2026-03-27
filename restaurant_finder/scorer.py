"""レストランの信頼性スコアリングアルゴリズム.

口コミ件数が少ないと評価が高くなりがちな問題を解決するため、
ベイズ平均（Bayesian Average）を使って「信頼性のある総合スコア」を算出する。

スコア = (v / (v + m)) * R + (m / (v + m)) * C

  R = そのレストランの平均評価
  v = そのレストランの口コミ件数
  m = 信頼に必要な最低口コミ数（デフォルト: 30）
  C = 全体の平均評価（事前分布の平均）

これにより、口コミが少ない店は全体平均に引っ張られ、
口コミが多く評価も高い店が上位に来る。
"""

# 信頼に必要な最低口コミ数
DEFAULT_MIN_REVIEWS = 30

# 全サイトの平均的な評価（事前分布）
DEFAULT_PRIOR_MEAN = 3.3


def bayesian_score(rating: float, review_count: int,
                   prior_mean: float = DEFAULT_PRIOR_MEAN,
                   min_reviews: int = DEFAULT_MIN_REVIEWS) -> float:
    """ベイズ平均で単一サイトの信頼性スコアを計算."""
    if review_count == 0:
        return prior_mean
    v = review_count
    m = min_reviews
    return (v / (v + m)) * rating + (m / (v + m)) * prior_mean


# 各サイトの重み（食べログはグルメ特化で信頼性高め）
SITE_WEIGHTS = {
    "tabelog": 0.40,
    "hotpepper": 0.25,
    "google": 0.35,
}


def compute_overall_score(reviews: list) -> float:
    """複数サイトの評価を統合して総合スコアを算出.

    Args:
        reviews: [{"source": "tabelog", "rating": 3.8, "review_count": 150}, ...]

    Returns:
        0.0 ~ 5.0 の総合スコア
    """
    if not reviews:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for r in reviews:
        source = r.get("source", "")
        rating = r.get("rating", 0.0)
        count = r.get("review_count", 0)
        weight = SITE_WEIGHTS.get(source, 0.2)

        site_score = bayesian_score(rating, count)
        weighted_sum += site_score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 2)


def rank_restaurants(restaurants: list) -> list:
    """レストランリストをスコア順にソート."""
    for r in restaurants:
        r["overall_score"] = compute_overall_score(r.get("reviews", []))
    return sorted(restaurants, key=lambda x: x["overall_score"], reverse=True)
