"""台本からAI画像生成プロンプトを自動生成するモジュール."""

import csv
import io
import json
import re
from dataclasses import dataclass, field, asdict


@dataclass
class Scene:
    """台本の1シーン."""
    scene_number: int
    speaker: str
    dialogue: str
    emotion: str = ""
    image_prompt: str = ""
    camera_note: str = ""


# キャラクター別のビジュアル設定テンプレート
CHARACTER_VISUALS = {
    "髪の毛": {
        "base": "A single anthropomorphic hair strand character with a tiny face (expressive eyes and mouth), small arms and legs, standing upright on a human scalp surface. Macro photography perspective, microscopic scale. The hair strand is dark brown, textured, with realistic hair fiber detail.",
        "environment": "Surrounded by other hair strands in the background, scalp skin texture visible, warm lighting.",
        "style": "Pixar-style 3D CGI rendering, photorealistic textures with cartoon facial features, vertical 9:16 composition.",
    },
    "皮脂": {
        "base": "An anthropomorphic sebum/oil blob character with a mischievous face, glistening yellowish-gold translucent body, sitting inside a hair follicle/pore. Macro photography perspective, microscopic scale.",
        "environment": "Inside a pore cavity, reddish skin walls surrounding, oily sheen, warm reddish lighting from below.",
        "style": "Pixar-style 3D CGI rendering, translucent glossy material with cartoon facial features, vertical 9:16 composition.",
    },
    "毛穴": {
        "base": "An anthropomorphic pore character — a round opening on skin surface with a distressed face embedded in the pore rim. The pore is slightly inflamed and reddened, surrounded by fine skin texture.",
        "environment": "Close-up of skin surface, tiny hair follicles visible, slightly reddish glow from irritation.",
        "style": "Pixar-style 3D CGI rendering, realistic skin texture with cartoon facial features, vertical 9:16 composition.",
    },
    "シルクシャンプー": {
        "base": "An anthropomorphic shampoo foam/bubble character — a heroic figure made of white pearlescent foam with a determined face. Shimmering silk-like iridescent surface, muscular foam body.",
        "environment": "Dramatic entrance scene, foam bubbles floating around, wet hair strands in background, bright clean lighting.",
        "style": "Pixar-style 3D CGI rendering, iridescent pearlescent material with cartoon facial features, vertical 9:16 composition.",
    },
    "後頭部": {
        "base": "A view of the back of a human head (posterior scalp area) with an anthropomorphic face appearing on the back of the head. The face looks annoyed/frustrated. Hair is wet and parted to reveal the face.",
        "environment": "Bathroom/shower setting, water droplets, steam, warm lighting.",
        "style": "Pixar-style 3D CGI rendering, realistic wet hair and skin with cartoon facial features, vertical 9:16 composition.",
    },
}

# 感情に応じた表情・演出の修飾
EMOTION_MODIFIERS = {
    "怒り": "angry expression, furrowed brows, gritted teeth, intense red lighting accent",
    "叫び": "screaming expression, wide open mouth, dramatic lighting, motion blur effect",
    "悲しみ": "sad expression, teary eyes, downturned mouth, cool blue lighting",
    "恐怖": "terrified expression, wide eyes, trembling, dark ominous atmosphere",
    "得意": "smug/proud expression, confident smirk, chin up, warm golden lighting",
    "説明": "explaining expression, one hand raised in gesture, neutral warm lighting",
    "苦しみ": "agonized expression, squinting eyes, grimacing, dramatic shadows",
    "訴え": "pleading expression, desperate eyes, reaching out with hands, emotional lighting",
    "威圧": "intimidating expression, looking down at viewer, dark dramatic lighting",
    "ヒーロー": "heroic expression, dramatic wind effect, backlit glow, power pose",
    "笑い": "laughing expression, evil grin, sneaky eyes, ominous green lighting",
    "安堵": "relieved expression, gentle smile, soft warm lighting, peaceful atmosphere",
    "決意": "determined expression, focused eyes, clenched fist, bold lighting",
}


def detect_emotion(dialogue: str) -> str:
    """セリフから感情を推定する."""
    if any(w in dialogue for w in ["やめて", "ぇぇ", "うわ"]):
        return "恐怖"
    if any(w in dialogue for w in ["ヒヒヒ", "フフフ", "ハハハ", "笑"]):
        return "笑い"
    if any(w in dialogue for w in ["！！", "一生", "できない", "なれない"]):
        return "怒り"
    if any(w in dialogue for w in ["身動き", "とれない", "助けて", "苦し"]):
        return "苦しみ"
    if any(w in dialogue for w in ["根こそぎ", "引き剥が", "鎧", "守る"]):
        return "ヒーロー"
    if any(w in dialogue for w in ["うんざり", "待たされ", "いつも"]):
        return "怒り"
    if any(w in dialogue for w in ["頼む", "守れば", "サラサラ"]):
        return "決意"
    if any(w in dialogue for w in ["しなさい", "ちゃんと", "でしょ？"]):
        return "訴え"
    if any(w in dialogue for w in ["だぞ", "だから", "するんだ"]):
        return "説明"
    return "説明"


def detect_camera(dialogue: str, speaker: str) -> str:
    """シーンに適したカメラアングルの補足を生成."""
    if speaker in ["髪の毛"]:
        return "Extreme macro close-up, low angle looking up at the hair strand character"
    if speaker in ["皮脂"]:
        return "Inside-pore perspective, looking up from within the follicle"
    if speaker in ["毛穴"]:
        return "Top-down macro view of skin surface, centered on the pore"
    if speaker in ["シルクシャンプー"]:
        return "Dynamic low angle, hero entrance shot with foam particles"
    if speaker in ["後頭部"]:
        return "Over-the-shoulder perspective, looking at the back of the head"
    return "Medium close-up, eye-level with the character"


def parse_script(script_text: str) -> list[Scene]:
    """台本テキストをシーンのリストに分割する."""
    scenes = []
    # （話者名）で区切る
    pattern = r'（([^）]+)）'
    parts = re.split(pattern, script_text)

    # partsは ['前文', '話者1', 'セリフ1', '話者2', 'セリフ2', ...] の形式
    scene_num = 0
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            speaker = parts[i].strip()
            # 「・」で区切られた付加情報（例:「髪の毛・締め」）を処理
            speaker_base = speaker.split("・")[0] if "・" in speaker else speaker
            dialogue = parts[i + 1].strip()
            if dialogue:
                scene_num += 1
                emotion = detect_emotion(dialogue)
                camera = detect_camera(dialogue, speaker_base)
                scenes.append(Scene(
                    scene_number=scene_num,
                    speaker=speaker,
                    dialogue=dialogue,
                    emotion=emotion,
                    camera_note=camera,
                ))

    return scenes


def generate_prompt_for_scene(scene: Scene) -> str:
    """1シーンに対するGemini画像生成プロンプトを組み立てる."""
    speaker_base = scene.speaker.split("・")[0] if "・" in scene.speaker else scene.speaker

    # キャラクタービジュアルの取得
    visual = CHARACTER_VISUALS.get(speaker_base)

    if visual:
        base = visual["base"]
        env = visual["environment"]
        style = visual["style"]
    else:
        # 未定義キャラクターのフォールバック
        base = f"An anthropomorphic {speaker_base} character with a face, tiny arms and legs, in a microscopic/macro photography setting."
        env = "Detailed realistic environment matching the character's nature."
        style = "Pixar-style 3D CGI rendering, photorealistic textures with cartoon facial features, vertical 9:16 composition."

    # 感情修飾の追加
    emotion_mod = EMOTION_MODIFIERS.get(scene.emotion, "neutral expression, natural lighting")

    # セリフの内容からシーン固有の演出を追加
    scene_specific = _extract_scene_context(scene.dialogue, speaker_base)

    prompt = f"""{base}

Expression & mood: {emotion_mod}
Scene context: {scene_specific}
Environment: {env}
Camera: {scene.camera_note}

{style}
Highly detailed, cinematic lighting, shallow depth of field, no text or watermark."""

    return prompt.strip()


def _extract_scene_context(dialogue: str, speaker: str) -> str:
    """セリフの内容からシーン固有の演出情報を抽出."""
    contexts = []

    if "サラサラ" in dialogue and "なれない" in dialogue:
        contexts.append("The hair looks dry, frizzy, and damaged. Frustrated gesture.")
    elif "サラサラ" in dialogue:
        contexts.append("The hair looks silky smooth and shiny. Satisfied pose.")

    if "居座" in dialogue:
        contexts.append("The character is firmly planted/stuck in place, looking immovable and stubborn.")

    if "シャンプー" in dialogue and "滑る" in dialogue:
        contexts.append("Shampoo bubbles sliding off the surface ineffectively.")

    if "38℃" in dialogue or "湯船" in dialogue:
        contexts.append("Warm bath water steam rising, thermometer showing 38°C, relaxing warm atmosphere.")

    if "バター" in dialogue and "溶ける" in dialogue:
        contexts.append("Visual metaphor: a small butter cube melting nearby, warmth waves radiating.")

    if "予洗い" in dialogue or "お湯で" in dialogue:
        contexts.append("Warm water flowing down over hair strands, pre-rinse washing scene.")

    if "7割" in dialogue or "流せる" in dialogue:
        contexts.append("Dirt and oil particles being washed away by water stream, 70% clean visualization.")

    if "やめて" in dialogue:
        contexts.append("The character is being washed away/dissolved, panicking and losing grip.")

    if "根こそぎ" in dialogue or "引き剥が" in dialogue:
        contexts.append("Dramatic action scene: foam hero pulling out the sebum villain from the pore.")

    if "シルクタンパク" in dialogue or "鎧" in dialogue:
        contexts.append("Silky protective coating forming around hair strands like armor, shimmering shield effect.")

    if "耳の後ろ" in dialogue or "襟足" in dialogue:
        contexts.append("Focus on the neglected areas behind ears and nape, looking dusty and unwashed.")

    if "入念に" in dialogue:
        contexts.append("Thorough scrubbing motion, detailed cleaning action.")

    if "手順" in dialogue or "守れば" in dialogue:
        contexts.append("Triumphant final pose, checklist/steps visualization in background, hopeful atmosphere.")

    if not contexts:
        contexts.append(f"The {speaker} character is speaking/expressing themselves animatedly.")

    return " ".join(contexts)


def generate_all_prompts(script_text: str) -> list[Scene]:
    """台本テキストから全シーンのプロンプトを生成."""
    scenes = parse_script(script_text)
    for scene in scenes:
        scene.image_prompt = generate_prompt_for_scene(scene)
    return scenes


def scenes_to_csv(scenes: list[Scene]) -> str:
    """シーンリストをCSV文字列に変換."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "シーン番号",
        "話者",
        "セリフ",
        "感情",
        "カメラ",
        "画像生成プロンプト",
    ])
    for scene in scenes:
        writer.writerow([
            scene.scene_number,
            scene.speaker,
            scene.dialogue,
            scene.emotion,
            scene.camera_note,
            scene.image_prompt,
        ])
    return output.getvalue()


def scenes_to_json(scenes: list[Scene]) -> str:
    """シーンリストをJSON文字列に変換."""
    return json.dumps([asdict(s) for s in scenes], ensure_ascii=False, indent=2)
