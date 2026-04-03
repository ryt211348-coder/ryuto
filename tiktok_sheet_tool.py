"""TikTokアカウントのデータを取得し、スプレッドシート用の指標を算出するツール.

対応シート列:
  C: 登録者
  D: 総再生数
  E: 月間再生回数
  F: 月間投稿本数（+ 平均月間投稿本数）
  G: 平均再生数/本
  H: 登録者推移（※外部データ必要）
  I: 初投稿
"""

import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import Optional

from tiktok_analyzer.extractor import (
    extract_account_videos,
    VideoInfo,
)


def _parse_upload_date(date_str: str) -> Optional[datetime]:
    """アップロード日をdatetimeに変換する."""
    if not date_str:
        return None

    # Unix timestamp (TikTokApi形式)
    try:
        ts = int(date_str)
        if ts > 1_000_000_000:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        pass

    # YYYYMMDD 形式 (yt-dlp形式)
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass

    # ISO形式
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass

    return None


def _format_number(n: int) -> str:
    """数値を万単位で読みやすくフォーマットする."""
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}億"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return f"{n:,}"


def _get_follower_count_via_ytdlp(account_url: str) -> Optional[int]:
    """yt-dlpでフォロワー数を取得する."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json", "--playlist-items", "1",
        "--no-download", "--no-warnings",
        account_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                data = json.loads(line)
                fc = data.get("channel_follower_count")
                if fc:
                    return int(fc)
    except Exception:
        pass
    return None


@dataclass
class SheetData:
    """スプレッドシートに埋める1行分のデータ."""
    platform: str = "TikTok"
    url: str = ""
    followers: str = ""
    followers_raw: int = 0
    total_views: int = 0                # D: 総再生数
    monthly_views: int = 0              # E: 月間再生回数
    monthly_posts: int = 0              # F: 月間投稿本数
    avg_monthly_posts: float = 0.0      # F補足: 平均月間投稿本数
    avg_views_per_video: int = 0        # G: 平均再生数/本
    follower_trend: str = ""            # H: 登録者推移
    first_post_date: str = ""           # I: 初投稿
    total_videos: int = 0
    active_months: int = 0              # 投稿があった月の数
    total_months_span: int = 0          # 初投稿〜現在の月数
    posting_timeline: list = None       # 月別投稿数 [{month, count, views}]


def _build_posting_timeline(videos: list[VideoInfo]) -> list[dict]:
    """月別の投稿数・再生数を集計してタイムラインデータを作成する."""
    monthly = defaultdict(lambda: {"count": 0, "views": 0})

    for v in videos:
        dt = _parse_upload_date(v.upload_date)
        if dt:
            key = dt.strftime("%Y-%m")
            monthly[key]["count"] += 1
            monthly[key]["views"] += v.view_count

    if not monthly:
        return []

    # 最古月〜現在月まで全月を埋める（投稿0の月も含む）
    sorted_keys = sorted(monthly.keys())
    start = datetime.strptime(sorted_keys[0], "%Y-%m").replace(tzinfo=timezone.utc)
    end = datetime.now(tz=timezone.utc).replace(day=1)

    timeline = []
    current = start
    while current <= end:
        key = current.strftime("%Y-%m")
        entry = monthly.get(key, {"count": 0, "views": 0})
        timeline.append({
            "month": key,
            "count": entry["count"],
            "views": entry["views"],
        })
        # 次の月へ
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return timeline


def compute_sheet_data(account_url: str, videos: list[VideoInfo]) -> SheetData:
    """動画リストからスプレッドシート用のデータを算出する."""
    now = datetime.now(tz=timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    data = SheetData()
    data.url = account_url
    data.posting_timeline = []

    if not videos:
        return data

    data.total_videos = len(videos)

    # --- 総再生数 (D) ---
    data.total_views = sum(v.view_count for v in videos)

    # --- 平均再生数/本 (G) ---
    data.avg_views_per_video = data.total_views // len(videos)

    # --- 月間データ (E, F) ---
    monthly_videos = []
    for v in videos:
        upload_dt = _parse_upload_date(v.upload_date)
        if upload_dt and upload_dt >= thirty_days_ago:
            monthly_videos.append(v)

    data.monthly_views = sum(v.view_count for v in monthly_videos)
    data.monthly_posts = len(monthly_videos)

    # --- 投稿タイムライン ---
    data.posting_timeline = _build_posting_timeline(videos)

    # --- 平均月間投稿本数 ---
    if data.posting_timeline:
        active_months = [m for m in data.posting_timeline if m["count"] > 0]
        data.active_months = len(active_months)
        data.total_months_span = len(data.posting_timeline)
        if data.active_months > 0:
            data.avg_monthly_posts = round(
                sum(m["count"] for m in active_months) / data.active_months, 1
            )

    # --- 初投稿 (I) ---
    earliest = None
    for v in videos:
        dt = _parse_upload_date(v.upload_date)
        if dt:
            if earliest is None or dt < earliest:
                earliest = dt
    if earliest:
        data.first_post_date = earliest.strftime("%Y/%m/%d")

    # --- フォロワー数 (C) ---
    fc = _get_follower_count_via_ytdlp(account_url)
    if fc:
        data.followers = f"{_format_number(fc)}人"
        data.followers_raw = fc

    return data
