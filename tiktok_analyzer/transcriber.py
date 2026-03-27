"""TikTok動画の文字起こし - 複数の方法で取得を試みる."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests as http_requests

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

console = Console()


def _try_scrapecreators(video_url, lang="ja"):
    """ScrapeCreators API でTikTokの字幕を取得する（無料100回）."""
    api_key = os.environ.get("SCRAPECREATORS_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = http_requests.get(
            "https://api.scrapecreators.com/v1/tiktok/video/transcript",
            headers={"x-api-key": api_key},
            params={"url": video_url, "language": lang, "use_ai_as_fallback": "true"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                # "transcript" フィールドがVTT形式の文字列の場合
                raw = data.get("transcript", "")
                if isinstance(raw, str) and raw.strip():
                    if "WEBVTT" in raw or "-->" in raw:
                        return _parse_vtt_text(raw)
                    return raw.strip()
                # transcript配列の場合
                if isinstance(raw, list):
                    texts = [item.get("text", "") for item in raw if isinstance(item, dict)]
                    text = " ".join(texts).strip()
                    if text:
                        return text
                # その他のフィールド
                for key in ["text", "content", "data", "subtitles"]:
                    val = data.get(key, "")
                    if isinstance(val, str) and val.strip():
                        if "WEBVTT" in val or "-->" in val:
                            return _parse_vtt_text(val)
                        return val.strip()
                    if isinstance(val, list):
                        texts = [item.get("text", "") for item in val if isinstance(item, dict)]
                        text = " ".join(texts).strip()
                        if text:
                            return text
        else:
            console.print(f"    [dim]ScrapeCreators: HTTP {resp.status_code}[/dim]")
    except Exception as e:
        console.print(f"    [dim]ScrapeCreators: {e}[/dim]")
    return None


def _parse_vtt_text(vtt_content):
    """VTT形式のテキストからセリフだけを抽出する."""
    lines = vtt_content.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if "-->" in line:
            continue
        if re.match(r"^\d+$", line):
            continue
        if line.startswith("Kind:") or line.startswith("Language:") or line.startswith("NOTE"):
            continue
        # HTMLタグ除去
        line = re.sub(r"<[^>]+>", "", line)
        if line and line not in text_lines:
            text_lines.append(line)
    return " ".join(text_lines).strip() if text_lines else None


def _try_supadata(video_url, lang="ja"):
    """Supadata API でTikTokの字幕を取得する（無料100回）."""
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
    base = output_dir / "temp_sub"

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
        return None

    all_files = []
    for ext in ["vtt", "srt"]:
        all_files.extend(output_dir.glob(f"temp_sub*.{ext}"))

    for f in all_files:
        text = _parse_subtitle_file(f)
        try:
            f.unlink()
        except OSError:
            pass
        if text and len(text.strip()) > 5 and _is_japanese(text):
            return text.strip()

    return None


def _try_whisper(video_url, output_dir, model_size="base"):
    """動画の音声をダウンロードしてWhisperで文字起こし."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "temp_audio.mp3"

    # 音声ダウンロード
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x", "--audio-format", "mp3", "--audio-quality", "0",
        "-o", str(audio_path).replace(".mp3", ".%(ext)s"),
        "--no-warnings", "--quiet",
        video_url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if not audio_path.exists():
        return None

    # Whisper文字起こし
    try:
        import whisper
        model = whisper.load_model(model_size)
        result = model.transcribe(str(audio_path), language="ja", verbose=False)
        text = result.get("text", "")
        try:
            audio_path.unlink()
        except OSError:
            pass
        return text if text else None
    except Exception as e:
        console.print(f"    [dim]Whisper: {e}[/dim]")
        try:
            audio_path.unlink()
        except OSError:
            pass
    return None


def _is_japanese(text):
    """テキストに日本語が含まれるか判定."""
    jp = sum(1 for c in text if '\u3040' <= c <= '\u309f'
             or '\u30a0' <= c <= '\u30ff'
             or '\u4e00' <= c <= '\u9fff')
    return jp > len(text) * 0.1


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
        line = re.sub(r"<[^>]+>", "", line)
        if line and line not in text_lines:
            text_lines.append(line)
    return " ".join(text_lines)


def transcribe_single_video(video_url, video_id, output_dir, whisper_model="base"):
    """1本の動画を文字起こしする。複数の方法を順番に試す."""
    output_dir = Path(output_dir)
    cache_path = output_dir / f"{video_id}.txt"

    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        if text.strip():
            return text.strip()

    methods = [
        ("ScrapeCreators API", lambda: _try_scrapecreators(video_url)),
        ("Supadata API", lambda: _try_supadata(video_url)),
        ("yt-dlp字幕", lambda: _try_ytdlp_subs(video_url, output_dir / "_subs")),
        ("Whisper", lambda: _try_whisper(video_url, output_dir / "_audio", whisper_model)),
    ]

    for method_name, method_fn in methods:
        try:
            text = method_fn()
            if text and len(text.strip()) > 5:
                console.print(f"    [green]{method_name} で取得成功[/green]")
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(text.strip(), encoding="utf-8")
                return text.strip()
        except Exception as e:
            console.print(f"    [dim]{method_name}: {e}[/dim]")

    console.print(f"    [yellow]文字起こし取得失敗[/yellow]")
    return ""


def transcribe_videos(video_list, transcript_dir, whisper_model="base"):
    """複数の動画を一括文字起こしする."""
    transcript_dir = Path(transcript_dir)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcripts = {}

    has_sc = bool(os.environ.get("SCRAPECREATORS_API_KEY"))
    has_sd = bool(os.environ.get("SUPADATA_API_KEY"))

    console.print(f"\n[bold cyan]文字起こし開始 ({len(video_list)} 本)[/bold cyan]")
    console.print(f"  [dim]利用可能な方法:[/dim]")
    console.print(f"    {'[green]✓[/green]' if has_sc else '[red]✗[/red]'} ScrapeCreators API {'(APIキー設定済)' if has_sc else '(SCRAPECREATORS_API_KEY 未設定)'}")
    console.print(f"    {'[green]✓[/green]' if has_sd else '[red]✗[/red]'} Supadata API {'(APIキー設定済)' if has_sd else '(SUPADATA_API_KEY 未設定)'}")
    console.print(f"    [green]✓[/green] yt-dlp 字幕抽出")
    console.print(f"    [green]✓[/green] Whisper 音声文字起こし")
    console.print()

    if not has_sc and not has_sd:
        console.print("  [yellow]ヒント: 無料APIキーを設定すると文字起こしの成功率が大幅に上がります[/yellow]")
        console.print("  [yellow]  export SCRAPECREATORS_API_KEY=your_key  (https://app.scrapecreators.com で無料取得)[/yellow]")
        console.print("  [yellow]  export SUPADATA_API_KEY=your_key  (https://supadata.ai で無料取得)[/yellow]")
        console.print()

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
            text = transcribe_single_video(video_url, video_id, transcript_dir, whisper_model)
            if text:
                transcripts[video_id] = text
            progress.update(task, advance=1)

    success = len(transcripts)
    total = len(video_list)
    console.print(f"\n  [green]文字起こし完了: {success}/{total} 本[/green]")
    return transcripts
