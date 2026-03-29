"""
美容AI擬人化動画 制作自動化エージェント
メインエントリーポイント

使い方:
    python agent.py run --doc-url "https://docs.google.com/document/d/..."
    python agent.py run --auto
    python agent.py regenerate --project "美容AI企画7" --scene 3
    python agent.py feedback --project "美容AI企画7" --scene 3 --result NG --memo "洞窟になってる"
    python agent.py log --show
    python agent.py profile --all
"""

import argparse
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

from doc_reader import read_document, parse_script
from prompt_engine import generate_prompt, apply_retry_fix
from image_generator import generate_scene_image
from evaluator import evaluate_and_decide
from drive_manager import save_scene_images, get_folder_url
from sheets_writer import write_instruction_sheet
from logger import (
    log_result,
    add_manual_feedback,
    show_log,
    show_profiles,
    load_log,
)


def run_pipeline(doc_url: str):
    """
    メインパイプライン: 台本読み込み → 画像生成 → 評価 → 保存 → 指示書作成

    Args:
        doc_url: GoogleドキュメントのURL
    """
    start_time = time.time()
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json")

    # プロジェクト名を日時から生成
    project_name = f"美容AI企画_{datetime.now().strftime('%Y%m%d_%H%M')}"

    print(f"\n🚀 美容AI制作エージェント起動")
    print(f"   プロジェクト: {project_name}")

    # ============================
    # 1. 台本読み込み
    # ============================
    print(f"\n📄 台本を読み込み中...")
    scenes = read_document(doc_url, creds_path)
    print(f"   ✅ {len(scenes)}シーン検出")

    print(f"\n🎭 キャラクター解析完了:")
    for scene in scenes:
        cave_warn = " ⚠️洞窟防止" if scene["character"] in ("毛穴", "白ニキビ", "赤ニキビ", "アクネ菌") else ""
        print(f"   Scene {scene['scene_id']}: {scene['character']}（{scene['inferred_emotion']}）{cave_warn}")

    # ============================
    # 2. プロンプト生成
    # ============================
    print(f"\n🎨 画像プロンプト生成中...")
    prompts = {}
    for scene in scenes:
        prompt = generate_prompt(scene)
        prompts[scene["scene_id"]] = prompt
        cave_msg = "（洞窟防止ルール適用済み）" if scene["character"] in ("毛穴", "白ニキビ", "赤ニキビ", "アクネ菌") else ""
        print(f"   Scene {scene['scene_id']} プロンプト生成 ✅ {cave_msg}")

    # ============================
    # 3. 画像生成 + 評価 + リトライ
    # ============================
    print(f"\n🖼️  Gemini APIで画像生成中...")
    output_dir = os.path.join("output", project_name)
    os.makedirs(output_dir, exist_ok=True)

    ok_images = []  # {"scene_id", "path", "character"}
    eval_results = []  # {"scene_id", "total", "result", ...}

    for scene in scenes:
        scene_id = scene["scene_id"]
        character = scene["character"]
        prompt = prompts[scene_id]
        retry_count = 0
        max_retries = 3

        while retry_count <= max_retries:
            # 画像生成
            gen_result = generate_scene_image(scene, prompt, output_dir, project_name)

            if not gen_result["success"]:
                print(f"   ❌ Scene {scene_id} 画像生成失敗: {gen_result['error']}")
                log_result(
                    "FAILED", scene,
                    {"scores": {}, "total": 0, "ng_reason": gen_result["error"]},
                    project_name, prompt,
                )
                break

            # 評価
            print(f"   🔍 Scene {scene_id} 評価中...")
            eval_result = evaluate_and_decide(gen_result["path"], scene)
            eval_result["scene_id"] = scene_id

            if eval_result["result"] == "OK":
                score = eval_result["total"]
                print(f"   ✅ Scene {scene_id} スコア{score}点 → OK")
                ok_images.append({
                    "scene_id": scene_id,
                    "path": gen_result["path"],
                    "character": character,
                })
                eval_results.append(eval_result)
                log_result("OK", scene, eval_result, project_name, prompt)
                break
            else:
                retry_count += 1
                score = eval_result["total"]
                reason = eval_result.get("ng_reason", "")
                print(f"   ⚠️  Scene {scene_id} スコア{score}点 → NG（{reason}）", end="")

                if retry_count <= max_retries:
                    print(f" リトライ{retry_count}/{max_retries}")
                    prompt = apply_retry_fix(
                        prompt,
                        eval_result.get("retry_suggestion", ""),
                        reason,
                    )
                    log_result("NG", scene, eval_result, project_name, prompt)
                else:
                    print(f" ※最大リトライ回数到達")
                    eval_results.append(eval_result)
                    log_result("FAILED", scene, eval_result, project_name, prompt)
                    print(f"   📢 りゅうとさんへ: Scene {scene_id}({character})は手動確認が必要です")

    # ============================
    # 4. Googleドライブに保存
    # ============================
    drive_urls = []
    if ok_images:
        print(f"\n💾 Googleドライブに保存中...")
        drive_urls = save_scene_images(ok_images, project_name, creds_path)
        print(f"   ✅ {len(ok_images)}枚保存完了")

        folder_id = os.getenv("DRIVE_FOLDER_ID", "")
        if folder_id:
            print(f"   📁 フォルダ: {get_folder_url(folder_id)}")

    # ============================
    # 5. スプレッドシート作成
    # ============================
    print(f"\n📊 スプレッドシート作成中...")
    spreadsheet_url = write_instruction_sheet(
        scenes, drive_urls, eval_results, project_name, creds_path
    )
    print(f"   「【編集者指示書】{project_name}」を作成 ✅")
    print(f"   全{len(scenes)}シーンの指示書を書き込み ✅")

    # ============================
    # 6. 完了
    # ============================
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print(f"\n📝 ログ更新完了")
    print(f"\n✅ 完了！")
    print(f"   スプレッドシート: {spreadsheet_url}")
    if folder_id:
        print(f"   Driveフォルダ: {get_folder_url(folder_id)}")
    print(f"   OK画像: {len(ok_images)}/{len(scenes)}枚")
    print(f"   処理時間: {minutes}分{seconds}秒")


def regenerate_scene(project_name: str, scene_id: int):
    """特定シーンだけリトライ"""
    log = load_log()

    # ログから該当シーンの情報を検索
    target = None
    for entry in reversed(log["logs"]):
        if entry["project"] == project_name and entry["scene_id"] == scene_id:
            target = entry
            break

    if not target:
        print(f"❌ {project_name} の Scene {scene_id} がログに見つかりません")
        sys.exit(1)

    character = target["character"]
    prompt = target.get("prompt_used", "")

    if not prompt:
        print(f"❌ プロンプトが記録されていません。--doc-url から再実行してください")
        sys.exit(1)

    print(f"\n🔄 リジェネレート: {project_name} Scene {scene_id} ({character})")

    scene = {
        "scene_id": scene_id,
        "character": character,
        "lines": [],
        "inferred_emotion": "",
        "inferred_situation": "",
        "character_role": "",
        "setting": "",
    }

    output_dir = os.path.join("output", project_name)
    os.makedirs(output_dir, exist_ok=True)

    gen_result = generate_scene_image(scene, prompt, output_dir, project_name)
    if gen_result["success"]:
        eval_result = evaluate_and_decide(gen_result["path"], scene)
        print(f"   スコア: {eval_result['total']}点 → {eval_result['result']}")
        log_result(eval_result["result"], scene, eval_result, project_name, prompt)
    else:
        print(f"   ❌ 生成失敗: {gen_result['error']}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="美容AI擬人化動画 制作自動化エージェント"
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # run コマンド
    run_parser = subparsers.add_parser("run", help="パイプライン実行")
    run_parser.add_argument("--doc-url", help="GoogleドキュメントのURL")
    run_parser.add_argument("--auto", action="store_true", help="最新企画を自動取得")

    # regenerate コマンド
    regen_parser = subparsers.add_parser("regenerate", help="特定シーンをリトライ")
    regen_parser.add_argument("--project", required=True, help="プロジェクト名")
    regen_parser.add_argument("--scene", type=int, required=True, help="シーン番号")

    # feedback コマンド
    fb_parser = subparsers.add_parser("feedback", help="手動フィードバック記録")
    fb_parser.add_argument("--project", required=True, help="プロジェクト名")
    fb_parser.add_argument("--scene", type=int, required=True, help="シーン番号")
    fb_parser.add_argument("--result", required=True, choices=["OK", "NG"], help="結果")
    fb_parser.add_argument("--memo", default="", help="メモ")

    # log コマンド
    log_parser = subparsers.add_parser("log", help="ログ表示")
    log_parser.add_argument("--show", action="store_true", help="ログを表示")

    # profile コマンド
    profile_parser = subparsers.add_parser("profile", help="キャラクタープロファイル")
    profile_parser.add_argument("--all", action="store_true", help="全プロファイル表示")

    args = parser.parse_args()

    if args.command == "run":
        if args.auto:
            print("⚠️  --auto モードは未実装です。--doc-url を使用してください。")
            sys.exit(1)
        if not args.doc_url:
            print("❌ --doc-url を指定してください")
            sys.exit(1)
        run_pipeline(args.doc_url)

    elif args.command == "regenerate":
        regenerate_scene(args.project, args.scene)

    elif args.command == "feedback":
        add_manual_feedback(args.project, args.scene, args.result, args.memo)

    elif args.command == "log":
        show_log()

    elif args.command == "profile":
        show_profiles()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
