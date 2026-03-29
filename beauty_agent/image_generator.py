"""
Gemini API画像生成
"""

import os
import time
from pathlib import Path

import google.generativeai as genai
from PIL import Image
import io


def configure_gemini(api_key: str = None):
    """Gemini APIの設定"""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY が設定されていません")
    genai.configure(api_key=key)


def generate_image(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "9:16",
    max_retries: int = 3,
) -> dict:
    """
    Gemini APIで画像を生成

    Args:
        prompt: 画像生成プロンプト
        output_path: 保存先パス
        aspect_ratio: アスペクト比（デフォルト9:16縦型）
        max_retries: API呼び出しのリトライ回数

    Returns:
        {"success": bool, "path": str, "error": str or None}
    """
    configure_gemini()

    model = genai.ImageGenerationModel("imagen-3.0-generate-002")

    for attempt in range(max_retries):
        try:
            response = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_only_high",
            )

            if not response.images:
                return {
                    "success": False,
                    "path": None,
                    "error": "画像が生成されませんでした（安全フィルターの可能性）",
                }

            # 画像を保存
            image = response.images[0]
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            img = Image.open(io.BytesIO(image._image_bytes))
            img.save(output_path, "PNG")

            return {
                "success": True,
                "path": output_path,
                "error": None,
            }

        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  ⚠️ API エラー（リトライ {attempt + 1}/{max_retries}）: {error_msg}")
                print(f"  {wait}秒待機中...")
                time.sleep(wait)
            else:
                return {
                    "success": False,
                    "path": None,
                    "error": f"API呼び出し失敗（{max_retries}回リトライ後）: {error_msg}",
                }

    return {"success": False, "path": None, "error": "予期しないエラー"}


def generate_scene_image(
    scene: dict,
    prompt: str,
    output_dir: str,
    project_name: str,
) -> dict:
    """
    シーン情報に基づいて画像を生成

    Args:
        scene: シーン辞書
        prompt: 生成プロンプト
        output_dir: 出力ディレクトリ
        project_name: プロジェクト名

    Returns:
        {"success": bool, "path": str, "error": str or None, "scene_id": int}
    """
    scene_id = scene["scene_id"]
    character = scene["character"]
    filename = f"{project_name}_scene{scene_id}_{character}.png"
    output_path = os.path.join(output_dir, filename)

    print(f"  🖼️  Scene {scene_id} ({character}) 生成中...")
    result = generate_image(prompt, output_path)
    result["scene_id"] = scene_id

    if result["success"]:
        print(f"  ✅ Scene {scene_id} 生成完了: {output_path}")
    else:
        print(f"  ❌ Scene {scene_id} 生成失敗: {result['error']}")

    return result
