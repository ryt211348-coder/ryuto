"""TikTok バイラル動画分析ツール - Webインターフェース."""

import json
import threading
import uuid
from pathlib import Path

from flask import Flask, render_template, request, jsonify, Response

from tiktok_analyzer.extractor import (
    extract_account_videos,
    filter_viral_videos,
    download_video_audio,
    save_videos_metadata,
)
from tiktok_analyzer.transcriber import transcribe_videos
from tiktok_analyzer.analyzer import (
    analyze_viral_patterns,
    generate_report,
)

app = Flask(__name__)

# ジョブの進捗を管理
jobs: dict[str, dict] = {}


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

        # Step 3
        job["status"] = "downloading"
        job["progress"] = 0
        job["total"] = len(viral_videos)
        downloaded_ids = []

        for i, video in enumerate(viral_videos):
            job["message"] = f"音声ダウンロード中 ({i + 1}/{len(viral_videos)})"
            job["progress"] = i
            result = download_video_audio(video, audio_dir)
            if result:
                downloaded_ids.append(video.video_id)

        # Step 4
        job["status"] = "transcribing"
        job["progress"] = 0
        job["total"] = len(downloaded_ids)
        job["message"] = f"文字起こし中 (0/{len(downloaded_ids)})"

        transcripts = {}
        if downloaded_ids:
            transcripts = transcribe_videos(
                audio_dir, transcript_dir, downloaded_ids, whisper_model
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
        })

    hook_examples = []
    if analysis.hook_patterns:
        for h in sorted(analysis.hook_patterns, key=lambda x: x["views"], reverse=True)[:10]:
            hook_examples.append({
                "views": h["views"],
                "text": h["text"],
                "keywords": h.get("matched_keywords", []),
                "has_question": h.get("has_question", False),
                "has_negative": h.get("has_negative_hook", False),
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
        "patterns": {
            "question_rate": analysis.question_usage_rate,
            "negative_hook_rate": analysis.negative_hook_rate,
            "number_rate": analysis.number_usage_rate,
            "cta_rate": analysis.cta_usage_rate,
            "urgency_rate": analysis.urgency_words_rate,
        },
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
