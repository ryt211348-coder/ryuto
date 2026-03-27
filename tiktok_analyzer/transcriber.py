"""Whisperを使った動画音声の文字起こし."""

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

console = Console()

_model_cache = {}


def load_whisper_model(model_size: str = "base"):
    """Whisperモデルをロードする（キャッシュ付き）."""
    if model_size in _model_cache:
        return _model_cache[model_size]

    import whisper

    console.print(f"[cyan]Whisperモデル ({model_size}) をロード中...[/cyan]")
    model = whisper.load_model(model_size)
    _model_cache[model_size] = model
    return model


def transcribe_audio(audio_path: Path, model_size: str = "base", language: str = "ja") -> dict:
    """音声ファイルを文字起こしする."""
    model = load_whisper_model(model_size)

    result = model.transcribe(
        str(audio_path),
        language=language,
        verbose=False,
    )

    return {
        "text": result["text"],
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
            }
            for seg in result.get("segments", [])
        ],
        "language": result.get("language", language),
    }


def transcribe_videos(
    audio_dir: Path,
    transcript_dir: Path,
    video_ids: list[str],
    model_size: str = "base",
) -> dict[str, str]:
    """複数の動画音声を一括文字起こしする."""
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcripts = {}

    console.print(f"\n[bold cyan]文字起こし開始 ({len(video_ids)} 本)[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("文字起こし中...", total=len(video_ids))

        for video_id in video_ids:
            audio_path = audio_dir / f"{video_id}.mp3"
            transcript_path = transcript_dir / f"{video_id}.json"
            text_path = transcript_dir / f"{video_id}.txt"

            # 既存の文字起こしがあればスキップ
            if text_path.exists():
                transcripts[video_id] = text_path.read_text(encoding="utf-8")
                progress.update(task, advance=1)
                continue

            if not audio_path.exists():
                console.print(f"  [yellow]スキップ: {video_id} (音声ファイルなし)[/yellow]")
                progress.update(task, advance=1)
                continue

            try:
                result = transcribe_audio(audio_path, model_size)
                transcripts[video_id] = result["text"]

                # JSON保存（セグメント情報付き）
                transcript_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                # プレーンテキスト保存
                text_path.write_text(result["text"], encoding="utf-8")

            except Exception as e:
                console.print(f"  [red]エラー ({video_id}): {e}[/red]")

            progress.update(task, advance=1)

    console.print(f"\n  [green]文字起こし完了: {len(transcripts)}/{len(video_ids)} 本[/green]")
    return transcripts
