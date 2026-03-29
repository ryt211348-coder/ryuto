"""
Googleドライブ管理
画像をGoogleドライブの「AI編集者様」フォルダに保存
"""

import os
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]


def get_drive_service(credentials_path: str = None):
    """Google Drive APIサービスを取得"""
    creds_path = credentials_path or os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json"
    )
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def get_or_create_folder(
    service, folder_name: str, parent_folder_id: str = None
) -> str:
    """フォルダを取得、なければ作成してIDを返す"""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    results = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # フォルダ作成
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_image(
    service,
    local_path: str,
    folder_id: str,
    filename: str = None,
) -> dict:
    """
    画像をGoogleドライブにアップロード

    Args:
        service: Drive APIサービス
        local_path: ローカルファイルパス
        folder_id: アップロード先フォルダID
        filename: ドライブ上のファイル名（省略時はローカルファイル名）

    Returns:
        {"id": str, "name": str, "webViewLink": str}
    """
    if filename is None:
        filename = os.path.basename(local_path)

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaFileUpload(local_path, mimetype="image/png", resumable=True)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )

    return {
        "id": file["id"],
        "name": file["name"],
        "webViewLink": file.get("webViewLink", ""),
    }


def save_scene_images(
    image_paths: list[dict],
    project_name: str,
    credentials_path: str = None,
) -> list[dict]:
    """
    プロジェクトの全シーン画像をGoogleドライブに保存

    Args:
        image_paths: [{"scene_id": int, "path": str, "character": str}, ...]
        project_name: プロジェクト名
        credentials_path: 認証ファイルパス

    Returns:
        [{"scene_id": int, "drive_url": str, "file_id": str}, ...]
    """
    service = get_drive_service(credentials_path)

    # AI編集者様フォルダIDを環境変数から取得
    base_folder_id = os.getenv("DRIVE_FOLDER_ID")
    if not base_folder_id:
        raise ValueError("DRIVE_FOLDER_ID が設定されていません")

    # プロジェクト用サブフォルダを作成
    project_folder_id = get_or_create_folder(
        service, project_name, base_folder_id
    )

    results = []
    for item in image_paths:
        scene_id = item["scene_id"]
        local_path = item["path"]
        character = item.get("character", "unknown")

        filename = f"scene{scene_id}_{character}.png"
        print(f"  📤 Scene {scene_id} ({character}) アップロード中...")

        uploaded = upload_image(service, local_path, project_folder_id, filename)
        results.append(
            {
                "scene_id": scene_id,
                "drive_url": uploaded["webViewLink"],
                "file_id": uploaded["id"],
            }
        )
        print(f"  ✅ Scene {scene_id} アップロード完了")

    return results


def get_folder_url(folder_id: str) -> str:
    """フォルダIDからURLを生成"""
    return f"https://drive.google.com/drive/folders/{folder_id}"
