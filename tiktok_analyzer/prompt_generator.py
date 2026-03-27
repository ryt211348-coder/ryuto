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
    role: str = ""          # 悪役/弱者/ヒーロー/説明役
    voice_note: str = ""    # 声の雰囲気メモ
    reality_anchor: str = ""  # 現実接続要素（人の手、肌など）
    image_prompt: str = ""
    camera_note: str = ""


# === バイラル映像設計ルール（スプシ分析データより） ===
# 冒頭0.3秒で映像だけで何の動画かわかる
# 等身大+人の手や体が映る（ミクロ世界の覗き見感）
# キャラに手足・眉毛（感情伝達パーツ）
# 非現実要素は「擬人化」だけ、それ以外は現実に寄せる
# 悪いやつは悪い顔、可愛いキャラは可愛い顔
# 動きのアクセント（静止画の羅列NG）

# 全プロンプト共通のスタイル指定
COMMON_STYLE = (
    "Pixar/Disney-style 3D CGI rendering, photorealistic textures with cute cartoon "
    "facial features (big round expressive eyes, eyebrows, small mouth). "
    "The character has tiny arms and hands for emotional gestures. "
    "Vertical 9:16 composition. Highly detailed, cinematic lighting, "
    "shallow depth of field. No text, no watermark, no UI elements."
)

# 全プロンプト共通の禁止事項
COMMON_PROHIBITIONS = (
    "IMPORTANT: The character must be microscopic/tiny scale compared to human body. "
    "Do NOT make the character human-sized. Do NOT make the background abstract or fantasy. "
    "Keep all non-character elements photorealistic. Only the character itself is stylized/cartoon."
)

# キャラ役割に応じた表情テンプレ
ROLE_TEMPLATES = {
    "悪役": "evil/mischievous expression, sinister smirk, narrowed eyes, dark aura",
    "黒幕": "sly grin, scheming expression, half-closed cunning eyes, shadowy lighting",
    "弱者": "distressed expression, teary big eyes, trembling, calling for help",
    "ヒーロー": "heroic determined expression, confident stance, backlit golden glow, power pose",
    "説明役": "serious but friendly expression, one hand raised explaining, neutral warm lighting",
    "締め": "hopeful determined expression, looking directly at viewer, warm golden light",
}

# キャラクター別のビジュアル設定テンプレート
CHARACTER_VISUALS = {
    "髪の毛": {
        "base": "A single anthropomorphic hair strand character standing upright on a real human scalp. Dark brown, textured realistic hair fiber. The character is tiny — surrounding hair strands tower like a forest of trees around it.",
        "environment": "Real human scalp surface with visible pores and skin texture. Other hair strands are much taller than the character, creating a forest-like environment. A real human finger or hand is partially visible at the edge of frame for scale.",
        "role_default": "説明役",
        "reality_anchor": "Human scalp skin texture, real hair strands as forest background, partial human finger visible for scale",
    },
    "皮脂": {
        "base": "An anthropomorphic sebum/oil blob character — glistening yellowish-gold translucent body, sitting smugly inside a real hair follicle/pore cavity. Oily, sticky, gross-looking but with a cute face.",
        "environment": "Inside a real pore cavity. Reddish skin walls surrounding. Oily sheen coating the walls. Other pores visible in the background on real skin surface.",
        "role_default": "悪役",
        "reality_anchor": "Real skin pore interior, realistic sebum texture, skin surface visible in background",
    },
    "毛穴": {
        "base": "An anthropomorphic pore character — a round reddened opening on real skin surface with a face embedded in the pore rim. Slightly inflamed, surrounded by realistic fine skin texture and tiny hair follicles.",
        "environment": "Extreme macro view of real human skin surface. Other pores and fine hairs visible around. Sebum buildup visible inside the pore.",
        "role_default": "弱者",
        "reality_anchor": "Real human skin surface at macro scale, visible pores and fine hairs, human finger approaching in background",
    },
    "シルクシャンプー": {
        "base": "An anthropomorphic shampoo foam character — heroic muscular figure made of white pearlescent shimmering foam. Silk-like iridescent surface. Emerging dramatically from a foam bubble cloud.",
        "environment": "Wet hair strands and scalp in background. Foam bubbles and water droplets floating. Bright clean bathroom lighting. The character is arriving to save the day.",
        "role_default": "ヒーロー",
        "reality_anchor": "Real wet hair strands, water droplets, bathroom shower environment partially visible",
    },
    "後頭部": {
        "base": "The back of a real human head with an annoyed anthropomorphic face appearing on the posterior scalp area. Wet hair parted to reveal the face. Realistic skin and hair texture.",
        "environment": "Bathroom/shower setting with water droplets and steam. Real shower head visible. The face on the back of the head looks neglected and frustrated.",
        "role_default": "説明役",
        "reality_anchor": "Real human head, shower environment, water droplets, steam",
    },
    # --- 美容系汎用キャラ ---
    "ニキビ": {
        "base": "An anthropomorphic pimple/acne character — a red inflamed bump on real human skin with an angry face. Yellowish-white pus visible at the top. Tiny arms crossed defiantly.",
        "environment": "On real human facial skin (cheek or forehead). Other pores and skin texture visible. A real human finger is approaching threateningly from above.",
        "role_default": "悪役",
        "reality_anchor": "Real human facial skin, approaching human finger, visible pores around the pimple",
    },
    "赤ニキビ": {
        "base": "An anthropomorphic red acne character — intensely red and inflamed bump on real skin. Angry face with glowing red eyes. Wearing a tiny military hat and holding a walkie-talkie, screaming. Surrounded by white blood cell battle effects.",
        "environment": "On real human facial skin. Battle scene: white blood cells attacking bacteria around the inflamed area. Human finger looming overhead.",
        "role_default": "悪役",
        "reality_anchor": "Real human facial skin close-up, human finger for scale, visible skin pores",
    },
    "白ニキビ": {
        "base": "An anthropomorphic whitehead character — a pale white sealed bump on real skin with a sly, cool expression. Smooth rounded body with a slightly translucent appearance. Bacteria floating nearby eyeing it hungrily.",
        "environment": "On real human skin surface. Floating bacteria characters nearby. Clean but threatening atmosphere.",
        "role_default": "黒幕",
        "reality_anchor": "Real skin surface, microscopic bacteria visible, skin pore details",
    },
    "黒ニキビ": {
        "base": "An anthropomorphic blackhead character — a dark oxidized bump on real skin with a young energetic face. Dark crumbly particles falling from its head. Standing proudly in an open pore.",
        "environment": "On real human skin, inside an open pore. Oxidized sebum particles falling. Other blackheads visible in nearby pores.",
        "role_default": "悪役",
        "reality_anchor": "Real skin pore opening, oxidized sebum particles, surrounding skin texture",
    },
    "角栓": {
        "base": "An anthropomorphic keratin plug character — a yellowish waxy cylindrical figure with a cheeky grinning face, arms crossed proudly, wedged inside a pore on real human nose skin (strawberry nose).",
        "environment": "Real human nose skin with multiple clogged pores (strawberry nose). The character is one of many plugs. Gross but the character is cute.",
        "role_default": "悪役",
        "reality_anchor": "Real human nose skin close-up, multiple visible clogged pores, skin texture",
    },
    "クレンジングオイル": {
        "base": "An anthropomorphic cleansing oil character — a clear golden oil bottle-shaped figure with a stern but caring female face. Hands on hips. Surrounded by milky emulsified droplets.",
        "environment": "Bathroom setting. A real woman's face partially visible in background (in shower). Water droplets and steam.",
        "role_default": "説明役",
        "reality_anchor": "Real bathroom, partial human face visible, shower water, steam",
    },
    "美容液": {
        "base": "An anthropomorphic serum character — a sleek glass dropper bottle figure with a serious commanding face. Glowing golden liquid body. Standing on a real bathroom counter next to real skincare products.",
        "environment": "Real bathroom vanity. Other skincare bottles visible. Clean bright lighting. Post-shower atmosphere with steam.",
        "role_default": "説明役",
        "reality_anchor": "Real bathroom counter, real skincare products for scale, mirror reflection",
    },
    "日焼け止め": {
        "base": "An anthropomorphic sunscreen tube character — a white tube-shaped figure with a gentle professional face (like a news anchor). Clean, trustworthy appearance. Holding a tiny UV shield.",
        "environment": "Bright sunny window. UV rays visualized as golden arrows being blocked. Real vanity table.",
        "role_default": "ヒーロー",
        "reality_anchor": "Real window with sunlight, real vanity/bathroom setting, UV rays visualization",
    },
    "フェイスパック": {
        "base": "An anthropomorphic face mask/sheet mask character — a flat white sheet-shaped figure with cute pink cheeks and an energetic face. Dripping with essence/serum. Tiny arms waving.",
        "environment": "Real woman's face partially visible (mask being applied or nearby). Bathroom mirror setting. Soft warm lighting.",
        "role_default": "説明役",
        "reality_anchor": "Real human face partially visible, bathroom mirror, skincare products nearby",
    },
    "枕": {
        "base": "An anthropomorphic pillow character — a rectangular yellowed dirty pillow with a villainous face. Evil glowing eyes. Bacteria colonies crawling on its surface. Tiny arms with menacing gestures.",
        "environment": "Real bed/bedroom at night. A real person sleeping with their face on the pillow. Dark moody lighting with bacteria glowing.",
        "role_default": "悪役",
        "reality_anchor": "Real bedroom, real sleeping person's face on the pillow, nighttime lighting",
    },
    "バスタオル": {
        "base": "An anthropomorphic bath towel character — a damp towel figure with a scared young face. Bacteria multiplying visibly on its surface. Shivering and dripping water.",
        "environment": "Real bathroom towel rack. Damp steamy environment. The towel is hanging and looking terrified at the bacteria growing on it.",
        "role_default": "弱者",
        "reality_anchor": "Real bathroom towel rack, steam, water droplets, real bathroom tiles",
    },
    "スポンジ": {
        "base": "An anthropomorphic kitchen/bath sponge character — a rectangular porous sponge with a nerdy intelligent face (glasses optional). Bacteria hidden in the pores. Speaking matter-of-factly.",
        "environment": "Real kitchen sink or bathroom. Wet surface. Other cleaning supplies visible for scale.",
        "role_default": "説明役",
        "reality_anchor": "Real kitchen/bathroom sink, real cleaning supplies, wet surface",
    },
    "角質": {
        "base": "An anthropomorphic dead skin cell / keratin character — a flat flaky greyish-white layered figure with a tough stubborn face. Stacked like bricks inside a pore. Rough dry texture, crumbly edges.",
        "environment": "Inside a real pore on human nose/face skin. Stacked layers of dead cells filling the pore. Sebum mixed in between layers. Macro view of skin surface visible above.",
        "role_default": "悪役",
        "reality_anchor": "Real facial skin pore interior, layered dead skin cells visible, realistic skin texture around pore",
    },
    "いちご鼻": {
        "base": "An anthropomorphic strawberry-nose character — a human nose tip covered in visible dark dots (oxidized sebum plugs in pores), with a taunting villainous face on the nose surface. The dark dots are prominent and gross. The nose itself has a reddish strawberry-like appearance.",
        "environment": "Real human face close-up, centered on the nose. Surrounding cheek skin visible. Mirror reflection or bathroom lighting. Each pore has a dark plug visible.",
        "role_default": "悪役",
        "reality_anchor": "Real human face/nose close-up, visible clogged pores, bathroom mirror setting",
    },
    "クレンジング": {
        "base": "An anthropomorphic cleansing product character — a sleek bottle-shaped female figure with a determined fierce face. Clear/golden oil body that looks powerful. Hands ready to fight. Emulsified milky droplets swirling around her like a battle aura.",
        "environment": "Bathroom counter or sink. Real human hand nearby holding/reaching for the character. Water droplets. Warm soft lighting. Makeup residue and sebum visualized as a dark fortress being dissolved.",
        "role_default": "ヒーロー",
        "reality_anchor": "Real bathroom counter, human hand nearby, water droplets, real skincare bottles in background",
    },
    "洗顔料": {
        "base": "An anthropomorphic face wash character — a tube-shaped muscular male figure with a tough no-nonsense face. Rich foamy lather surrounding him like armor. Charcoal/enzyme particles visible in the foam like tiny soldiers. Standing heroically on a real bathroom shelf.",
        "environment": "Real bathroom. Thick foam clouds around the character. Remnants of dissolved dirt and oil being swept away. Bright clean lighting.",
        "role_default": "ヒーロー",
        "reality_anchor": "Real bathroom shelf, foamy lather, real soap dish or sink visible, human hands in background",
    },
    "美容成分": {
        "base": "An anthropomorphic serum/active ingredient squad — a group of tiny glowing colorful droplet soldiers in formation. The leader is a golden glowing droplet with a commanding general's face. Behind him are 5-6 smaller droplets in different colors (green, orange, white, yellow) each representing different ingredients. Military formation pose.",
        "environment": "On real human skin surface after cleansing — clean, clear pores visible. The squad is marching into the open pores like an army entering a cleared battlefield. Dramatic golden backlight.",
        "role_default": "ヒーロー",
        "reality_anchor": "Real cleansed human skin surface, open empty pores, post-wash clean skin texture",
    },
}

# 感情に応じた表情・演出の修飾
EMOTION_MODIFIERS = {
    "怒り": "angry expression, furrowed brows, gritted teeth, yelling, intense red lighting accent",
    "叫び": "screaming expression, wide open mouth, dramatic lighting, motion blur effect",
    "悲しみ": "sad expression, teary big eyes, downturned mouth, cool blue lighting",
    "恐怖": "terrified expression, wide panicked eyes, trembling body, dark ominous atmosphere",
    "得意": "smug expression, evil confident smirk, chin up, one eyebrow raised, golden lighting",
    "説明": "serious explaining expression, one hand raised in gesture, neutral warm lighting",
    "苦しみ": "agonized expression, squinting eyes, grimacing, being crushed/squeezed, dramatic shadows",
    "訴え": "pleading desperate expression, big teary eyes, reaching out with both hands, emotional lighting",
    "威圧": "intimidating expression, looking down at viewer, crossed arms, dark dramatic lighting, glowing eyes",
    "ヒーロー": "heroic determined expression, dramatic wind blowing, backlit golden glow, power pose, fist raised",
    "笑い": "evil cackling expression, wide grin showing teeth, sneaky narrowed eyes, ominous green lighting",
    "安堵": "relieved expression, gentle smile, soft sigh, warm golden soft lighting",
    "決意": "determined expression, focused sharp eyes, clenched fist, bold dramatic lighting",
    "嘲笑": "mocking expression, tongue out, taunting gesture, looking down at viewer",
    "焦り": "panicking expression, sweating, looking around frantically, chaotic lighting",
}


def detect_emotion(dialogue: str) -> str:
    """セリフから感情を推定する."""
    # 順序重要：より具体的なパターンを先に
    if any(w in dialogue for w in ["ぐあぁ", "うわぁぁ", "やめてくれぇ"]):
        return "叫び"
    if any(w in dialogue for w in ["やめて", "ぇぇ", "うわ", "近づけるな"]):
        return "恐怖"
    if any(w in dialogue for w in ["ハハハ", "ヒヒヒ", "フフフ", "ガハハ", "愚か"]):
        return "嘲笑"
    if any(w in dialogue for w in ["聞け", "引っ込めろ", "怒", "！！", "なれない"]):
        return "怒り"
    if any(w in dialogue for w in ["絶望", "お手上げ", "一生消えない", "一生ない", "放っておいても"]):
        return "威圧"
    if any(w in dialogue for w in ["身動き", "とれない", "助けて", "溺れ", "苦し"]):
        return "苦しみ"
    if any(w in dialogue for w in ["根こそぎ", "引き剥が", "鎧", "守る", "踏み潰", "切る",
                                    "崩す", "溶かせ", "流してやる", "攻め込め", "送り込め",
                                    "俺たちの番"]):
        return "ヒーロー"
    if any(w in dialogue for w in ["うんざり", "待たされ", "いつも最後"]):
        return "怒り"
    if any(w in dialogue for w in ["お願い", "させないで", "2度と", "頼む", "続けてくれ"]):
        return "訴え"
    if any(w in dialogue for w in ["守れば", "サラサラ", "行くぞ"]):
        return "決意"
    if any(w in dialogue for w in ["しなさい", "ちゃんと", "でしょ？", "温めなさい"]):
        return "訴え"
    if any(w in dialogue for w in ["知ってた？", "実は", "正体", "分かってんのか"]):
        return "得意"
    if any(w in dialogue for w in ["選べよ", "だぞ", "だから", "するんだ", "使っとけ"]):
        return "説明"
    return "説明"


def detect_role(dialogue: str, speaker: str, visual: dict | None) -> str:
    """セリフとキャラ設定から役割を推定する."""
    # キャラ設定にデフォルト役割がある場合はそれを基本にする
    default = visual.get("role_default", "説明役") if visual else "説明役"

    # セリフ内容で上書き判定
    if any(w in dialogue for w in ["根こそぎ", "守る", "鎧", "踏み潰", "召喚しろ", "切る"]):
        return "ヒーロー"
    if any(w in dialogue for w in ["やめて", "助けて", "身動き", "溺れ", "苦し", "とれない"]):
        return "弱者"
    if any(w in dialogue for w in ["ハハハ", "ヒヒヒ", "ガハハ", "愚か", "食い荒ら"]):
        return "悪役"
    if any(w in dialogue for w in ["頼む", "守れば", "手順"]):
        return "締め"

    return default


def detect_voice(dialogue: str, speaker: str) -> str:
    """キャラに適した声の雰囲気メモを生成."""
    if any(w in dialogue for w in ["あたし", "〜わよ", "〜の！", "なさい",
                                    "わよ！", "のよ！", "するわ", "崩すわ"]):
        return "女性・芯の通った声・命令口調"
    if any(w in dialogue for w in ["私にしか", "私で"]) and any(w in dialogue for w in ["の！", "わよ", "わ！"]):
        return "女性・芯の通った声・困っている感じ"
    if any(w in dialogue for w in ["俺様", "貴様", "愚か", "ハハハ"]):
        return "男性・20代・威圧的な怒鳴り声"
    if any(w in dialogue for w in ["僕", "だよ", "ちゃう"]):
        return "男性・10代〜20代前半・若くて臆病"
    if any(w in dialogue for w in ["俺は", "だぜ", "だぞ", "してやる"]):
        return "男性・20代・芯のある声"
    if any(w in dialogue for w in ["我が名", "甘いな", "行くぞ"]):
        return "男性・イケボ・低めで落ち着いた声"
    if any(w in dialogue for w in ["こんにちは", "しましょう", "です"]):
        return "男性・アナウンサー風・丁寧で優しい"
    return "20代男性・感情豊かに"


def detect_camera(dialogue: str, speaker: str, role: str) -> str:
    """シーンに適したカメラアングル."""
    if role == "ヒーロー":
        return "Dynamic low angle hero shot, looking up at the character, dramatic backlighting"
    if role == "悪役":
        return "Slightly low angle, character looking down at viewer menacingly"
    if role == "弱者":
        return "High angle looking down at the small helpless character, empathy-inducing"
    if role == "締め":
        return "Eye-level medium shot, character looking directly at camera, warm hopeful lighting"

    # キャラ別のデフォルト
    cam_defaults = {
        "髪の毛": "Extreme macro, low angle looking up at hair strand among forest of other strands",
        "皮脂": "Inside-pore perspective looking up, pore walls visible around edges of frame",
        "毛穴": "Top-down extreme macro of skin surface, centered on the pore character",
        "後頭部": "Over-the-shoulder shot, back of real human head, character face revealed",
        "ニキビ": "Macro close-up of skin, human finger approaching from above, pimple character center frame",
        "枕": "Low angle from pillow level, sleeping person's face above, character looking up menacingly",
    }
    return cam_defaults.get(speaker, "Extreme macro close-up, eye-level with the tiny character, shallow depth of field")


def parse_script(script_text: str) -> list[Scene]:
    """台本テキストをシーンのリストに分割する."""
    scenes = []
    # （話者名）で区切る
    pattern = r'（([^）]+)）'
    parts = re.split(pattern, script_text)

    scene_num = 0
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            speaker = parts[i].strip()
            speaker_base = speaker.split("・")[0] if "・" in speaker else speaker
            dialogue = parts[i + 1].strip()
            if dialogue:
                scene_num += 1
                visual = CHARACTER_VISUALS.get(speaker_base)
                emotion = detect_emotion(dialogue)
                role = detect_role(dialogue, speaker_base, visual)
                voice = detect_voice(dialogue, speaker_base)
                camera = detect_camera(dialogue, speaker_base, role)
                anchor = visual.get("reality_anchor", "") if visual else ""

                scenes.append(Scene(
                    scene_number=scene_num,
                    speaker=speaker,
                    dialogue=dialogue,
                    emotion=emotion,
                    role=role,
                    voice_note=voice,
                    reality_anchor=anchor,
                    camera_note=camera,
                ))

    return scenes


def generate_prompt_for_scene(scene: Scene) -> str:
    """1シーンに対するGemini画像生成プロンプトを組み立てる."""
    speaker_base = scene.speaker.split("・")[0] if "・" in scene.speaker else scene.speaker
    visual = CHARACTER_VISUALS.get(speaker_base)

    if visual:
        base = visual["base"]
        env = visual["environment"]
        anchor = visual.get("reality_anchor", "")
    else:
        base = (
            f"An anthropomorphic {speaker_base} character with a cute face "
            f"(big round eyes, eyebrows, small mouth), tiny arms and hands, "
            f"in a photorealistic environment where this object naturally exists. "
            f"The character is tiny/microscopic scale."
        )
        env = f"Photorealistic environment where a {speaker_base} naturally exists. Real human body part or hand partially visible for scale."
        anchor = "Real human hand or body part partially visible for scale reference"

    # 感情（セリフから） + 役割（ドラマ上の立場）を組み合わせ
    emotion_mod = EMOTION_MODIFIERS.get(scene.emotion, "neutral expression, natural lighting")
    role_mod = ROLE_TEMPLATES.get(scene.role, "")

    # セリフ内容からシーン演出を抽出
    scene_context = _extract_scene_context(scene.dialogue, speaker_base)

    prompt = f"""{base}

[Expression] {emotion_mod}
[Character role] {role_mod}
[Scene action] {scene_context}
[Environment] {env}
[Reality anchor] {anchor}
[Camera] {scene.camera_note}

[Style] {COMMON_STYLE}
[Rules] {COMMON_PROHIBITIONS}"""

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
        "役割",
        "感情",
        "声の雰囲気",
        "カメラ",
        "現実接続要素",
        "画像生成プロンプト",
    ])
    for scene in scenes:
        writer.writerow([
            scene.scene_number,
            scene.speaker,
            scene.dialogue,
            scene.role,
            scene.emotion,
            scene.voice_note,
            scene.camera_note,
            scene.reality_anchor,
            scene.image_prompt,
        ])
    return output.getvalue()


def scenes_to_json(scenes: list[Scene]) -> str:
    """シーンリストをJSON文字列に変換."""
    return json.dumps([asdict(s) for s in scenes], ensure_ascii=False, indent=2)
