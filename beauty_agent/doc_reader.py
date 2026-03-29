"""
Googleドキュメント読み込み・台本パース
"""

import re
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build


ROLE_PATTERNS = {
    "villain": ["アクネ菌", "細菌", "ウイルス", "雑菌"],
    "victim": ["毛穴", "肌", "髪の毛", "頭皮"],
    "enabler": ["皮脂", "汚れ", "水分不足"],
    "hero": ["洗顔料", "シャンプー", "化粧水", "日焼け止め", "保湿"],
    "result": ["白ニキビ", "赤ニキビ", "ニキビ", "乾燥"],
    "narrator": ["締め", "まとめ", "結論"],
}

EMOTION_KEYWORDS = {
    "パニック": ["やめて", "緊急", "危ない", "！！", "ヤバい"],
    "悪役・支配": ["ガハハ", "俺の縄張り", "最高だな", "楽園"],
    "苦しみ": ["詰まってる", "息できない", "限界", "…！"],
    "指導・冷静": ["落ち着いて", "〜だけでいい", "朝と夜", "それで十分"],
    "撤退・諦め": ["チッ", "居場所がない", "引くしかない", "もう終わり"],
    "警告": ["出てくるぞ", "皮膚科", "炎症", "覚悟"],
}


def get_docs_service(credentials_path: str):
    """Google Docs APIサービスを取得"""
    scopes = ["https://www.googleapis.com/auth/documents.readonly"]
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=scopes
    )
    return build("docs", "v1", credentials=creds)


def extract_document_id(url: str) -> str:
    """GoogleドキュメントURLからドキュメントIDを抽出"""
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"無効なGoogleドキュメントURL: {url}")
    return match.group(1)


def fetch_document_text(service, doc_id: str) -> str:
    """ドキュメントの全テキストを取得"""
    doc = service.documents().get(documentId=doc_id).execute()
    text = ""
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    text += run["textRun"]["content"]
    return text


def infer_role(character_name: str) -> str:
    """キャラクター名から役割を推定"""
    for role, keywords in ROLE_PATTERNS.items():
        for keyword in keywords:
            if keyword in character_name:
                return role
    return "unknown"


def infer_emotion(lines: list[str]) -> str:
    """セリフから感情を推定"""
    combined = "".join(lines)
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[emotion] = score

    if not scores:
        return "ニュートラル"
    return max(scores, key=scores.get)


def infer_situation(character_name: str, lines: list[str], emotion: str) -> str:
    """キャラクター・セリフ・感情から状況を推定"""
    combined = "".join(lines)

    situation_hints = []
    if "洗顔" in combined or "泡" in combined:
        situation_hints.append("洗顔中")
    if "毛穴" in combined or "詰まっ" in combined:
        situation_hints.append("毛穴の詰まり")
    if "炎症" in combined or "赤" in combined:
        situation_hints.append("炎症状態")
    if "食べ" in combined or "エサ" in combined:
        situation_hints.append("皮脂を消費中")
    if "洗面台" in combined or "鏡" in combined:
        situation_hints.append("バスルーム")

    if not situation_hints:
        if "パニック" in emotion:
            situation_hints.append("緊急事態")
        elif "悪役" in emotion:
            situation_hints.append("支配状態")
        elif "苦しみ" in emotion:
            situation_hints.append("圧迫状態")
        else:
            situation_hints.append("通常状態")

    return "・".join(situation_hints)


def infer_setting(character_name: str, lines: list[str]) -> str:
    """シーンの場所を推定"""
    combined = "".join(lines)

    if "洗面台" in combined or "洗顔料" in character_name:
        return "バスルーム・洗面台"
    if "毛穴" in character_name:
        return "皮膚表面・毛穴付近"
    if "ニキビ" in character_name:
        return "皮膚表面・炎症部位"
    if "アクネ菌" in character_name:
        return "毛穴内・皮脂層"
    if "皮脂" in character_name:
        return "毛穴の中・皮膚表面"
    if "髪" in character_name or "頭皮" in character_name:
        return "頭皮・髪の毛"
    return "皮膚表面"


def parse_script(text: str) -> list[dict]:
    """
    台本テキストをパースしてシーンリストに変換

    区切り線(---)以降を台本として扱い、
    （キャラクター名）パターンでシーン分割する
    """
    # --- 以降を台本部分として抽出
    parts = re.split(r"-{3,}", text)
    if len(parts) < 2:
        # 区切り線がない場合は全体を台本として扱う
        script_text = text
    else:
        script_text = "".join(parts[1:])

    # 「台本」行を除去
    script_text = re.sub(r"^台本\s*\n", "", script_text.strip(), flags=re.MULTILINE)

    # （キャラクター名）または（キャラクター名・補足）でシーン分割
    character_pattern = re.compile(r"（([^）]+)）")
    lines = script_text.split("\n")

    scenes = []
    current_character = None
    current_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = character_pattern.match(line)
        if match:
            # 前のキャラクターのシーンを保存
            if current_character and current_lines:
                scenes.append({
                    "character": current_character,
                    "lines": current_lines,
                })
            # 新しいキャラクター開始
            char_text = match.group(1)
            # 「・」で分割して名前と補足を分離
            if "・" in char_text:
                current_character = char_text.split("・")[0]
            else:
                current_character = char_text
            current_lines = []
        elif current_character:
            current_lines.append(line)

    # 最後のシーンを追加
    if current_character and current_lines:
        scenes.append({
            "character": current_character,
            "lines": current_lines,
        })

    # 各シーンに追加情報を付与
    result = []
    for i, scene in enumerate(scenes, 1):
        character = scene["character"]
        lines = scene["lines"]
        emotion = infer_emotion(lines)

        result.append({
            "scene_id": i,
            "character": character,
            "lines": lines,
            "inferred_emotion": emotion,
            "inferred_situation": infer_situation(character, lines, emotion),
            "character_role": infer_role(character),
            "setting": infer_setting(character, lines),
        })

    return result


def read_document(doc_url: str, credentials_path: str) -> list[dict]:
    """
    GoogleドキュメントURLから台本を読み込み、シーンリストを返す

    Args:
        doc_url: GoogleドキュメントのURL
        credentials_path: サービスアカウントJSON認証ファイルのパス

    Returns:
        シーンリスト（parse_scriptの出力形式）
    """
    service = get_docs_service(credentials_path)
    doc_id = extract_document_id(doc_url)
    text = fetch_document_text(service, doc_id)
    return parse_script(text)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使い方: python doc_reader.py <Google Doc URL>")
        sys.exit(1)

    import os
    from dotenv import load_dotenv

    load_dotenv()
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json")
    scenes = read_document(sys.argv[1], creds_path)
    print(json.dumps(scenes, ensure_ascii=False, indent=2))
