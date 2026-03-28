"""kotoba-whisper文字起こしモジュール - 日本語特化の高精度文字起こし."""

import os
import subprocess
import tempfile


def download_video_audio(video_url, output_path=None):
    """動画URLから音声をダウンロード.

    Args:
        video_url: 動画のURL
        output_path: 保存先パス（省略時はtmpファイル）

    Returns:
        音声ファイルのパス
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".mp3")

    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_path,
        video_url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    return output_path


def transcribe_audio(audio_path, model_name="kotoba-tech/kotoba-whisper-v2.0"):
    """音声ファイルを文字起こし.

    kotoba-whisper-v2.0を使用（日本語CER 9.2%の高精度）。
    M4 Macではmpsバックエンドで高速動作。

    Args:
        audio_path: 音声ファイルパス
        model_name: whisperモデル名

    Returns:
        文字起こしテキスト
    """
    try:
        import torch
        from transformers import pipeline

        # M4 Mac対応: mpsバックエンド優先
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        pipe = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device,
            chunk_length_s=30,
        )

        result = pipe(
            audio_path,
            return_timestamps=True,
            generate_kwargs={"language": "ja", "task": "transcribe"},
        )

        return result["text"]

    except ImportError:
        # transformers未インストール時はwhisperにフォールバック
        return _transcribe_with_whisper_cli(audio_path)


def _transcribe_with_whisper_cli(audio_path):
    """whisper CLIでフォールバック文字起こし."""
    cmd = [
        "whisper",
        audio_path,
        "--model", "large-v3",
        "--language", "ja",
        "--output_format", "txt",
        "--output_dir", tempfile.gettempdir(),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)

    txt_path = os.path.splitext(audio_path)[0] + ".txt"
    alt_path = os.path.join(
        tempfile.gettempdir(),
        os.path.splitext(os.path.basename(audio_path))[0] + ".txt"
    )

    for path in [txt_path, alt_path]:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return f.read().strip()

    return ""


def transcribe_video(video_url, model_name="kotoba-tech/kotoba-whisper-v2.0"):
    """動画URLから文字起こしまで一括実行.

    Args:
        video_url: 動画URL
        model_name: whisperモデル名

    Returns:
        文字起こしテキスト
    """
    audio_path = None
    try:
        audio_path = download_video_audio(video_url)
        text = transcribe_audio(audio_path, model_name)
        return text
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
