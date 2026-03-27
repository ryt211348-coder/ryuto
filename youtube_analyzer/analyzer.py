"""YouTube チャンネルの動画をショート/長尺に分類して分析する."""

import json
import subprocess
from collections import defaultdict
from datetime import datetime


def fetch_channel_videos(channel_url: str, progress_callback=None) -> dict:
    """チャンネルURLから全動画のメタデータを取得する.

    Returns:
        dict with keys: channel_name, subscriber_count, videos (list)
    """
    # チャンネル情報と動画一覧を取得
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--extractor-args", "youtube:lang=ja",
        channel_url,
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp エラー: {result.stderr[:500]}")

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            videos.append(data)
        except json.JSONDecodeError:
            continue

    if not videos:
        raise RuntimeError("動画が見つかりませんでした。チャンネルURLを確認してください。")

    return videos


def fetch_video_details(video_ids: list, progress_callback=None) -> list:
    """個別の動画詳細（再生回数、duration等）を取得する."""
    details = []
    total = len(video_ids)

    for i, vid in enumerate(video_ids):
        if progress_callback:
            progress_callback(i + 1, total)

        url = f"https://www.youtube.com/watch?v={vid}"
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--skip-download",
            url,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip().split("\n")[0])
                details.append(data)
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            continue

    return details


def classify_video(video: dict) -> str:
    """動画をショートまたは長尺に分類する.

    判定基準（優先順）:
    1. URLに /shorts/ パスが含まれる（最も確実）
    2. webpage_url / original_url に /shorts/ が含まれる
    3. タイトルに #shorts タグが含まれる
    4. 動画の縦横比が縦型（height > width）かつ60秒以下
    5. duration が60秒以下かつ上記のいずれかに該当
    """
    # flat-playlistで既にショートと判定されている場合
    if video.get("_short_hint"):
        return "short"

    # URL系フィールドをすべてチェック
    url_fields = ["url", "webpage_url", "original_url", "display_id"]
    for field in url_fields:
        val = (video.get(field) or "").lower()
        if "/shorts/" in val:
            return "short"

    # タイトルに #shorts が含まれる
    title = (video.get("title") or "").lower()
    description = (video.get("description") or "").lower()
    if "#shorts" in title or "#shorts" in description:
        return "short"

    # 縦型動画（height > width）かつ60秒以下 → ショートの可能性が高い
    duration = video.get("duration") or 0
    width = video.get("width") or 0
    height = video.get("height") or 0
    if duration and duration <= 60 and height > width and height > 0:
        return "short"

    return "long"


def analyze_channel(channel_url: str, progress_callback=None) -> dict:
    """チャンネルを分析してショート/長尺の月間データを返す."""

    if progress_callback:
        progress_callback("fetching", "動画一覧を取得中...")

    # Step 1: flat-playlistで動画ID一覧を取得
    playlist_videos = fetch_channel_videos(channel_url)

    # flat-playlistのURL情報からショート判定用のヒントを保持
    video_entries = []
    for v in playlist_videos:
        vid = v.get("id") or v.get("url")
        if vid:
            # flat-playlistのURLに /shorts/ が含まれるかチェック
            entry_url = v.get("url") or ""
            is_short_hint = "/shorts/" in entry_url
            video_entries.append({"id": vid, "is_short_hint": is_short_hint})

    if not video_entries:
        raise RuntimeError("動画が見つかりませんでした。")

    video_ids = [e["id"] for e in video_entries]
    short_hints = {e["id"]: e["is_short_hint"] for e in video_entries}

    if progress_callback:
        progress_callback("details", f"{len(video_ids)}本の動画の詳細を取得中...")

    # Step 2: 各動画の詳細情報を取得
    def detail_progress(current, total):
        if progress_callback:
            progress_callback("details", f"動画詳細を取得中 ({current}/{total})...")

    details = fetch_video_details(video_ids, progress_callback=detail_progress)

    # flat-playlistで得たショートヒントを詳細データにマージ
    for d in details:
        vid = d.get("id", "")
        if short_hints.get(vid):
            d["_short_hint"] = True

    if not details:
        raise RuntimeError("動画の詳細情報を取得できませんでした。")

    # チャンネル情報
    first_video = details[0] if details else {}
    channel_name = first_video.get("channel") or first_video.get("uploader") or "不明"
    subscriber_count = first_video.get("channel_follower_count") or 0

    # Step 3: 分類と集計
    if progress_callback:
        progress_callback("analyzing", "データを分析中...")

    monthly_data = defaultdict(lambda: {
        "short_views": 0, "short_count": 0,
        "long_views": 0, "long_count": 0,
        "total_views": 0, "total_count": 0,
    })

    all_videos = []
    first_upload_date = None

    for v in details:
        upload_date_str = v.get("upload_date") or ""
        if not upload_date_str or len(upload_date_str) < 8:
            continue

        try:
            upload_date = datetime.strptime(upload_date_str[:8], "%Y%m%d")
        except ValueError:
            continue

        month_key = upload_date.strftime("%Y-%m")
        view_count = v.get("view_count") or 0
        duration = v.get("duration") or 0
        video_type = classify_video(v)

        video_info = {
            "id": v.get("id", ""),
            "title": v.get("title", ""),
            "url": v.get("webpage_url") or f"https://www.youtube.com/watch?v={v.get('id', '')}",
            "views": view_count,
            "duration": duration,
            "upload_date": upload_date.strftime("%Y-%m-%d"),
            "type": video_type,
            "thumbnail": v.get("thumbnail", ""),
            "like_count": v.get("like_count") or 0,
            "comment_count": v.get("comment_count") or 0,
        }
        all_videos.append(video_info)

        # 月間集計
        md = monthly_data[month_key]
        md["total_views"] += view_count
        md["total_count"] += 1

        if video_type == "short":
            md["short_views"] += view_count
            md["short_count"] += 1
        else:
            md["long_views"] += view_count
            md["long_count"] += 1

        # 最初の投稿日を追跡
        if first_upload_date is None or upload_date < first_upload_date:
            first_upload_date = upload_date

    # 月間データをソート
    sorted_months = sorted(monthly_data.keys(), reverse=True)
    monthly_list = []
    for m in sorted_months:
        d = monthly_data[m]
        monthly_list.append({
            "month": m,
            **d,
        })

    # 全体の集計
    total_short_views = sum(d["short_views"] for d in monthly_data.values())
    total_long_views = sum(d["long_views"] for d in monthly_data.values())
    total_short_count = sum(d["short_count"] for d in monthly_data.values())
    total_long_count = sum(d["long_count"] for d in monthly_data.values())

    return {
        "channel_name": channel_name,
        "subscriber_count": subscriber_count,
        "first_upload_date": first_upload_date.strftime("%Y-%m-%d") if first_upload_date else "不明",
        "total_videos": len(all_videos),
        "total_short_count": total_short_count,
        "total_long_count": total_long_count,
        "total_short_views": total_short_views,
        "total_long_views": total_long_views,
        "total_views": total_short_views + total_long_views,
        "monthly": monthly_list,
        "videos": sorted(all_videos, key=lambda x: x["upload_date"], reverse=True),
    }
