"""TikTokアカウントから動画メタデータを抽出し、再生数でフィルタリングする."""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


@dataclass
class VideoInfo:
    video_id: str
    title: str
    url: str
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    duration: int
    upload_date: str
    description: str
    thumbnail: str = ""


async def _fetch_with_tiktokapi(username):
    """TikTokApi (Playwright) を使って動画データを取得する."""
    from TikTokApi import TikTokApi

    videos_data = []
    async with TikTokApi() as api:
        await api.create_sessions(num_sessions=1, sleep_after=5)
        user = api.user(username)
        async for video in user.videos(count=300):
            vd = video.as_dict
            stats = vd.get("stats", {})
            desc = vd.get("desc", "")
            vid_id = vd.get("id", "")
            duration = vd.get("video", {}).get("duration", 0)
            create_time = vd.get("createTime", "")

            cover = vd.get("video", {}).get("cover", "")
            if not cover:
                cover = vd.get("video", {}).get("dynamicCover", "")
            if not cover:
                cover = vd.get("video", {}).get("originCover", "")

            videos_data.append({
                "id": vid_id,
                "desc": desc,
                "views": stats.get("playCount", 0),
                "likes": stats.get("diggCount", 0),
                "comments": stats.get("commentCount", 0),
                "shares": stats.get("shareCount", 0),
                "duration": duration,
                "createTime": create_time,
                "thumbnail": cover,
            })
    return videos_data


def _fetch_with_ytdlp(account_url):
    """yt-dlp を使って動画データを取得する（フォールバック）."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json", "--flat-playlist",
        "--no-download", "--no-warnings",
        account_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if result.returncode != 0 and not result.stdout:
        return []

    videos_data = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            videos_data.append({
                "id": str(data.get("id", "")),
                "desc": data.get("description", "") or data.get("title", ""),
                "views": int(data.get("view_count", 0) or 0),
                "likes": int(data.get("like_count", 0) or 0),
                "comments": int(data.get("comment_count", 0) or 0),
                "shares": int(data.get("share_count", 0) or 0),
                "duration": int(data.get("duration", 0) or 0),
                "createTime": data.get("upload_date", ""),
                "thumbnail": data.get("thumbnail", "") or data.get("thumbnails", [{}])[0].get("url", "") if data.get("thumbnails") else "",
            })
        except (json.JSONDecodeError, ValueError):
            continue
    return videos_data


def _parse_username(account_url):
    """URLからユーザー名を抽出する."""
    url = account_url.strip().rstrip("/")
    if "@" in url:
        # https://www.tiktok.com/@username or just @username
        parts = url.split("@")
        username = parts[-1].split("/")[0].split("?")[0]
        return username
    return url


def extract_account_videos(account_url):
    """TikTokアカウントの全動画メタデータを取得する."""
    console.print(f"\n[bold cyan]アカウントから動画情報を取得中...[/bold cyan]")
    console.print(f"  URL: {account_url}\n")

    username = _parse_username(account_url)
    videos_data = []

    # 方法1: TikTokApi (Playwright) を試す
    try:
        console.print("  [dim]TikTokApi (Playwright) で取得中...[/dim]")
        videos_data = asyncio.run(_fetch_with_tiktokapi(username))
        if videos_data:
            console.print(f"  [green]TikTokApi で {len(videos_data)} 本の動画を検出[/green]")
    except Exception as e:
        console.print(f"  [yellow]TikTokApi 失敗: {e}[/yellow]")
        console.print("  [dim]yt-dlp にフォールバック中...[/dim]")

    # 方法2: yt-dlp でフォールバック
    if not videos_data:
        try:
            videos_data = _fetch_with_ytdlp(account_url)
            if videos_data:
                console.print(f"  [green]yt-dlp で {len(videos_data)} 本の動画を検出[/green]")
            else:
                console.print("  [red]yt-dlp でも取得できませんでした[/red]")
        except Exception as e:
            console.print(f"  [red]yt-dlp エラー: {e}[/red]")

    # VideoInfoに変換
    videos = []
    for d in videos_data:
        vid_id = str(d.get("id", ""))
        video = VideoInfo(
            video_id=vid_id,
            title=d.get("desc", "")[:100],
            url=f"https://www.tiktok.com/@{username}/video/{vid_id}",
            view_count=int(d.get("views", 0) or 0),
            like_count=int(d.get("likes", 0) or 0),
            comment_count=int(d.get("comments", 0) or 0),
            share_count=int(d.get("shares", 0) or 0),
            duration=int(d.get("duration", 0) or 0),
            upload_date=str(d.get("createTime", "")),
            description=d.get("desc", ""),
            thumbnail=d.get("thumbnail", ""),
        )
        videos.append(video)

    console.print(f"  [green]合計 {len(videos)} 本の動画を検出[/green]")
    return videos


def filter_viral_videos(videos, min_views=1_000_000):
    """指定再生数以上の動画をフィルタリングする."""
    viral = [v for v in videos if v.view_count >= min_views]
    viral.sort(key=lambda v: v.view_count, reverse=True)

    console.print(f"  [yellow]{min_views:,}再生以上: {len(viral)} 本[/yellow]\n")

    if viral:
        console.print("[bold]バイラル動画一覧:[/bold]")
        for i, v in enumerate(viral, 1):
            console.print(
                f"  {i:3d}. [cyan]{v.view_count:>12,}再生[/cyan] | "
                f"{v.like_count:>10,}いいね | "
                f"{v.duration:>3d}秒 | {v.title[:50]}"
            )
        console.print()

    return viral


def download_video_audio(video, output_dir):
    """動画の音声をダウンロードする."""
    output_dir = Path(output_dir)
    output_path = output_dir / f"{video.video_id}.mp3"

    if output_path.exists():
        return output_path

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", str(output_dir / f"{video.video_id}.%(ext)s"),
        "--no-warnings",
        "--quiet",
        video.url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and output_path.exists():
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def save_videos_metadata(videos, output_path):
    """動画メタデータをJSONファイルに保存する."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(v) for v in videos]
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"  [dim]メタデータ保存: {output_path}[/dim]")
