"""TikTok バイラル動画分析ツール - メインエントリーポイント."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from tiktok_analyzer.extractor import (
    extract_account_videos,
    filter_viral_videos,
    download_video_audio,
    save_videos_metadata,
)
from tiktok_analyzer.transcriber import transcribe_videos
from tiktok_analyzer.analyzer import (
    analyze_viral_patterns,
    print_analysis,
    generate_report,
)

console = Console()


@click.group()
def cli():
    """TikTok バイラル動画分析ツール"""
    pass


@cli.command()
@click.argument("account_url")
@click.option("--min-views", default=1_000_000, help="最低再生数（デフォルト: 1,000,000）")
@click.option("--whisper-model", default="base", help="Whisperモデル（tiny/base/small/medium/large）")
@click.option("--output-dir", default="./results", help="出力ディレクトリ")
@click.option("--language", default="ja", help="文字起こし言語（デフォルト: ja）")
@click.option("--skip-transcribe", is_flag=True, help="文字起こしをスキップ")
def analyze(account_url, min_views, whisper_model, output_dir, language, skip_transcribe):
    """TikTokアカウントのバイラル動画を分析する.

    ACCOUNT_URL: TikTokアカウントのURL (例: https://www.tiktok.com/@username)
    """
    console.print(Panel(
        "[bold cyan]TikTok バイラル動画分析ツール[/bold cyan]\n"
        f"対象: {account_url}\n"
        f"最低再生数: {min_views:,}\n"
        f"Whisperモデル: {whisper_model}",
        title="設定",
    ))

    output = Path(output_dir)
    audio_dir = output / "audio"
    transcript_dir = output / "transcripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: 動画メタデータ取得
    console.print(Panel("[bold]Step 1/4: 動画メタデータ取得[/bold]", style="blue"))
    videos = extract_account_videos(account_url)

    if not videos:
        console.print("[red]動画が見つかりませんでした。URLを確認してください。[/red]")
        return

    # Step 2: バイラル動画フィルタリング
    console.print(Panel("[bold]Step 2/4: バイラル動画フィルタリング[/bold]", style="blue"))
    viral_videos = filter_viral_videos(videos, min_views)

    if not viral_videos:
        console.print(f"[yellow]{min_views:,}再生以上の動画が見つかりませんでした。[/yellow]")
        console.print("[yellow]--min-views オプションで閾値を下げてみてください。[/yellow]")

        # 再生数上位10本を表示
        top_videos = sorted(videos, key=lambda v: v.view_count, reverse=True)[:10]
        if top_videos:
            console.print("\n[bold]再生数上位10本:[/bold]")
            for i, v in enumerate(top_videos, 1):
                console.print(f"  {i}. {v.view_count:>12,}再生 | {v.title[:50]}")
        return

    save_videos_metadata(viral_videos, output / "videos.json")

    # Step 3: 音声ダウンロード & 文字起こし
    transcripts = {}
    if not skip_transcribe:
        console.print(Panel("[bold]Step 3/4: 音声ダウンロード & 文字起こし[/bold]", style="blue"))

        # 音声ダウンロード
        console.print("[cyan]音声ダウンロード中...[/cyan]")
        downloaded_ids = []
        for video in viral_videos:
            result = download_video_audio(video, audio_dir)
            if result:
                downloaded_ids.append(video.video_id)
                console.print(f"  [green]✓[/green] {video.video_id} ({video.view_count:,}再生)")
            else:
                console.print(f"  [red]✗[/red] {video.video_id} (ダウンロード失敗)")

        # 文字起こし
        if downloaded_ids:
            transcripts = transcribe_videos(
                audio_dir, transcript_dir, downloaded_ids, whisper_model
            )
    else:
        console.print(Panel("[bold]Step 3/4: 文字起こしスキップ[/bold]", style="yellow"))
        # 既存のtranscriptを読み込む
        for video in viral_videos:
            txt_path = transcript_dir / f"{video.video_id}.txt"
            if txt_path.exists():
                transcripts[video.video_id] = txt_path.read_text(encoding="utf-8")

    # Step 4: 分析
    console.print(Panel("[bold]Step 4/4: バイラルパターン分析[/bold]", style="blue"))
    analysis = analyze_viral_patterns(viral_videos, transcripts)

    # 結果表示
    print_analysis(analysis)

    # レポート生成
    generate_report(viral_videos, transcripts, analysis, output / "analysis_report.md")

    console.print(Panel(
        f"[bold green]分析完了！[/bold green]\n\n"
        f"結果ディレクトリ: {output}\n"
        f"  - videos.json: 動画メタデータ\n"
        f"  - transcripts/: 文字起こしテキスト\n"
        f"  - analysis_report.md: 分析レポート",
        title="完了",
        style="green",
    ))


@cli.command()
@click.argument("account_url")
@click.option("--min-views", default=1_000_000, help="最低再生数")
def list_videos(account_url, min_views):
    """アカウントの動画一覧を表示する（ダウンロードなし）."""
    videos = extract_account_videos(account_url)
    if videos:
        filter_viral_videos(videos, min_views)


if __name__ == "__main__":
    cli()
