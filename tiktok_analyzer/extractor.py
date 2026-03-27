"""TikTokアカウントから動画メタデータを抽出し、再生数でフィルタリングする."""

import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

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


def extract_account_videos(account_url: str) -> list[VideoInfo]:
    """yt-dlpでTikTokアカウントの全動画メタデータを取得する."""
    console.print(f"\n[bold cyan]アカウントから動画情報を取得中...[/bold cyan]")
    console.print(f"  URL: {account_url}\n")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--no-warnings",
        account_url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        console.print("[red]タイムアウト: 動画情報の取得に時間がかかりすぎました[/red]")
        return []
    except FileNotFoundError:
        console.print("[red]エラー: yt-dlpがインストールされていません。pip install yt-dlp を実行してください[/red]")
        return []

    if result.returncode != 0 and not result.stdout:
        console.print(f"[red]エラー: 動画情報の取得に失敗しました[/red]")
        if result.stderr:
            console.print(f"[dim]{result.stderr[:500]}[/dim]")
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            video = VideoInfo(
                video_id=str(data.get("id", "")),
                title=data.get("title", ""),
                url=data.get("webpage_url") or data.get("url", ""),
                view_count=int(data.get("view_count", 0) or 0),
                like_count=int(data.get("like_count", 0) or 0),
                comment_count=int(data.get("comment_count", 0) or 0),
                share_count=int(data.get("share_count", 0) or 0),
                duration=int(data.get("duration", 0) or 0),
                upload_date=data.get("upload_date", ""),
                description=data.get("description", ""),
            )
            videos.append(video)
        except (json.JSONDecodeError, ValueError):
            continue

    console.print(f"  [green]合計 {len(videos)} 本の動画を検出[/green]")
    return videos


def filter_viral_videos(videos: list[VideoInfo], min_views: int = 1_000_000) -> list[VideoInfo]:
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


def download_video_audio(video: VideoInfo, output_dir: Path) -> Path | None:
    """動画の音声をダウンロードする."""
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


def save_videos_metadata(videos: list[VideoInfo], output_path: Path) -> None:
    """動画メタデータをJSONファイルに保存する."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(v) for v in videos]
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"  [dim]メタデータ保存: {output_path}[/dim]")
