"""Gemini APIを使って画像を生成するモジュール."""

import base64
import json
import os
import re
import time
from pathlib import Path

import requests


def get_api_key() -> str:
    """環境変数からGemini APIキーを取得."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.environ.get("GEMINI_API_KEY", "")
    return key


def generate_image(prompt: str, output_path: str, api_key: str = "") -> dict:
    """Gemini APIで1枚の画像を生成して保存する.

    Returns:
        dict with keys: success, path, error
    """
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        return {"success": False, "path": "", "error": "GEMINI_API_KEY が設定されていません"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"Generate this image:\n\n{prompt}"
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # レスポンスから画像データを探す
        candidates = data.get("candidates", [])
        for candidate in candidates:
            parts = candidate.get("content", {}).get("parts", [])
            for part in parts:
                inline_data = part.get("inlineData")
                if inline_data and inline_data.get("mimeType", "").startswith("image/"):
                    image_bytes = base64.b64decode(inline_data["data"])
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    return {"success": True, "path": output_path, "error": ""}

        return {"success": False, "path": "", "error": "APIレスポンスに画像が含まれていません"}

    except requests.exceptions.Timeout:
        return {"success": False, "path": "", "error": "タイムアウト（120秒）"}
    except requests.exceptions.HTTPError as e:
        return {"success": False, "path": "", "error": f"API エラー: {e.response.status_code} {e.response.text[:200]}"}
    except Exception as e:
        return {"success": False, "path": "", "error": str(e)}


def generate_all_images(scenes: list, job_dir: str, api_key: str = "",
                        on_progress=None) -> list[dict]:
    """全シーンの画像を順次生成する.

    Args:
        scenes: Sceneオブジェクトのリスト
        job_dir: 画像保存先ディレクトリ
        api_key: Gemini APIキー
        on_progress: callback(scene_number, total, status) 進捗コールバック

    Returns:
        各シーンの結果リスト
    """
    if not api_key:
        api_key = get_api_key()

    results = []
    total = len(scenes)

    for i, scene in enumerate(scenes):
        if on_progress:
            on_progress(i + 1, total, "generating")

        output_path = os.path.join(job_dir, f"scene_{scene.scene_number:02d}_{scene.speaker}.png")
        result = generate_image(scene.image_prompt, output_path, api_key)
        result["scene_number"] = scene.scene_number
        result["speaker"] = scene.speaker
        results.append(result)

        # レート制限対策: シーン間に少し待つ
        if i < total - 1:
            time.sleep(2)

    if on_progress:
        on_progress(total, total, "completed")

    return results
