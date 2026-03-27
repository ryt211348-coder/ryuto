"""TikTok動画の文字起こし - 複数の方法で取得を試みる."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

console = Console()


def _try_supadata(video_url, lang="ja"):
    """Supadata API で TikTok の字幕を取得する（無料100回/月）."""
    api_key = os.environ.get("SUPADATA_API_KEY", "")
    if not api_key:
        return None

    try:
        from supadata import Supadata
        client = Supadata(api_key=api_key)
        result = client.transcript(url=video_url, lang=lang, text=True)
        if result and hasattr(result, "text") and result.text:
            return result.text
        if isinstance(result, str) and result.strip():
            return result
    except Exception as e:
        console.print(f"    [dim]Supadata: {e}[/dim]")
    return None


def _try_ytdlp_subs(video_url, output_dir):
    """yt-dlp でTikTokの自動字幕を抽出する."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 字幕ファイルのベース名
    base = output_dir / "temp_sub"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs", "ja,jpn,ja-JP",
        "--sub-format", "vtt/srt/best",
        "--skip-download",
        "-o", str(base) + ".%(ext)s",
        "--no-warnings",
        "--quiet",
        video_url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    # 生成された字幕ファイルを探す（日本語優先）
    all_files = []
    for ext in ["vtt", "srt"]:
        all_files.extend(output_dir.glob(f"temp_sub*.{ext}"))

    best_text = None
    for f in all_files:
        text = _parse_subtitle_file(f)
        try:
            f.unlink()
        except OSError:
            pass
        if text and len(text.strip()) > 5:
            if _is_japanese(text):
                return text.strip()
            # 日本語でない場合は一旦保持（日本語が見つからなければ使わない）
            if best_text is None:
                best_text = text.strip()

    # 日本語字幕が見つからなかった場合はNoneを返す（Whisperにフォールバック）
    return None


def _is_japanese(text):
    """テキストに日本語（ひらがな・カタカナ・漢字）が含まれるか判定."""
    japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u309f'   # ひらがな
                        or '\u30a0' <= c <= '\u30ff'   # カタカナ
                        or '\u4e00' <= c <= '\u9fff')   # 漢字
    return japanese_chars > len(text) * 0.1


def _parse_subtitle_file(filepath):
    """VTT/SRTファイルからテキストだけを抽出する."""
    try:
        content = Path(filepath).read_text(encoding="utf-8")
    except Exception:
        return None

    lines = content.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        # タイムスタンプ行をスキップ
        if re.match(r"^\d{2}:\d{2}", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            continue
        if not line:
            continue
        # HTMLタグを除去
        line = re.sub(r"<[^>]+>", "", line)
        if line and line not in text_lines:
            text_lines.append(line)

    return " ".join(text_lines)


def _try_whisper(audio_path, model_size="base", language="ja"):
    """Whisper で音声からテキストに変換する（フォールバック）."""
    try:
        import whisper
    except ImportError:
        console.print("    [dim]Whisper未インストール[/dim]")
        return None

    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(str(audio_path), language=language, verbose=False)
        return result.get("text", "")
    except Exception as e:
        console.print(f"    [dim]Whisper: {e}[/dim]")
        return None


def _download_audio(video_url, output_dir):
    """yt-dlp で動画の音声をダウンロードする."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "temp_audio.mp3"

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", str(output_path).replace(".mp3", ".%(ext)s"),
        "--no-warnings", "--quiet",
        video_url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if output_path.exists():
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def transcribe_single_video(video_url, video_id, output_dir, whisper_model="base"):
    """1本の動画を文字起こしする。複数の方法を順番に試す."""
    output_dir = Path(output_dir)
    cache_path = output_dir / f"{video_id}.txt"

    # キャッシュチェック
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        if text.strip():
            return text.strip()

    text = None

    # 方法1: Supadata API（TikTokの字幕を直接取得）
    text = _try_supadata(video_url)
    if text:
        console.print(f"    [green]Supadata で取得成功[/green]")
        cache_path.write_text(text, encoding="utf-8")
        return text

    # 方法2: yt-dlp で自動字幕を抽出
    text = _try_ytdlp_subs(video_url, output_dir / "_subs")
    if text:
        console.print(f"    [green]yt-dlp 字幕で取得成功[/green]")
        cache_path.write_text(text, encoding="utf-8")
        return text

    # 方法3: Whisper（音声をダウンロードして文字起こし）
    audio_path = _download_audio(video_url, output_dir / "_audio")
    if audio_path:
        text = _try_whisper(str(audio_path), whisper_model)
        # 一時音声ファイル削除
        try:
            audio_path.unlink()
        except OSError:
            pass
        if text:
            console.print(f"    [green]Whisper で取得成功[/green]")
            cache_path.write_text(text, encoding="utf-8")
            return text

    console.print(f"    [yellow]文字起こし取得失敗[/yellow]")
    return ""


def transcribe_videos(video_list, transcript_dir, whisper_model="base"):
    """複数の動画を一括文字起こしする.

    video_list: [(video_url, video_id), ...] のリスト
    """
    transcript_dir = Path(transcript_dir)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcripts = {}

    console.print(f"\n[bold cyan]文字起こし開始 ({len(video_list)} 本)[/bold cyan]")
    console.print(f"  [dim]方法: Supadata API → yt-dlp字幕 → Whisper[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("文字起こし中...", total=len(video_list))

        for video_url, video_id in video_list:
            progress.update(task, description=f"文字起こし: {video_id}")
            text = transcribe_single_video(
                video_url, video_id, transcript_dir, whisper_model
            )
            if text:
                transcripts[video_id] = text
            progress.update(task, advance=1)

    success = len(transcripts)
    total = len(video_list)
    console.print(f"\n  [green]文字起こし完了: {success}/{total} 本[/green]")
    return transcripts
