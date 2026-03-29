"""
美容AI擬人化動画 制作自動化エージェント - Web UI
ブラウザ上で完結する操作画面
"""

import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# beauty_agentのモジュールをインポートできるようにパスを追加
sys.path.insert(0, os.path.dirname(__file__))

from doc_reader import read_document, parse_script
from prompt_engine import generate_prompt, apply_retry_fix
from image_generator import generate_scene_image
from evaluator import evaluate_and_decide
from drive_manager import save_scene_images, get_folder_url
from sheets_writer import write_instruction_sheet
from logger import (
    log_result,
    add_manual_feedback,
    load_log,
    save_log,
    DEFAULT_LOG_PATH,
    DEFAULT_LOG_STRUCTURE,
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# ジョブ管理
jobs = {}


# ========================================
# パイプライン実行（バックグラウンド）
# ========================================


def run_pipeline_job(job_id: str, doc_url: str):
    """バックグラウンドでパイプラインを実行"""
    job = jobs[job_id]
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json")
    project_name = f"美容AI企画_{datetime.now().strftime('%Y%m%d_%H%M')}"
    job["project_name"] = project_name

    try:
        # Step 1: 台本読み込み
        job["status"] = "reading"
        job["message"] = "📄 台本を読み込み中..."
        scenes = read_document(doc_url, creds_path)
        job["scenes"] = scenes
        job["total_scenes"] = len(scenes)
        job["message"] = f"✅ {len(scenes)}シーン検出"

        # Step 2: プロンプト生成
        job["status"] = "prompting"
        job["message"] = "🎨 画像プロンプト生成中..."
        prompts = {}
        for scene in scenes:
            prompts[scene["scene_id"]] = generate_prompt(scene)
        job["prompts"] = prompts
        job["message"] = f"✅ {len(scenes)}シーンのプロンプト生成完了"

        # Step 3: 画像生成 + 評価 + リトライ
        job["status"] = "generating"
        output_dir = os.path.join(
            os.path.dirname(__file__), "output", project_name
        )
        os.makedirs(output_dir, exist_ok=True)

        ok_images = []
        eval_results = []
        scene_results = []

        for i, scene in enumerate(scenes):
            scene_id = scene["scene_id"]
            character = scene["character"]
            prompt = prompts[scene_id]
            retry_count = 0
            max_retries = 3

            job["message"] = f"🖼️ Scene {scene_id}/{len(scenes)} ({character}) 生成中..."
            job["current_scene"] = scene_id
            job["progress"] = i

            scene_status = {
                "scene_id": scene_id,
                "character": character,
                "status": "generating",
                "score": None,
                "result": None,
                "retries": 0,
                "image_path": None,
                "drive_url": None,
            }

            while retry_count <= max_retries:
                gen_result = generate_scene_image(
                    scene, prompt, output_dir, project_name
                )

                if not gen_result["success"]:
                    scene_status["status"] = "failed"
                    scene_status["result"] = "FAILED"
                    log_result(
                        "FAILED",
                        scene,
                        {"scores": {}, "total": 0, "ng_reason": gen_result["error"]},
                        project_name,
                        prompt,
                    )
                    break

                # 評価
                job["message"] = f"🔍 Scene {scene_id} 評価中..."
                eval_result = evaluate_and_decide(gen_result["path"], scene)
                eval_result["scene_id"] = scene_id

                if eval_result["result"] == "OK":
                    scene_status["status"] = "ok"
                    scene_status["result"] = "OK"
                    scene_status["score"] = eval_result["total"]
                    scene_status["image_path"] = gen_result["path"]
                    ok_images.append(
                        {
                            "scene_id": scene_id,
                            "path": gen_result["path"],
                            "character": character,
                        }
                    )
                    eval_results.append(eval_result)
                    log_result("OK", scene, eval_result, project_name, prompt)
                    break
                else:
                    retry_count += 1
                    scene_status["retries"] = retry_count
                    scene_status["score"] = eval_result["total"]

                    if retry_count <= max_retries:
                        job["message"] = (
                            f"⚠️ Scene {scene_id} NG ({eval_result['total']}点) "
                            f"リトライ {retry_count}/{max_retries}..."
                        )
                        prompt = apply_retry_fix(
                            prompt,
                            eval_result.get("retry_suggestion", ""),
                            eval_result.get("ng_reason", ""),
                        )
                        log_result("NG", scene, eval_result, project_name, prompt)
                    else:
                        scene_status["status"] = "failed"
                        scene_status["result"] = "FAILED"
                        eval_results.append(eval_result)
                        log_result(
                            "FAILED", scene, eval_result, project_name, prompt
                        )

            scene_results.append(scene_status)
            job["scene_results"] = scene_results

        job["progress"] = len(scenes)

        # Step 4: Googleドライブに保存
        drive_urls = []
        if ok_images:
            job["status"] = "uploading"
            job["message"] = f"💾 Googleドライブに{len(ok_images)}枚保存中..."
            try:
                drive_urls = save_scene_images(ok_images, project_name, creds_path)
                # scene_resultsにdrive_urlを反映
                url_map = {d["scene_id"]: d["drive_url"] for d in drive_urls}
                for sr in scene_results:
                    if sr["scene_id"] in url_map:
                        sr["drive_url"] = url_map[sr["scene_id"]]
            except Exception as e:
                job["drive_error"] = str(e)

        # Step 5: スプレッドシート作成
        job["status"] = "writing_sheet"
        job["message"] = "📊 スプレッドシート作成中..."
        try:
            spreadsheet_url = write_instruction_sheet(
                scenes, drive_urls, eval_results, project_name, creds_path
            )
            job["spreadsheet_url"] = spreadsheet_url
        except Exception as e:
            job["sheet_error"] = str(e)
            job["spreadsheet_url"] = None

        # 完了
        folder_id = os.getenv("DRIVE_FOLDER_ID", "")
        job["status"] = "completed"
        job["message"] = "✅ 完了！"
        job["ok_count"] = len(ok_images)
        job["drive_folder_url"] = (
            get_folder_url(folder_id) if folder_id else None
        )
        job["scene_results"] = scene_results

    except Exception as e:
        job["status"] = "error"
        job["message"] = f"❌ エラー: {str(e)}"


# ========================================
# ルーティング
# ========================================


@app.route("/")
def index():
    return render_template("beauty_index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    """パイプライン実行開始"""
    data = request.get_json()
    doc_url = data.get("doc_url", "").strip()
    if not doc_url:
        return jsonify({"error": "ドキュメントURLを入力してください"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "queued",
        "message": "開始準備中...",
        "progress": 0,
        "total_scenes": 0,
        "scenes": [],
        "scene_results": [],
    }

    thread = threading.Thread(
        target=run_pipeline_job, args=(job_id, doc_url), daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id):
    """ジョブ状態取得"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "ジョブが見つかりません"}), 404
    return jsonify(job)


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """台本をパースしてプレビュー（実行前の確認用）"""
    data = request.get_json()
    doc_url = data.get("doc_url", "").strip()
    if not doc_url:
        return jsonify({"error": "ドキュメントURLを入力してください"}), 400

    try:
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json")
        scenes = read_document(doc_url, creds_path)
        return jsonify({"scenes": scenes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/parse-text", methods=["POST"])
def api_parse_text():
    """テキスト直貼りで台本パース（Google API不要）"""
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "台本テキストを入力してください"}), 400

    try:
        scenes = parse_script(text)
        return jsonify({"scenes": scenes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/log")
def api_log():
    """ログ取得"""
    log = load_log()
    return jsonify(log)


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """手動フィードバック記録"""
    data = request.get_json()
    project = data.get("project", "").strip()
    scene_id = data.get("scene_id")
    result = data.get("result", "").strip()
    memo = data.get("memo", "").strip()

    if not all([project, scene_id, result]):
        return jsonify({"error": "project, scene_id, result は必須です"}), 400

    add_manual_feedback(project, int(scene_id), result, memo)
    return jsonify({"success": True})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """設定状態の確認"""
    return jsonify(
        {
            "gemini_key": bool(os.getenv("GEMINI_API_KEY")),
            "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            "google_creds": os.path.exists(
                os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json")
            ),
            "drive_folder": bool(os.getenv("DRIVE_FOLDER_ID")),
        }
    )


@app.route("/api/config", methods=["POST"])
def api_set_config():
    """APIキー設定（ランタイム用）"""
    data = request.get_json()
    if data.get("gemini_key"):
        os.environ["GEMINI_API_KEY"] = data["gemini_key"]
    if data.get("anthropic_key"):
        os.environ["ANTHROPIC_API_KEY"] = data["anthropic_key"]
    if data.get("drive_folder_id"):
        os.environ["DRIVE_FOLDER_ID"] = data["drive_folder_id"]
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
