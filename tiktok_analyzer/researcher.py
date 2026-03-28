"""TikTok リサーチャー - トレンド自動発見・エンゲージメント分析・アカウント属人性チェック."""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests as http_requests
from rich.console import Console

console = Console()


# ===== トレンドキーワード候補（スキンケア系） =====
TREND_SEED_KEYWORDS = [
    # 肌悩み系
    "ニキビ スキンケア", "毛穴 ケア", "シミ 消す", "乾燥肌 保湿", "美白 透明感",
    "赤み 敏感肌", "ニキビ跡 治し方", "毛穴 黒ずみ", "いちご鼻", "肌荒れ 原因",
    "テカリ 皮脂", "シワ たるみ", "くすみ 対策", "角栓 除去",
    # ハウツー系
    "スキンケア ルーティン", "正しい洗顔", "化粧水 塗り方", "美容液 効果",
    "日焼け止め 塗り方", "クレンジング 方法",
    # トレンド系
    "韓国 スキンケア", "ドラコス おすすめ", "プチプラ スキンケア",
    "美容 ライフハック", "擬人化 スキンケア", "コスメ 擬人化",
    # 成分系
    "レチノール 使い方", "ナイアシンアミド", "ビタミンC 美容液", "CICA 効果",
]


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
    # エンゲージメント指標（後で計算）
    engagement_rate: float = 0.0      # (likes+comments+shares) / views
    comment_rate: float = 0.0         # comments / views
    like_rate: float = 0.0            # likes / views
    engagement_score: float = 0.0     # 総合スコア


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
    # 属人性分析
    activity_months: int = 0          # 活動期間（月）
    avg_views_per_video: int = 0      # 動画あたり平均再生数
    is_personality_driven: bool = False  # 属人アカウントか
    personality_reason: str = ""       # 判定理由
    trending_products: list = field(default_factory=list)  # 扱っているトレンド商品


@dataclass
class TrendKeyword:
    """トレンドキーワード候補."""
    keyword: str = ""
    estimated_volume: int = 0       # 推定ボリューム（検索結果の動画再生数合計）
    avg_views: int = 0              # 平均再生数
    avg_engagement: float = 0.0     # 平均エンゲージメント率
    top_video_views: int = 0        # トップ動画の再生数
    video_count: int = 0            # 見つかった動画数
    sample_hooks: list = field(default_factory=list)  # サンプルフック


# ===== トレンドキーワード自動発見 =====

def discover_trending_keywords(period_months: int = 3,
                               min_views: int = 500_000,
                               max_keywords: int = 10) -> list[TrendKeyword]:
    """スキンケア系のトレンドキーワードを自動発見する."""
    console.print("\n[bold cyan]トレンドキーワードを自動発見中...[/bold cyan]")
    results = []

    # まずAPIが使えるか素早くチェック（1キーワードだけ試す）
    api_available = False
    try:
        test_videos = search_tiktok_videos("ニキビ", min_views=0, period_months=12, max_results=3)
        if test_videos:
            api_available = True
            console.print("  [green]API接続OK[/green]")
    except Exception:
        pass

    if not api_available:
        # APIが使えない場合: ビルトインの参考データからキーワード候補を返す
        console.print("  [yellow]API未接続。参考データからキーワードを提示します。[/yellow]")
        from .reference_data import KEYWORD_REFERENCES
        for keyword, ref in list(KEYWORD_REFERENCES.items())[:max_keywords]:
            vids = ref.get("videos", [])
            total_views = sum(v.get("views", 0) for v in vids)
            top_views = max((v.get("views", 0) for v in vids), default=0)
            avg_views = total_views // len(vids) if vids else 0
            hooks = [v.get("title", "")[:30] for v in vids if v.get("title")]
            results.append(TrendKeyword(
                keyword=keyword,
                estimated_volume=total_views,
                avg_views=avg_views,
                avg_engagement=0,
                top_video_views=top_views,
                video_count=len(vids),
                sample_hooks=hooks[:3],
            ))
        return results

    # APIが使える場合: 上位5キーワードだけ検索（全30+は遅すぎる）
    priority_seeds = TREND_SEED_KEYWORDS[:8]
    for seed in priority_seeds:
        try:
            videos = search_tiktok_videos(
                seed, min_views=0, period_months=period_months * 2, max_results=10,
            )
            if not videos:
                continue

            total_views = sum(v.views for v in videos)
            avg_views = total_views // len(videos) if videos else 0
            avg_eng = sum(_calc_engagement_rate(v) for v in videos) / len(videos)
            top_views = max(v.views for v in videos)

            hooks = []
            for v in sorted(videos, key=lambda x: x.views, reverse=True)[:3]:
                text = v.transcript or v.description or v.title
                if text:
                    hooks.append(text[:30])

            results.append(TrendKeyword(
                keyword=seed,
                estimated_volume=total_views,
                avg_views=avg_views,
                avg_engagement=avg_eng,
                top_video_views=top_views,
                video_count=len(videos),
                sample_hooks=hooks,
            ))
            console.print(f"  [green]{seed}: {len(videos)}本[/green]")
        except Exception as e:
            console.print(f"  [dim]{seed}: {e}[/dim]")

    results.sort(key=lambda k: k.estimated_volume * (1 + k.avg_engagement) + 1, reverse=True)
    return results[:max_keywords]


def _calc_engagement_rate(video: TikTokVideo) -> float:
    """エンゲージメント率を計算する."""
    if video.views <= 0:
        return 0.0
    return (video.likes + video.comments * 3 + video.shares * 2) / video.views


# ===== エンゲージメント分析 =====

def score_videos_by_engagement(videos: list[TikTokVideo]) -> list[TikTokVideo]:
    """動画にエンゲージメントスコアを付与する."""
    for v in videos:
        if v.views > 0:
            v.like_rate = v.likes / v.views
            v.comment_rate = v.comments / v.views
            v.engagement_rate = (v.likes + v.comments + v.shares) / v.views
            # コメント率を重視したスコア（コメント多い=本当に刺さっている）
            v.engagement_score = (
                v.views * 0.3
                + v.likes * 1.0
                + v.comments * 5.0   # コメント重視
                + v.shares * 3.0
            )
        else:
            v.engagement_score = 0
    return videos


# ===== アカウント属人性チェック =====

def analyze_account_personality(account: TikTokAccount,
                                recent_videos: list[TikTokVideo] = None) -> TikTokAccount:
    """アカウントが属人（人に人気）かコンテンツ型かを判定する."""
    reasons = []

    # 1. 活動期間チェック
    if account.first_post_date:
        parsed = _parse_date(account.first_post_date)
        if parsed:
            months = (datetime.now() - parsed).days // 30
            account.activity_months = months

    # 2. フォロワーと動画数の比率
    if account.video_count > 0 and account.follower_count > 0:
        followers_per_video = account.follower_count / account.video_count
        account.avg_views_per_video = account.like_count // account.video_count if account.video_count else 0

        # フォロワーが動画数に比べて異常に多い → 属人の可能性
        if followers_per_video > 50000:
            reasons.append(f"フォロワー/動画比が高い({followers_per_video:,.0f})")

    # 3. bio分析 - 個人名・肩書きがある場合は属人
    if account.bio:
        personality_markers = [
            "美容師", "皮膚科", "医師", "ドクター", "先生", "モデル",
            "インフルエンサー", "YouTuber", "歳", "才",
            "私の", "僕の", "俺の",
        ]
        for marker in personality_markers:
            if marker in account.bio:
                reasons.append(f"bioに「{marker}」を含む")
                break

    # 4. ユーザー名分析 - 個人名っぽいかどうか
    if account.username:
        name_lower = account.username.lower()
        # 個人名っぽい（ひらがな・カタカナ中心、短い）
        if not any(kw in name_lower for kw in [
            "hack", "lab", "tips", "info", "cosme", "beauty", "skin",
            "health", "life", "ai", "bot", "official", "review",
        ]):
            if len(account.username) < 12:
                reasons.append("ユーザー名が個人名風")

    # 5. 最近の動画のばらつきチェック
    if recent_videos and len(recent_videos) >= 3:
        views_list = [v.views for v in recent_videos]
        avg = sum(views_list) / len(views_list)
        # 標準偏差が平均に比べて小さい→安定したファン層
        if avg > 0:
            variance = sum((x - avg) ** 2 for x in views_list) / len(views_list)
            std = variance ** 0.5
            cv = std / avg  # 変動係数
            if cv < 0.5:
                reasons.append(f"再生数が安定（変動係数{cv:.2f}）→固定ファン")

    # 判定
    account.is_personality_driven = len(reasons) >= 2
    account.personality_reason = "、".join(reasons) if reasons else "コンテンツ型の可能性が高い"

    # トレンド商品検出
    if recent_videos:
        account.trending_products = _detect_trending_products(recent_videos)

    return account


def _detect_trending_products(videos: list[TikTokVideo]) -> list[str]:
    """動画群からトレンド商品を検出する."""
    product_counter = Counter()
    product_patterns = [
        # ブランド名
        "アヌア", "クオリティファースト", "メディキューブ", "VT", "COSRX",
        "魔女工場", "ONE THING", "ナンバーズイン", "イニスフリー", "ラロッシュポゼ",
        "オルビス", "キュレル", "ミノン", "白潤", "肌ラボ",
        "セタフィル", "ドクターシーラボ", "アベンヌ", "ビオデルマ",
        "ナーズ", "スキンライフ",
        # 成分・施術名
        "レチノール", "ナイアシンアミド", "CICA", "シカ", "ビタミンC美容液",
        "ダーマペン", "ハーブピーリング", "美顔器",
    ]

    for v in videos:
        text = (v.transcript or "") + " " + (v.description or "")
        for product in product_patterns:
            if product.lower() in text.lower():
                product_counter[product] += 1

    return [p for p, _ in product_counter.most_common(10)]


def search_tiktok_videos(keyword: str, min_views: int = 500_000,
                         period_months: int = 3, max_results: int = 30) -> list[TikTokVideo]:
    """TikTokでキーワード検索し、条件に合う動画を返す（完全無料）."""
    videos = []
    seen_ids = set()

    # 方法1: Web検索でTikTok動画URLを収集（無料・無制限）
    web_videos = _search_web_fallback(keyword, max_results * 2)
    for v in web_videos:
        if v.video_id not in seen_ids:
            videos.append(v)
            seen_ids.add(v.video_id)

    # 方法2: ScrapeCreators API（APIキーがある場合のみ）
    sc_videos = _search_scrapecreators(keyword, max_results)
    for v in sc_videos:
        if v.video_id not in seen_ids:
            videos.append(v)
            seen_ids.add(v.video_id)

    # 方法3: 見つかったURLのメタデータをyt-dlpで取得（無料・無制限）
    if videos:
        console.print(f"  [cyan]{len(videos)}件のURLのメタデータを取得中...[/cyan]")
        _enrich_videos_with_ytdlp(videos)

    # フィルタリング
    cutoff = datetime.now() - timedelta(days=period_months * 30)
    filtered = []
    for v in videos:
        if min_views > 0 and v.views < min_views:
            continue
        if v.upload_timestamp:
            try:
                vdate = datetime.fromtimestamp(v.upload_timestamp)
                if vdate < cutoff:
                    continue
            except (ValueError, OSError):
                pass
        elif v.upload_date:
            parsed = _parse_date(v.upload_date)
            if parsed and parsed < cutoff:
                continue
        filtered.append(v)

    filtered.sort(key=lambda v: v.views, reverse=True)
    return filtered[:max_results]


def _enrich_videos_with_ytdlp(videos: list[TikTokVideo], max_enrich: int = 15):
    """yt-dlpで動画のメタデータ（再生数等）を無料で取得する."""
    for i, v in enumerate(videos[:max_enrich]):
        if v.views > 0:  # 既にメタデータがある場合はスキップ
            continue
        if not v.url:
            continue
        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--dump-json", "--no-download", "--no-warnings", "--quiet",
                v.url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                v.views = int(data.get("view_count", 0) or 0)
                v.likes = int(data.get("like_count", 0) or 0)
                v.comments = int(data.get("comment_count", 0) or 0)
                v.shares = int(data.get("repost_count", data.get("share_count", 0)) or 0)
                v.duration = int(data.get("duration", 0) or 0)
                v.title = (data.get("description", "") or data.get("title", ""))[:100]
                v.description = data.get("description", "")
                v.upload_date = data.get("upload_date", "")
                v.thumbnail = data.get("thumbnail", "")

                uploader = data.get("uploader", data.get("channel", ""))
                if uploader and not v.account_name:
                    v.account_name = uploader
                    v.account_url = f"https://www.tiktok.com/@{uploader}"

                console.print(f"    [green]✓ {v.video_id[:8]}... {v.views:,}再生[/green]")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            console.print(f"    [dim]✗ {v.video_id[:8]}...: {e}[/dim]")


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
    """TikTok検索ページ + Web検索で動画を探す（完全無料）."""
    videos = []
    seen_ids = set()

    # 方法1: TikTok検索ページに直接アクセス
    try:
        _search_tiktok_direct(keyword, videos, seen_ids, max_results)
        if videos:
            console.print(f"  [green]TikTok直接検索: {len(videos)}件取得[/green]")
    except Exception as e:
        console.print(f"  [dim]TikTok直接検索: {e}[/dim]")

    # 方法2: DuckDuckGo
    if len(videos) < 5:
        try:
            for query in [f"site:tiktok.com {keyword}", f"tiktok {keyword} バズ 再生"]:
                resp = http_requests.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": _ua()},
                    timeout=15,
                )
                if resp.status_code == 200:
                    _extract_tiktok_urls(resp.text, videos, seen_ids)
            if videos:
                console.print(f"  [green]DuckDuckGo: {len(videos)}件取得[/green]")
        except Exception as e:
            console.print(f"  [dim]DuckDuckGo: {e}[/dim]")

    # 方法3: Google
    if len(videos) < 5:
        try:
            for query in [f"site:tiktok.com {keyword}", f"tiktok.com {keyword} 万再生"]:
                resp = http_requests.get(
                    "https://www.google.com/search",
                    params={"q": query, "num": 20},
                    headers={"User-Agent": _ua()},
                    timeout=15,
                )
                if resp.status_code == 200:
                    _extract_tiktok_urls(resp.text, videos, seen_ids)
            if videos:
                console.print(f"  [green]Google: {len(videos)}件取得[/green]")
        except Exception as e:
            console.print(f"  [dim]Google: {e}[/dim]")

    return videos[:max_results]


def _ua():
    """ブラウザっぽいUser-Agent."""
    return ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def _search_tiktok_direct(keyword: str, videos: list, seen_ids: set, max_results: int = 20):
    """TikTokの検索ページから動画データを取得する."""
    import urllib.parse
    encoded = urllib.parse.quote(keyword)
    url = f"https://www.tiktok.com/search/video?q={encoded}"

    headers = {
        "User-Agent": _ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.tiktok.com/",
    }

    resp = http_requests.get(url, headers=headers, timeout=20)
    if resp.status_code != 200:
        return

    # TikTokページに埋め込まれたJSONデータを抽出
    # __UNIVERSAL_DATA_FOR_REHYDRATION__ スクリプトタグを探す
    json_match = re.search(
        r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        resp.text, re.DOTALL
    )

    if json_match:
        try:
            data = json.loads(json_match.group(1))
            _parse_tiktok_search_json(data, videos, seen_ids, max_results)
            return
        except json.JSONDecodeError:
            pass

    # SIGI_STATE も試す
    sigi_match = re.search(
        r'<script\s+id="SIGI_STATE"[^>]*>(.*?)</script>',
        resp.text, re.DOTALL
    )
    if sigi_match:
        try:
            data = json.loads(sigi_match.group(1))
            _parse_tiktok_sigi_state(data, videos, seen_ids, max_results)
            return
        except json.JSONDecodeError:
            pass

    # 最後の手段: HTMLからURLを直接抽出
    _extract_tiktok_urls(resp.text, videos, seen_ids)


def _parse_tiktok_search_json(data: dict, videos: list, seen_ids: set, max_results: int):
    """TikTokの__UNIVERSAL_DATA_FOR_REHYDRATION__からデータを抽出."""
    # データ構造を探索
    def _find_items(obj, depth=0):
        if depth > 8 or len(videos) >= max_results:
            return
        if isinstance(obj, dict):
            # 動画データっぽい構造を検出
            vid_id = str(obj.get("id", obj.get("video_id", "")))
            stats = obj.get("stats", obj.get("statistics", {}))
            author = obj.get("author", {})

            if vid_id and isinstance(stats, dict) and stats.get("playCount", stats.get("play_count")):
                if vid_id not in seen_ids:
                    seen_ids.add(vid_id)
                    username = ""
                    if isinstance(author, dict):
                        username = author.get("uniqueId", author.get("username", ""))

                    v = TikTokVideo(
                        video_id=vid_id,
                        url=f"https://www.tiktok.com/@{username}/video/{vid_id}" if username else "",
                        title=(obj.get("desc", "") or "")[:100],
                        description=obj.get("desc", ""),
                        views=int(stats.get("playCount", stats.get("play_count", 0)) or 0),
                        likes=int(stats.get("diggCount", stats.get("like_count", 0)) or 0),
                        comments=int(stats.get("commentCount", stats.get("comment_count", 0)) or 0),
                        shares=int(stats.get("shareCount", stats.get("share_count", 0)) or 0),
                        duration=int(obj.get("video", {}).get("duration", 0) or 0),
                        upload_timestamp=int(obj.get("createTime", 0) or 0),
                        account_name=username,
                        account_url=f"https://www.tiktok.com/@{username}" if username else "",
                        account_id=username,
                    )
                    if v.upload_timestamp:
                        try:
                            v.upload_date = datetime.fromtimestamp(v.upload_timestamp).strftime("%Y-%m-%d")
                        except (ValueError, OSError):
                            pass
                    videos.append(v)
                return

            for val in obj.values():
                _find_items(val, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _find_items(item, depth + 1)

    _find_items(data)


def _parse_tiktok_sigi_state(data: dict, videos: list, seen_ids: set, max_results: int):
    """TikTokのSIGI_STATEからデータを抽出."""
    item_module = data.get("ItemModule", {})
    if isinstance(item_module, dict):
        for vid_id, item in item_module.items():
            if len(videos) >= max_results:
                break
            if vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            stats = item.get("stats", {})
            username = item.get("author", "")

            v = TikTokVideo(
                video_id=vid_id,
                url=f"https://www.tiktok.com/@{username}/video/{vid_id}" if username else "",
                title=(item.get("desc", "") or "")[:100],
                description=item.get("desc", ""),
                views=int(stats.get("playCount", 0) or 0),
                likes=int(stats.get("diggCount", 0) or 0),
                comments=int(stats.get("commentCount", 0) or 0),
                shares=int(stats.get("shareCount", 0) or 0),
                duration=int(item.get("video", {}).get("duration", 0) or 0),
                upload_timestamp=int(item.get("createTime", 0) or 0),
                account_name=username,
                account_url=f"https://www.tiktok.com/@{username}" if username else "",
            )
            if v.upload_timestamp:
                try:
                    v.upload_date = datetime.fromtimestamp(v.upload_timestamp).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    pass
            videos.append(v)


def _extract_tiktok_urls(html_text: str, videos: list, seen_ids: set):
    """HTMLテキストからTikTok動画URLを抽出してvideosリストに追加する."""
    matches = re.findall(r'tiktok\.com/@([\w.]+)/video/(\d+)', html_text)
    for username, vid_id in matches:
        if vid_id in seen_ids:
            continue
        seen_ids.add(vid_id)
        videos.append(TikTokVideo(
            video_id=vid_id,
            url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
            account_name=username,
            account_url=f"https://www.tiktok.com/@{username}",
            account_id=username,
        ))


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
        "activity_months": account.activity_months,
        "is_personality_driven": account.is_personality_driven,
        "personality_reason": account.personality_reason,
        "trending_products": account.trending_products,
    }


def format_trend_keyword_for_display(kw: TrendKeyword) -> dict:
    """TrendKeywordをフロント表示用に整形する."""
    from .reference_data import KEYWORD_REFERENCES
    ref = KEYWORD_REFERENCES.get(kw.keyword, {})

    return {
        "keyword": kw.keyword,
        "estimated_volume": kw.estimated_volume,
        "avg_views": kw.avg_views,
        "avg_engagement": round(kw.avg_engagement * 100, 1),
        "top_video_views": kw.top_video_views,
        "video_count": kw.video_count,
        "sample_hooks": kw.sample_hooks,
        "ref_videos": ref.get("videos", [])[:10],
        "ref_accounts": ref.get("accounts", [])[:3],
        "desc": ref.get("desc", ""),
    }
