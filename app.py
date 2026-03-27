"""TikTok バイラル動画分析ツール & YouTube チャンネル分析 - Webインターフェース."""

import json
import os
import threading
import uuid
from pathlib import Path

from flask import Flask, render_template, request, jsonify, Response

try:
    from tiktok_analyzer.extractor import (
        extract_account_videos,
        filter_viral_videos,
        save_videos_metadata,
    )
    from tiktok_analyzer.transcriber import transcribe_videos
    from tiktok_analyzer.analyzer import (
        analyze_viral_patterns,
        generate_report,
    )
    TIKTOK_AVAILABLE = True
except ImportError:
    TIKTOK_AVAILABLE = False

from youtube_analyzer.analyzer import analyze_channel

app = Flask(__name__)

# ジョブの進捗を管理
jobs = {}

# APIキーの保存先
CONFIG_PATH = Path(__file__).parent / ".api_config.json"


def load_api_key():
    """保存されたAPIキーを読み込む."""
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            key = data.get("scrapecreators_api_key", "")
            if key:
                os.environ["SCRAPECREATORS_API_KEY"] = key
            return key
        except Exception:
            pass
    return os.environ.get("SCRAPECREATORS_API_KEY", "")


def save_api_key(key):
    """APIキーをファイルに保存する."""
    CONFIG_PATH.write_text(json.dumps({"scrapecreators_api_key": key}))
    os.environ["SCRAPECREATORS_API_KEY"] = key


# 起動時にAPIキーを読み込む
load_api_key()


def run_analysis(job_id: str, account_url: str, min_views: int, whisper_model: str):
    """バックグラウンドで分析を実行する."""
    job = jobs[job_id]

    try:
        output = Path(f"results/{job_id}")
        audio_dir = output / "audio"
        transcript_dir = output / "transcripts"
        audio_dir.mkdir(parents=True, exist_ok=True)
        transcript_dir.mkdir(parents=True, exist_ok=True)

        # Step 1
        job["status"] = "fetching"
        job["message"] = "動画メタデータを取得中..."
        videos = extract_account_videos(account_url)

        if not videos:
            job["status"] = "error"
            job["message"] = "動画が見つかりませんでした。URLを確認してください。"
            return

        job["message"] = f"{len(videos)} 本の動画を検出"

        # Step 2
        job["status"] = "filtering"
        job["message"] = f"{min_views:,}再生以上の動画をフィルタリング中..."
        viral_videos = filter_viral_videos(videos, min_views)

        if not viral_videos:
            top = sorted(videos, key=lambda v: v.view_count, reverse=True)[:10]
            job["status"] = "no_results"
            job["message"] = f"{min_views:,}再生以上の動画がありません"
            job["top_videos"] = [
                {"title": v.title, "views": v.view_count, "url": v.url}
                for v in top
            ]
            return

        job["viral_count"] = len(viral_videos)
        job["message"] = f"{len(viral_videos)} 本のバイラル動画を検出"

        save_videos_metadata(viral_videos, output / "videos.json")

        # Step 3: 文字起こし（字幕抽出 → Whisperフォールバック）
        job["status"] = "transcribing"
        job["progress"] = 0
        job["total"] = len(viral_videos)
        job["message"] = f"文字起こし中 (0/{len(viral_videos)})"

        video_list = [(v.url, v.video_id) for v in viral_videos]
        transcripts = transcribe_videos(
            video_list, transcript_dir, whisper_model
        )

        # Step 5
        job["status"] = "analyzing"
        job["message"] = "バイラルパターンを分析中..."
        analysis = analyze_viral_patterns(viral_videos, transcripts)

        generate_report(viral_videos, transcripts, analysis, output / "analysis_report.md")

        # 結果をジョブに格納
        job["status"] = "completed"
        job["message"] = "分析完了！"
        job["result"] = build_result(viral_videos, transcripts, analysis)

    except Exception as e:
        job["status"] = "error"
        job["message"] = f"エラーが発生しました: {str(e)}"


def build_result(videos, transcripts, analysis):
    """分析結果をフロント用に整形."""
    video_list = []
    for v in sorted(videos, key=lambda x: x.view_count, reverse=True):
        transcript = transcripts.get(v.video_id, "")
        video_list.append({
            "id": v.video_id,
            "title": v.title,
            "url": v.url,
            "views": v.view_count,
            "likes": v.like_count,
            "comments": v.comment_count,
            "shares": v.share_count,
            "duration": v.duration,
            "date": v.upload_date,
            "description": v.description,
            "transcript": transcript,
            "thumbnail": getattr(v, "thumbnail", ""),
        })

    hook_examples = []
    if analysis.hook_patterns:
        for h in sorted(analysis.hook_patterns, key=lambda x: x["views"], reverse=True)[:10]:
            hook_examples.append({
                "views": h["views"],
                "text": h.get("hook_text", ""),
                "formats": h.get("formats", []),
                "appeals": h.get("appeals", []),
                "emotions": h.get("emotions", []),
                "has_question": h.get("hook_has_question", False),
                "has_negative": h.get("hook_has_negative", False),
                "has_curiosity": h.get("hook_has_curiosity", False),
            })

    phrases = [{"phrase": p, "count": c} for p, c in analysis.common_phrases if c >= 2]

    return {
        "stats": {
            "total": analysis.total_videos,
            "avg_views": analysis.avg_views,
            "avg_likes": analysis.avg_likes,
            "avg_duration": analysis.avg_duration,
            "avg_script_length": analysis.avg_script_length,
        },
        "content_formats": [{"name": n, "count": c} for n, c in analysis.content_formats],
        "appeal_types": [{"name": n, "count": c} for n, c in analysis.appeal_types],
        "emotional_triggers": [{"name": n, "count": c} for n, c in analysis.emotional_triggers],
        "structure_patterns": [{"name": n, "count": c} for n, c in analysis.structure_patterns],
        "script_breakdowns": analysis.script_breakdowns,
        "hook_technique_rates": analysis.hook_technique_rates,
        "product_mentions": [{"name": n, "count": c} for n, c in analysis.product_mentions[:20]],
        "top_insights": analysis.top_performing_insights,
        "duration_dist": analysis.duration_distribution,
        "hooks": hook_examples,
        "phrases": phrases,
        "videos": video_list,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def start_analysis():
    data = request.get_json()
    account_url = data.get("account_url", "").strip()
    min_views = int(data.get("min_views", 1_000_000))
    whisper_model = data.get("whisper_model", "base")

    if not account_url:
        return jsonify({"error": "アカウントURLを入力してください"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "queued",
        "message": "分析を開始しています...",
        "progress": 0,
        "total": 0,
    }

    thread = threading.Thread(
        target=run_analysis,
        args=(job_id, account_url, min_views, whisper_model),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "ジョブが見つかりません"}), 404
    return jsonify(job)


@app.route("/api/config", methods=["GET"])
def get_config():
    key = load_api_key()
    return jsonify({"has_key": bool(key), "key_preview": key[:8] + "..." if len(key) > 8 else ""})


@app.route("/api/config", methods=["POST"])
def set_config():
    data = request.get_json()
    key = data.get("api_key", "").strip()
    if not key:
        return jsonify({"error": "APIキーを入力してください"}), 400
    save_api_key(key)
    return jsonify({"success": True, "message": "APIキーを保存しました"})


# --- YouTube チャンネル分析 ---

# YouTubeジョブの進捗管理
youtube_jobs = {}


@app.route("/youtube")
def youtube_page():
    return render_template("youtube.html")


@app.route("/api/youtube/analyze", methods=["POST"])
def youtube_analyze():
    data = request.get_json()
    channel_url = data.get("channel_url", "").strip()

    if not channel_url:
        return jsonify({"error": "チャンネルURLを入力してください"}), 400

    job_id = str(uuid.uuid4())[:8]
    youtube_jobs[job_id] = {
        "status": "queued",
        "message": "分析を開始しています...",
    }

    thread = threading.Thread(
        target=run_youtube_analysis,
        args=(job_id, channel_url),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


def run_youtube_analysis(job_id: str, channel_url: str):
    """YouTubeチャンネル分析をバックグラウンドで実行."""
    job = youtube_jobs[job_id]

    try:
        def progress_callback(status, message):
            job["status"] = status
            job["message"] = message

        result = analyze_channel(channel_url, progress_callback=progress_callback)

        job["status"] = "completed"
        job["message"] = "分析完了！"
        job["result"] = result

    except Exception as e:
        job["status"] = "error"
        job["message"] = f"エラーが発生しました: {str(e)}"


@app.route("/api/youtube/status/<job_id>")
def youtube_status(job_id):
    job = youtube_jobs.get(job_id)
    if not job:
        return jsonify({"error": "ジョブが見つかりません"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
