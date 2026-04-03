"""TikTokアカウントのデータを取得し、スプレッドシート用の指標を算出するツール.

対応シート列:
  D: 総再生数
  E: 月間再生回数
  F: 月間投稿本数
  G: 長尺（投稿本数・平均再生数）
  H: ショート（投稿本数・平均再生数）
  I: 登録者推移（※外部データ必要）
  J: 初投稿
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict, field
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tiktok_analyzer.extractor import (
    extract_account_videos,
    _parse_username,
    _fetch_with_tiktokapi,
    _fetch_with_ytdlp,
    VideoInfo,
)

console = Console()

# TikTokでは60秒以下をショート、61秒以上を長尺とみなす
SHORT_VIDEO_MAX_SECONDS = 60


@dataclass
class SheetData:
    """スプレッドシートに埋める1行分のデータ."""
    platform: str = "TikTok"
    url: str = ""
    followers: str = ""
    total_views: int = 0
    total_views_detail: str = ""       # D: 長尺/ショート内訳
    monthly_views: int = 0             # E: 月間再生回数
    monthly_posts: int = 0             # F: 月間投稿本数
    long_form_count: int = 0           # G: 長尺の投稿本数
    long_form_avg_views: int = 0       # G: 長尺の平均再生数
    short_form_count: int = 0          # H: ショートの投稿本数
    short_form_avg_views: int = 0      # H: ショートの平均再生数
    follower_trend: str = ""           # I: 登録者推移
    first_post_date: str = ""          # J: 初投稿


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
                # yt-dlp sometimes includes channel info
                fc = data.get("channel_follower_count")
                if fc:
                    return int(fc)
    except Exception:
        pass
    return None


def compute_sheet_data(account_url: str, videos: list[VideoInfo]) -> SheetData:
    """動画リストからスプレッドシート用のデータを算出する."""
    now = datetime.now(tz=timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    data = SheetData()
    data.url = account_url

    if not videos:
        return data

    # --- 総再生数 (D) ---
    total_views = sum(v.view_count for v in videos)
    data.total_views = total_views

    # --- 長尺 / ショート分類 ---
    long_videos = [v for v in videos if v.duration > SHORT_VIDEO_MAX_SECONDS]
    short_videos = [v for v in videos if v.duration <= SHORT_VIDEO_MAX_SECONDS]

    long_total_views = sum(v.view_count for v in long_videos)
    short_total_views = sum(v.view_count for v in short_videos)

    data.total_views_detail = (
        f"（長尺：{_format_number(long_total_views)}　ショート：{_format_number(short_total_views)}）"
    )

    # --- 月間データ (E, F) ---
    monthly_videos = []
    monthly_long = []
    monthly_short = []
    for v in videos:
        upload_dt = _parse_upload_date(v.upload_date)
        if upload_dt and upload_dt >= thirty_days_ago:
            monthly_videos.append(v)
            if v.duration > SHORT_VIDEO_MAX_SECONDS:
                monthly_long.append(v)
            else:
                monthly_short.append(v)

    data.monthly_views = sum(v.view_count for v in monthly_videos)
    data.monthly_posts = len(monthly_videos)

    # --- 長尺 (G): 月間の投稿本数・平均再生数 ---
    data.long_form_count = len(monthly_long)
    if monthly_long:
        data.long_form_avg_views = sum(v.view_count for v in monthly_long) // len(monthly_long)

    # --- ショート (H): 月間の投稿本数・平均再生数 ---
    data.short_form_count = len(monthly_short)
    if monthly_short:
        data.short_form_avg_views = sum(v.view_count for v in monthly_short) // len(monthly_short)

    # --- 初投稿 (J) ---
    earliest = None
    for v in videos:
        dt = _parse_upload_date(v.upload_date)
        if dt:
            if earliest is None or dt < earliest:
                earliest = dt
    if earliest:
        data.first_post_date = earliest.strftime("%Y/%m/%d")

    # --- フォロワー数 (C) ---
    console.print("  [dim]フォロワー数を取得中...[/dim]")
    fc = _get_follower_count_via_ytdlp(account_url)
    if fc:
        data.followers = f"{_format_number(fc)}人"

    return data


def print_sheet_data(data: SheetData):
    """スプレッドシート用データを見やすく表示する."""
    table = Table(title="スプレッドシート用データ", show_header=True, header_style="bold cyan")
    table.add_column("列", style="bold", width=6)
    table.add_column("項目", width=24)
    table.add_column("値", style="green")

    table.add_row("A", "媒体", data.platform)
    table.add_row("B", "URL", data.url)
    table.add_row("C", "登録者", data.followers or "取得不可")
    table.add_row("D", "総再生数", f"{data.total_views:,}\n{data.total_views_detail}")
    table.add_row("E", "月間再生回数", f"{_format_number(data.monthly_views)}回")
    table.add_row("F", "月間投稿本数", f"{data.monthly_posts}")
    table.add_row(
        "G", "長尺\n（投稿本数・平均再生数）",
        f"{data.long_form_count}本\n平均 {_format_number(data.long_form_avg_views)}回/本"
    )
    table.add_row(
        "H", "ショート\n（投稿本数・平均再生数）",
        f"{data.short_form_count}本\n平均 {_format_number(data.short_form_avg_views)}回/本"
    )
    table.add_row("I", "登録者推移", data.follower_trend or "（要手動入力）")
    table.add_row("J", "初投稿", data.first_post_date or "不明")

    console.print()
    console.print(table)


def export_to_csv(data: SheetData, output_path: str = "tiktok_sheet_data.csv"):
    """CSV形式でエクスポートする（Google Sheetsに貼り付け可能）."""
    import csv
    from pathlib import Path

    rows = [
        ["媒体", "URL", "登録者", "総再生数", "月間再生回数", "月間投稿本数",
         "長尺（投稿本数・平均再生数）", "ショート（投稿本数・平均再生数）",
         "登録者推移", "初投稿"],
        [
            data.platform,
            data.url,
            data.followers,
            f"{data.total_views:,}\n{data.total_views_detail}",
            f"{_format_number(data.monthly_views)}回",
            str(data.monthly_posts),
            f"{data.long_form_count}本\n平均 {_format_number(data.long_form_avg_views)}回/本",
            f"{data.short_form_count}本\n平均 {_format_number(data.short_form_avg_views)}回/本",
            data.follower_trend,
            data.first_post_date,
        ],
    ]

    path = Path(output_path)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    console.print(f"\n  [green]CSV保存: {path}[/green]")
    return path


def export_to_json(data: SheetData, output_path: str = "tiktok_sheet_data.json"):
    """JSON形式でエクスポートする."""
    from pathlib import Path

    path = Path(output_path)
    path.write_text(
        json.dumps(asdict(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"  [green]JSON保存: {path}[/green]")
    return path


# ─── CLI ───────────────────────────────────────────────────────────────────────


@click.group()
def cli():
    """TikTokシート埋めツール - スプレッドシートに必要なデータを自動取得."""
    pass


@cli.command()
@click.argument("account_url")
@click.option("--csv", "export_csv", is_flag=True, help="CSV形式でエクスポート")
@click.option("--json", "export_json", is_flag=True, help="JSON形式でエクスポート")
@click.option("--output", default=".", help="出力ディレクトリ")
def fetch(account_url, export_csv, export_json, output):
    """TikTokアカウントのシート用データを取得する.

    ACCOUNT_URL: TikTokアカウントURL (例: https://www.tiktok.com/@username)
    """
    console.print(Panel(
        "[bold cyan]TikTok シート埋めツール[/bold cyan]\n"
        f"対象: {account_url}",
        title="開始",
    ))

    # Step 1: 動画メタデータ取得
    console.print("\n[bold]Step 1: 動画メタデータ取得[/bold]")
    videos = extract_account_videos(account_url)

    if not videos:
        console.print("[red]動画が見つかりませんでした。URLを確認してください。[/red]")
        return

    console.print(f"  [green]{len(videos)} 本の動画を取得[/green]")

    # Step 2: シート用データ算出
    console.print("\n[bold]Step 2: シート用データ算出[/bold]")
    sheet_data = compute_sheet_data(account_url, videos)

    # 結果表示
    print_sheet_data(sheet_data)

    # エクスポート
    from pathlib import Path
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if export_csv:
        export_to_csv(sheet_data, str(out_dir / "tiktok_sheet_data.csv"))
    if export_json:
        export_to_json(sheet_data, str(out_dir / "tiktok_sheet_data.json"))

    # デフォルトでは両方出力
    if not export_csv and not export_json:
        export_to_csv(sheet_data, str(out_dir / "tiktok_sheet_data.csv"))
        export_to_json(sheet_data, str(out_dir / "tiktok_sheet_data.json"))

    console.print(Panel(
        "[bold green]完了！[/bold green]\n\n"
        "CSVファイルをGoogle Sheetsに貼り付けるか、\n"
        "上記の値を手動でシートに入力してください。\n\n"
        "[dim]※ 登録者推移(I列)はTikTokから直接取得できないため、\n"
        "  Social Bladeなどの外部ツールで確認してください。[/dim]",
        title="完了",
        style="green",
    ))


@cli.command()
@click.argument("account_url")
def quick(account_url):
    """クイックモード: データを取得してコンソールに表示するだけ.

    ACCOUNT_URL: TikTokアカウントURL
    """
    console.print(f"[bold cyan]クイック取得: {account_url}[/bold cyan]\n")

    videos = extract_account_videos(account_url)
    if not videos:
        console.print("[red]動画が見つかりませんでした。[/red]")
        return

    sheet_data = compute_sheet_data(account_url, videos)
    print_sheet_data(sheet_data)


@cli.command()
@click.argument("account_urls", nargs=-1)
@click.option("--output", default=".", help="出力ディレクトリ")
def batch(account_urls, output):
    """複数アカウントを一括処理する.

    ACCOUNT_URLS: TikTokアカウントURLのリスト
    """
    if not account_urls:
        console.print("[red]アカウントURLを指定してください。[/red]")
        return

    import csv
    from pathlib import Path

    all_data = []

    for i, url in enumerate(account_urls, 1):
        console.print(Panel(f"[bold]アカウント {i}/{len(account_urls)}: {url}[/bold]"))

        videos = extract_account_videos(url)
        if not videos:
            console.print(f"  [red]動画が見つかりません: {url}[/red]")
            continue

        sheet_data = compute_sheet_data(url, videos)
        print_sheet_data(sheet_data)
        all_data.append(sheet_data)

    if all_data:
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "tiktok_sheet_batch.csv"

        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "媒体", "URL", "登録者", "総再生数", "月間再生回数",
                "月間投稿本数", "長尺（投稿本数・平均再生数）",
                "ショート（投稿本数・平均再生数）", "登録者推移", "初投稿",
            ])
            for d in all_data:
                writer.writerow([
                    d.platform, d.url, d.followers,
                    f"{d.total_views:,}\n{d.total_views_detail}",
                    f"{_format_number(d.monthly_views)}回",
                    str(d.monthly_posts),
                    f"{d.long_form_count}本\n平均 {_format_number(d.long_form_avg_views)}回/本",
                    f"{d.short_form_count}本\n平均 {_format_number(d.short_form_avg_views)}回/本",
                    d.follower_trend,
                    d.first_post_date,
                ])

        console.print(f"\n[green]一括CSV保存: {out_path}[/green]")


if __name__ == "__main__":
    cli()
