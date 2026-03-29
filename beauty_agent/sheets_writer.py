"""
Googleスプレッドシート書き込み
編集者指示書を自動生成・書き込み
"""

import os


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "シーン番号",
    "キャラクター名",
    "台本セリフ",
    "使用画像（DriveURL）",
    "声質・キャラクター性格指示",
    "ナレーション口調メモ",
    "映像イメージ・編集指示",
    "画像評価スコア",
    "備考・メモ",
]

VOICE_STYLE_MAP = {
    "パニック": "力強い女性声。早口・焦り気味。語尾を上げてパニック感を出す。",
    "悪役・支配": "太い男性声。余裕のある低音。不敵な笑いを含む。ゆっくり話す。",
    "苦しみ": "弱い声。掠れた感じ。詰まりながら話す。語尾が消える。",
    "指導・冷静": "落ち着いた中性声。断定的だが威圧的でない。テンポ均一。",
    "撤退・諦め": "低い男性声。悔しさを滲ませる。語尾が短く切れる。",
    "警告": "低く重い男性声。ゆっくり・強調的。間を取る。",
    "明るい・元気": "明るい女性声。アップテンポ。語尾を上げ気味に。",
    "ニュートラル": "落ち着いた中性声。ゆっくりめ。",
}

VIDEO_STYLE_MAP = {
    "パニック": "カットイン→ズームイン。手ブレ風エフェクト。効果音：ドン！赤みフィルター。",
    "悪役・支配": "ローアングル（見上げ構図）。暗めフィルター。不気味なBGM。",
    "苦しみ": "クローズアップ→揺れエフェクト。画面が圧縮される演出。息苦しいBGM。",
    "指導・冷静": "正面固定。テロップ強調。落ち着いたBGM。清潔感のある明るさ。",
    "撤退・諦め": "フェードアウト。画面が明るくなるエフェクト。スッキリしたBGM。",
    "警告": "赤みフィルター→フラッシュ。警告音。テキスト点滅。",
    "明るい・元気": "明るいカラーグレーディング。ポップなBGM。テンポ早めカット。",
    "ニュートラル": "正面固定。ニュートラルなBGM。",
}


def get_sheets_service(credentials_path: str = None):
    """Google Sheets APIサービスを取得"""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_path = credentials_path or os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json"
    )
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return {
        "sheets": build("sheets", "v4", credentials=creds),
        "drive": build("drive", "v3", credentials=creds),
    }


def create_spreadsheet(services: dict, project_name: str) -> dict:
    """
    新規スプレッドシートを作成

    Returns:
        {"spreadsheet_id": str, "spreadsheet_url": str}
    """
    sheets_service = services["sheets"]

    title = f"【編集者指示書】{project_name}"
    body = {"properties": {"title": title}}

    spreadsheet = (
        sheets_service.spreadsheets().create(body=body, fields="spreadsheetId").execute()
    )
    spreadsheet_id = spreadsheet["spreadsheetId"]
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    return {"spreadsheet_id": spreadsheet_id, "spreadsheet_url": url}


def share_spreadsheet(services: dict, spreadsheet_id: str, email: str = None):
    """スプレッドシートを共有設定"""
    drive_service = services["drive"]

    if email:
        permission = {"type": "user", "role": "writer", "emailAddress": email}
    else:
        permission = {"type": "anyone", "role": "writer"}

    drive_service.permissions().create(
        fileId=spreadsheet_id,
        body=permission,
        fields="id",
    ).execute()


def _get_voice_style(emotion: str) -> str:
    """感情から声質指示を取得"""
    for key, value in VOICE_STYLE_MAP.items():
        if key in emotion:
            return value
    return VOICE_STYLE_MAP["ニュートラル"]


def _get_video_style(emotion: str) -> str:
    """感情から映像指示を取得"""
    for key, value in VIDEO_STYLE_MAP.items():
        if key in emotion:
            return value
    return VIDEO_STYLE_MAP["ニュートラル"]


def _get_narration_memo(character: str, emotion: str, lines: list[str]) -> str:
    """ナレーション口調メモを生成"""
    sample = lines[0] if lines else ""
    return f"キャラ: {character} / 感情: {emotion} / 冒頭セリフ例: 「{sample}」"


def write_instruction_sheet(
    scenes: list[dict],
    drive_urls: list[dict],
    eval_results: list[dict],
    project_name: str,
    credentials_path: str = None,
) -> str:
    """
    全シーンの編集者指示書をスプレッドシートに書き込み

    Args:
        scenes: シーンリスト
        drive_urls: [{"scene_id": int, "drive_url": str}, ...]
        eval_results: [{"scene_id": int, "total": int}, ...]
        project_name: プロジェクト名

    Returns:
        スプレッドシートURL
    """
    services = get_sheets_service(credentials_path)

    # スプレッドシート作成
    result = create_spreadsheet(services, project_name)
    spreadsheet_id = result["spreadsheet_id"]
    spreadsheet_url = result["spreadsheet_url"]

    # 共有設定
    share_spreadsheet(services, spreadsheet_id)

    # drive_urlsとeval_resultsをscene_idでマッピング
    url_map = {item["scene_id"]: item.get("drive_url", "") for item in drive_urls}
    score_map = {item["scene_id"]: item.get("total", 0) for item in eval_results}

    # データ行を構築
    rows = [HEADERS]
    for scene in scenes:
        sid = scene["scene_id"]
        character = scene["character"]
        emotion = scene["inferred_emotion"]
        lines = scene["lines"]

        row = [
            str(sid),
            character,
            "\n".join(lines),
            url_map.get(sid, ""),
            _get_voice_style(emotion),
            _get_narration_memo(character, emotion, lines),
            _get_video_style(emotion),
            str(score_map.get(sid, "")),
            "",
        ]
        rows.append(row)

    # 書き込み
    sheets_service = services["sheets"]
    body = {"values": rows}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="RAW",
        body=body,
    ).execute()

    # ヘッダー行の書式設定（太字・背景色）
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.2,
                            "green": 0.6,
                            "blue": 0.9,
                        },
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # 列幅の自動調整
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": len(HEADERS),
                }
            }
        },
    ]

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    print(f"  📊 スプレッドシート作成完了: {spreadsheet_url}")
    return spreadsheet_url
