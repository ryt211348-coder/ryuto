"""
美容AI制作エージェント - CLI直接実行ヘルパー
Claude Codeのチャットから直接呼び出して使う
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from doc_reader import parse_script
from prompt_engine import generate_prompt
from logger import load_log, save_log, add_manual_feedback, DEFAULT_LOG_STRUCTURE


def parse_and_preview(text: str) -> str:
    """台本テキストをパースしてプレビューを返す"""
    scenes = parse_script(text)
    if not scenes:
        return "シーンが検出されませんでした。台本の形式を確認してください。"

    cave_chars = {"毛穴", "白ニキビ", "赤ニキビ", "アクネ菌"}
    lines = [f"✅ {len(scenes)}シーン検出\n"]
    for s in scenes:
        cave = " ⚠️洞窟防止" if s["character"] in cave_chars else ""
        lines.append(
            f"  Scene {s['scene_id']}: {s['character']}（{s['inferred_emotion']}）{cave}"
        )
        lines.append(f"    セリフ: {' / '.join(s['lines'][:2])}")
        lines.append(f"    状況: {s['inferred_situation']} | 場所: {s['setting']}")
        lines.append("")
    return "\n".join(lines)


def generate_all_prompts(text: str) -> str:
    """台本テキストから全シーンのプロンプトを生成"""
    scenes = parse_script(text)
    if not scenes:
        return "シーンが検出されませんでした。"

    results = []
    for scene in scenes:
        prompt = generate_prompt(scene)
        results.append(
            f"━━━ Scene {scene['scene_id']}: {scene['character']}（{scene['inferred_emotion']}）━━━"
        )
        results.append(prompt)
        results.append("")
    return "\n".join(results)


def generate_single_prompt(text: str, scene_id: int) -> str:
    """特定シーンのプロンプトだけ生成"""
    scenes = parse_script(text)
    for scene in scenes:
        if scene["scene_id"] == scene_id:
            prompt = generate_prompt(scene)
            return (
                f"Scene {scene_id}: {scene['character']}（{scene['inferred_emotion']}）\n\n"
                f"{prompt}"
            )
    return f"Scene {scene_id} が見つかりません"


def show_log_summary() -> str:
    """ログのサマリーを返す"""
    log = load_log()
    lines = ["📊 === OK/NGログ ===\n"]

    # キャラクタープロファイル
    lines.append("🎭 キャラクタープロファイル:")
    for name, p in log.get("character_profiles", {}).items():
        total = p.get("total_attempts", 0)
        ok = p.get("total_ok", 0)
        rate = f"{ok/total:.0%}" if total > 0 else "---"
        cave = " ⚠️洞窟防止" if p.get("cave_prevention_needed") else ""
        lines.append(f"  {name}: {ok}/{total} ({rate}){cave}")
        if p.get("notes"):
            lines.append(f"    📌 {p['notes']}")

    # 最近のログ
    recent = log.get("logs", [])[-10:]
    if recent:
        lines.append(f"\n📝 最近のログ（{len(recent)}件）:")
        for e in reversed(recent):
            icon = "✅" if e["result"] == "OK" else "❌"
            lines.append(
                f"  {icon} {e['date']} {e['project']} Scene{e['scene_id']} "
                f"({e['character']}) = {e['result']} ({e.get('total_score', '-')}点)"
            )
            if e.get("memo"):
                lines.append(f"     💬 {e['memo']}")

    # 学習ルール
    rules = log.get("global_rules_learned", [])
    if rules:
        lines.append(f"\n🧠 学習済みルール:")
        for r in rules:
            lines.append(f"  • {r}")

    return "\n".join(lines)


def show_profiles() -> str:
    """キャラクタープロファイル詳細を返す"""
    log = load_log()
    profiles = log.get("character_profiles", {})

    icons = {"皮脂": "🧴", "毛穴": "🕳", "アクネ菌": "🦠", "白ニキビ": "⚪", "赤ニキビ": "🔴", "洗顔料": "🧼"}
    lines = ["🎭 === キャラクタープロファイル ===\n"]

    for name, p in profiles.items():
        icon = icons.get(name, "🎭")
        total = p.get("total_attempts", 0)
        ok = p.get("total_ok", 0)
        rate = f"{ok/total:.0%}" if total > 0 else "---"

        lines.append(f"━━━ {icon} {name} ━━━")
        lines.append(f"  外見: {p.get('established_appearance', '未設定')}")
        lines.append(f"  洞窟防止: {'必要' if p.get('cave_prevention_needed') else '不要'}")
        lines.append(f"  成功率: {rate} ({ok}/{total})")
        if p.get("notes"):
            lines.append(f"  📌 {p['notes']}")
        ng = p.get("failed_prompt_patterns", [])
        if ng:
            lines.append(f"  ❌ 失敗パターン: {' / '.join(ng[:3])}")
        lines.append("")

    return "\n".join(lines)


def record_feedback(project: str, scene_id: int, result: str, memo: str = "") -> str:
    """手動フィードバックを記録"""
    add_manual_feedback(project, scene_id, result, memo)
    return f"✅ フィードバック記録: {project} Scene {scene_id} → {result}" + (f"\n  メモ: {memo}" if memo else "")


def show_config_status() -> str:
    """設定状態を確認"""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    items = [
        ("Gemini API Key", bool(os.getenv("GEMINI_API_KEY"))),
        ("Anthropic API Key", bool(os.getenv("ANTHROPIC_API_KEY"))),
        ("Google認証ファイル", os.path.exists(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials.json"))),
        ("Drive Folder ID", bool(os.getenv("DRIVE_FOLDER_ID"))),
    ]

    lines = ["⚙️ === 設定状態 ===\n"]
    for label, ok in items:
        icon = "🟢" if ok else "🔴"
        lines.append(f"  {icon} {label}")
    return "\n".join(lines)


if __name__ == "__main__":
    # テスト用
    print(show_config_status())
    print()
    print(show_log_summary())
