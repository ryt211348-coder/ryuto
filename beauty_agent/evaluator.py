"""
Claude Vision自動評価
生成画像の品質をClaude Vision APIで自動評価する
"""

import os
import json
import base64

import anthropic


EVALUATION_PROMPT = """
この画像を以下の基準で評価してください。
各項目を0-20点で採点し、合計100点満点で評価してください。

【評価基準】

① 文字・テキスト混入チェック（0 or 20点）
- 画像内に文字・数字・記号が一切ないか
- ロゴ・透かし・字幕がないか
→ 文字があれば0点、なければ20点

② キャラクターの一貫性（0-20点）
- キャラクター: {character}
- 期待される外見: {character_description}
→ 完全一致20点 / 少しズレ10点 / 別キャラになっている0点

③ 台本内容との合致度（0-20点）
- セリフ: {lines}
- 推定感情: {emotion}
- 推定状況: {situation}
→ セリフの感情・状況と画像が一致しているか

④ 洞窟化・ミクロ世界チェック（0 or 20点）
- 洞窟化防止が必要なキャラか: {cave_prevention}
- 「鏡で見たときの距離感」になっているか
→ 洞窟になっていれば0点、正常なら20点

⑤ 視認性・構図（0-20点）
- キャラクターが画面中央で大きく見えるか
- 9:16縦型構図になっているか
- テキスト用の余白があるか

【回答形式】
必ず以下のJSON形式のみで回答してください。JSON以外の文字は含めないでください。
{{
  "score_text": 点数,
  "score_consistency": 点数,
  "score_content_match": 点数,
  "score_no_cave": 点数,
  "score_visibility": 点数,
  "total": 合計点,
  "result": "OK" or "NG",
  "ng_reason": "NGの場合の理由（OKの場合は空文字）",
  "retry_suggestion": "リトライ時にプロンプトに追加すべき修正指示（OKの場合は空文字）"
}}
"""

# キャラクター説明（評価用）
CHARACTER_DESCRIPTIONS = {
    "皮脂": "golden glossy semi-liquid sebum, face embedded in oil itself",
    "毛穴": "pore structure as character, face formed by pore wall/opening",
    "アクネ菌": "small bacteria character on/between sebum layers",
    "白ニキビ": "whitehead pimple embedded under skin, face on bump surface",
    "赤ニキビ": "inflamed red pimple on skin surface, face within redness",
    "洗顔料": "Pixar-style squeeze tube character in bathroom setting",
}

CAVE_PREVENTION_CHARACTERS = {"毛穴", "アクネ菌", "白ニキビ", "赤ニキビ"}


def evaluate_image(image_path: str, scene: dict, api_key: str = None) -> dict:
    """
    生成画像をClaude Visionで評価

    Args:
        image_path: 評価する画像のパス
        scene: シーン辞書
        api_key: Anthropic APIキー（省略時は環境変数）

    Returns:
        評価結果辞書
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY が設定されていません")

    client = anthropic.Anthropic(api_key=key)

    # 画像をbase64エンコード
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 拡張子からメディアタイプを判定
    ext = os.path.splitext(image_path)[1].lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "image/png")

    character = scene["character"]
    char_desc = CHARACTER_DESCRIPTIONS.get(character, f"Pixar-style {character} character")
    cave_needed = character in CAVE_PREVENTION_CHARACTERS

    prompt = EVALUATION_PROMPT.format(
        character=character,
        character_description=char_desc,
        lines="／".join(scene["lines"][:5]),
        emotion=scene["inferred_emotion"],
        situation=scene["inferred_situation"],
        cave_prevention="はい（洞窟化防止必要）" if cave_needed else "いいえ",
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    # レスポンスからJSONを抽出
    response_text = response.content[0].text.strip()
    try:
        # JSONブロックを抽出（```json ... ``` やプレーンJSON対応）
        if "```" in response_text:
            json_match = response_text.split("```")[1]
            if json_match.startswith("json"):
                json_match = json_match[4:]
            result = json.loads(json_match.strip())
        else:
            result = json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        # パース失敗時のフォールバック
        result = {
            "score_text": 0,
            "score_consistency": 0,
            "score_content_match": 0,
            "score_no_cave": 0,
            "score_visibility": 0,
            "total": 0,
            "result": "NG",
            "ng_reason": f"評価レスポンスのパースに失敗: {response_text[:200]}",
            "retry_suggestion": "再評価してください",
        }

    # OKの閾値: 80点以上
    if result.get("total", 0) >= 80:
        result["result"] = "OK"
    else:
        result["result"] = "NG"

    return result


def evaluate_and_decide(image_path: str, scene: dict) -> dict:
    """
    評価を実行し、OK/NGを判定

    Returns:
        {
            "result": "OK" or "NG",
            "scores": {...},
            "total": int,
            "ng_reason": str,
            "retry_suggestion": str
        }
    """
    eval_result = evaluate_image(image_path, scene)

    return {
        "result": eval_result["result"],
        "scores": {
            "no_text": eval_result.get("score_text", 0),
            "consistency": eval_result.get("score_consistency", 0),
            "content_match": eval_result.get("score_content_match", 0),
            "no_cave": eval_result.get("score_no_cave", 0),
            "visibility": eval_result.get("score_visibility", 0),
        },
        "total": eval_result.get("total", 0),
        "ng_reason": eval_result.get("ng_reason", ""),
        "retry_suggestion": eval_result.get("retry_suggestion", ""),
    }
