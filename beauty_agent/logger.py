"""
OK/NGログ管理・学習
feedback_log.jsonへの読み書き・次回学習反映
"""

import json
import os
from datetime import datetime


DEFAULT_LOG_PATH = os.path.join(os.path.dirname(__file__), "feedback_log.json")

DEFAULT_LOG_STRUCTURE = {
    "logs": [],
    "character_profiles": {
        "皮脂": {
            "established_appearance": "golden glossy semi-liquid, face embedded in oil",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": False,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
        },
        "毛穴": {
            "established_appearance": "pore structure as character, face formed by wall",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": True,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
            "notes": "断面図禁止を必ず入れること",
        },
        "アクネ菌": {
            "established_appearance": "small bacteria on sebum layers",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": True,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
        },
        "白ニキビ": {
            "established_appearance": "whitehead pimple embedded under skin",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": True,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
            "notes": "NOT inside a cavity を必ず入れること",
        },
        "赤ニキビ": {
            "established_appearance": "inflamed red pimple on skin surface",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": True,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
            "notes": "断面図禁止・鏡の距離感 を必ず入れること",
        },
        "洗顔料": {
            "established_appearance": "squeeze tube character in bathroom",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": False,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
        },
    },
    "global_rules_learned": [
        "断面図禁止 を毛穴・ニキビ系に必ず入れると洞窟化が防げる",
        "皮脂とアクネ菌を同じシーンに入れる時はSebumにNO faceを明記",
        "白ニキビはNOT inside a cavityを入れないとミクロ世界になる",
        "洗顔料はポンプ式でなくチューブ型にすると主役感が出る",
        "白背景×白キャラは同化するのでパステルカラーを指定すること",
    ],
}


def load_log(log_path: str = None) -> dict:
    """ログファイルを読み込み（なければ初期構造を返す）"""
    path = log_path or DEFAULT_LOG_PATH
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(DEFAULT_LOG_STRUCTURE))


def save_log(data: dict, log_path: str = None):
    """ログファイルを保存"""
    path = log_path or DEFAULT_LOG_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_result(
    result: str,
    scene: dict,
    eval_result: dict,
    project_name: str,
    prompt_used: str = "",
    manual_override: str = None,
    memo: str = "",
    log_path: str = None,
):
    """
    評価結果をログに記録

    Args:
        result: "OK", "NG", or "FAILED"
        scene: シーン辞書
        eval_result: 評価結果辞書
        project_name: プロジェクト名
        prompt_used: 使用したプロンプト
        manual_override: 手動オーバーライド（"OK"/"NG" or None）
        memo: メモ
    """
    log = load_log(log_path)

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "project": project_name,
        "scene_id": scene["scene_id"],
        "character": scene["character"],
        "prompt_used": prompt_used,
        "result": result,
        "scores": eval_result.get("scores", {}),
        "total_score": eval_result.get("total", 0),
        "manual_override": manual_override,
        "memo": memo,
    }
    log["logs"].append(entry)

    # キャラクタープロファイル更新
    character = scene["character"]
    if character not in log["character_profiles"]:
        log["character_profiles"][character] = {
            "established_appearance": "",
            "successful_prompt_patterns": [],
            "failed_prompt_patterns": [],
            "cave_prevention_needed": False,
            "success_rate": 0.0,
            "total_attempts": 0,
            "total_ok": 0,
        }

    profile = log["character_profiles"][character]
    profile["total_attempts"] = profile.get("total_attempts", 0) + 1

    if result == "OK":
        profile["total_ok"] = profile.get("total_ok", 0) + 1
    elif result == "NG" or result == "FAILED":
        ng_reason = eval_result.get("ng_reason", "")
        if ng_reason and ng_reason not in profile.get("failed_prompt_patterns", []):
            profile.setdefault("failed_prompt_patterns", []).append(ng_reason)

    # 成功率更新
    total = profile.get("total_attempts", 0)
    ok = profile.get("total_ok", 0)
    profile["success_rate"] = round(ok / total, 2) if total > 0 else 0.0

    save_log(log, log_path)


def add_manual_feedback(
    project_name: str,
    scene_id: int,
    result: str,
    memo: str = "",
    log_path: str = None,
):
    """手動フィードバックを追加"""
    log = load_log(log_path)

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "project": project_name,
        "scene_id": scene_id,
        "character": "",
        "prompt_used": "",
        "result": result,
        "scores": {},
        "total_score": 0,
        "manual_override": result,
        "memo": memo,
    }

    # 既存ログからキャラクター名を検索
    for existing in reversed(log["logs"]):
        if existing["project"] == project_name and existing["scene_id"] == scene_id:
            entry["character"] = existing["character"]
            break

    log["logs"].append(entry)
    save_log(log, log_path)
    print(f"  📝 フィードバック記録: {project_name} Scene {scene_id} → {result}")
    if memo:
        print(f"     メモ: {memo}")


def show_log(log_path: str = None):
    """ログ内容を表示"""
    log = load_log(log_path)

    print("\n📊 === OK/NGログ ===\n")

    # キャラクタープロファイル
    print("🎭 キャラクタープロファイル:")
    for name, profile in log.get("character_profiles", {}).items():
        total = profile.get("total_attempts", 0)
        ok = profile.get("total_ok", 0)
        rate = profile.get("success_rate", 0)
        cave = "⚠️洞窟防止必要" if profile.get("cave_prevention_needed") else ""
        print(f"  {name}: {ok}/{total} ({rate:.0%}) {cave}")
        if profile.get("notes"):
            print(f"    📌 {profile['notes']}")

    # 最近のログ
    print(f"\n📝 最近のログ（直近10件）:")
    for entry in log.get("logs", [])[-10:]:
        icon = "✅" if entry["result"] == "OK" else "❌"
        override = f" [手動→{entry['manual_override']}]" if entry.get("manual_override") else ""
        print(
            f"  {icon} {entry['date']} {entry['project']} "
            f"Scene{entry['scene_id']} ({entry['character']}) "
            f"= {entry['result']}{override}"
        )
        if entry.get("memo"):
            print(f"     💬 {entry['memo']}")

    # グローバルルール
    print(f"\n🧠 学習済みルール:")
    for rule in log.get("global_rules_learned", []):
        print(f"  • {rule}")


def show_profiles(log_path: str = None):
    """キャラクタープロファイルの詳細表示"""
    log = load_log(log_path)

    print("\n🎭 === キャラクタープロファイル詳細 ===\n")
    for name, profile in log.get("character_profiles", {}).items():
        print(f"━━━ {name} ━━━")
        print(f"  外見: {profile.get('established_appearance', '未設定')}")
        print(f"  洞窟防止: {'必要' if profile.get('cave_prevention_needed') else '不要'}")
        print(f"  成功率: {profile.get('success_rate', 0):.0%} ({profile.get('total_ok', 0)}/{profile.get('total_attempts', 0)})")

        ok_patterns = profile.get("successful_prompt_patterns", [])
        if ok_patterns:
            print(f"  ✅ 成功パターン:")
            for p in ok_patterns:
                print(f"     • {p}")

        ng_patterns = profile.get("failed_prompt_patterns", [])
        if ng_patterns:
            print(f"  ❌ 失敗パターン:")
            for p in ng_patterns:
                print(f"     • {p}")

        if profile.get("notes"):
            print(f"  📌 {profile['notes']}")
        print()
