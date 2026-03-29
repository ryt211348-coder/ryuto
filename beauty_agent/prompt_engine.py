"""
プロンプト生成エンジン
キャラクター別のPixar風3D画像プロンプトを生成する
"""

import json
import os

# ========================================
# キャラクター別ベースデザイン
# ========================================

CHARACTER_DESIGNS = {
    "皮脂": {
        "base": """A golden glossy semi-liquid sebum character.
The FACE IS EMBEDDED IN THE OIL ITSELF — not a separate body.
No independent body — the sebum IS the character.
Texture: thick, shiny, viscous golden oil with slight translucency.""",
        "emotions": {
            "パニック": """Eyes: wide and panicked, darting side to side
Eyebrows: raised high in alarm
Mouth: open, shouting urgently
Arms: waving frantically, uncontrollably spreading""",
            "安定": """Eyes: calm, minimal expression
Mouth: neutral, slight curve
Arms: still, relaxed""",
            "消費中": """Eyes: shocked and desperate
Eyebrows: raised in disbelief
Mouth: screaming
Arms: breaking apart, dissolving""",
            "悪役・支配": """Eyes: narrow and confident, gleaming
Eyebrows: angled down in arrogance
Mouth: wide grin, laughing
Arms: spread wide, claiming territory""",
            "撤退・諦め": """Eyes: narrowed in frustration
Eyebrows: furrowed
Mouth: tight, teeth clenched
Arms: pulling back, retreating""",
        },
        "composition": """[COMPOSITION]
Character fills center frame (60% of screen)
Upper space left empty for text overlay
Vertical mobile-first framing

[CAMERA]
Macro lens feel, shallow depth of field
Close-up on character face and expression

[LIGHTING]
Warm golden highlights on oil texture
Slight glow from within the sebum mass""",
        "forbidden": """[CRITICAL - DO NOT]
DO NOT create a solid ball or sphere character
DO NOT make sebum look like acne bacteria
DO NOT add text or labels""",
        "cave_prevention_needed": False,
    },
    "毛穴": {
        "base": """The PORE STRUCTURE ITSELF IS THE CHARACTER.
The inner wall or opening forms the face (like a tunnel mouth).
Face is PART OF THE SKIN TISSUE, not a separate object.
Eyes: formed by natural bulges/folds in pore wall
Mouth: stretched opening of the pore wall (organic tissue, NOT lips)""",
        "emotions": {
            "苦しみ": """Eyes: squinting in pain, barely open
Eyebrows: pushed together in agony
Mouth: compressed, gasping
The pore walls are squeezed tight""",
            "パニック": """Eyes: wide with panic
Eyebrows: raised high
Mouth: wide open screaming
Pore walls trembling""",
            "安定": """Eyes: calm, relaxed
Mouth: neutral opening
Pore walls smooth and relaxed""",
            "警告": """Eyes: stern and intense
Eyebrows: furrowed
Mouth: tight, serious expression""",
        },
        "composition": """[COMPOSITION]
Character fills center frame
Skin surface visible around the pore
Upper space left for text overlay
Vertical 9:16 framing

[CAMERA]
Macro view from above skin surface
NOT inside the pore

[LIGHTING]
Natural skin-tone lighting
Soft shadows showing skin texture""",
        "forbidden": "",
        "cave_prevention_needed": True,
    },
    "アクネ菌": {
        "base": """Small but expressive bacteria character.
Positioned ON or BETWEEN sebum layers (NOT standing freely).
NOT floating in space, NOT standing upright.
Scale: macro skin-level realism — NOT microscopic fantasy, NOT a cave.
Small relative to the pore — embedded between sebum layers.""",
        "emotions": {
            "悪役・支配": """Eyes: sinister, gleaming with malice
Eyebrows: angled sharply down
Mouth: evil grin, cackling
Arms: rubbing together deviously""",
            "パニック": """Eyes: wide with fear
Eyebrows: raised
Mouth: screaming
Arms: flailing""",
            "撤退・諦め": """Eyes: narrowed, bitter
Eyebrows: furrowed
Mouth: grimacing
Arms: retreating""",
            "苦しみ": """Eyes: squinting
Mouth: gasping
Body shrinking""",
        },
        "composition": """[COMPOSITION]
Bacteria character small but expressive in frame
Sebum visible as environmental element
Vertical 9:16 framing

[CAMERA]
Macro skin-level view

[LIGHTING]
Dim, slightly ominous lighting""",
        "forbidden": """[CRITICAL]
NOT a cave or wide tunnel
NOT standing upright in open space
Bacteria must be ATTACHED to or EMBEDDED IN sebum surface
Macro skin realism only — no fantasy world
断面図禁止""",
        "cave_prevention_needed": True,
        "sebum_rule": """[SEBUM IN THIS SCENE]
Sebum: golden sticky food source, NOT a character
NO face on sebum, NO expression on sebum
Sebum is purely material/environmental element""",
    },
    "白ニキビ": {
        "base": """Semi-realistic whitehead pimple EMBEDDED UNDER SKIN.
NO body, NO legs, NO arms — fully embedded in skin.
Face subtly formed ON THE SURFACE of the bump.
Eyes: barely visible, slightly bulging shapes under thin skin
Eyebrows: formed by subtle tension in the skin surface
Mouth: small strained opening, partially covered by skin
Skin: stretched, swollen, slightly red around the bump.""",
        "emotions": {
            "苦しみ": """Eyes: strained, barely visible through skin
Mouth: compressed, suffocating
Skin surface taut and stressed""",
            "警告": """Eyes: intense through the skin surface
Mouth: strained warning expression""",
            "パニック": """Eyes: bulging slightly more under skin
Mouth: trying to open wider""",
        },
        "composition": """[COMPOSITION]
Whitehead bump centered in frame
Surrounding skin visible
Vertical 9:16 framing

[CAMERA]
Close macro view of skin surface

[LIGHTING]
Natural lighting showing skin texture
Slight redness around bump""",
        "forbidden": "",
        "cave_prevention_needed": True,
    },
    "赤ニキビ": {
        "base": """Inflamed red pimple, swollen bump on skin surface.
NO body, NO legs — fully embedded in skin.
Face subtly visible within redness, blended into skin texture.
Eyes: narrow intense slightly glowing through redness
Eyebrows: formed by inflamed skin folds
Mouth: subtle but sharp warning expression""",
        "emotions": {
            "警告": """Eyes: intense, glowing red
Eyebrows: deep furrow from inflammation
Mouth: sharp, threatening""",
            "苦しみ": """Eyes: strained with pain
Mouth: grimacing
Redness intensifying""",
            "悪役・支配": """Eyes: fierce, dominating
Mouth: aggressive expression
Inflammation radiating outward""",
        },
        "composition": """[COMPOSITION]
Red pimple bump centered in frame
Inflamed skin visible around it
Vertical 9:16 framing

[CAMERA]
Close macro view of skin surface

[LIGHTING]
Warm lighting emphasizing redness
Slight glow from inflammation""",
        "forbidden": "",
        "cave_prevention_needed": True,
    },
    "洗顔料": {
        "base": """Pixar-style facial cleanser SQUEEZE TUBE character.
(NOT a pump bottle — a squeeze tube like face wash)
Soft plastic squeeze tube, rounded edges, slightly matte texture.
Colored cap at bottom (red or blue accent).
Face placed on UPPER FRONT AREA of tube, centered and clearly visible.
Arms: simple flexible arms emerging from sides of tube.
Color: soft pastel tinted (light blue or mint green — NOT pure white).""",
        "emotions": {
            "指導・冷静": """Eyes: calm, confident, kind
Eyebrows: slightly raised, approachable
Mouth: gentle smile, reassuring
Arms: one arm gesturing calmly""",
            "パニック": """Eyes: wide, concerned
Eyebrows: raised high
Mouth: open, calling out
Arms: reaching forward""",
            "明るい・元気": """Eyes: bright, sparkling
Eyebrows: raised happily
Mouth: big smile
Arms: one raised enthusiastically""",
        },
        "composition": """[COMPOSITION]
Character fills center frame
Bathroom clearly visible as context
NOT on skin surface — in bathroom space

[CAMERA]
Slight low angle, heroic framing

[LIGHTING]
Soft warm natural bathroom lighting""",
        "forbidden": """[CRITICAL]
NOT a pump bottle — squeeze tube only
The character is the TUBE ITSELF, not the foam""",
        "cave_prevention_needed": False,
        "setting_override": """[SETTING]
Realistic bathroom environment.
Bathroom sink visible, mirror, faucet in background.
Soft warm natural lighting.
Character standing on sink counter.""",
    },
}

# ========================================
# 洞窟化防止ルール（共通）
# ========================================

CAVE_PREVENTION_RULES = """
[CRITICAL - CAVE PREVENTION - ALWAYS INCLUDE]
これは毛穴の内部ではなく「皮膚表面のマクロ表現」です
断面図禁止
カメラは毛穴の中に入らない
空洞は存在しない
NOT microscopic, NOT inside a cavity
No cross-section view, No wide open space
Scale: as if looking in a mirror at close distance
This is a MACRO view of real facial skin surface
Everything tightly packed with almost NO empty space
"""

# ========================================
# 三層構成テンプレート（洗顔中シーン専用）
# ========================================

THREE_LAYER_TEMPLATE = """Pixar-style 3D render, vertical 9:16 composition.

[COMPOSITION - THREE CRITICAL LAYERS]
TOP LAYER:
Soft white foam flowing across skin surface from above
Foam pressing downward — active washing motion
Creamy texture, slightly translucent

MIDDLE LAYER (MAIN FOCUS):
{character_description} — panicked expression
Being pushed/compressed by foam pressure from above

BOTTOM LAYER:
More {material} actively rising upward from deep inside
Continuous upward flow — supply not stopping
{material} pouring from below like being pumped up

[CRITICAL]
Three distinct layers must be clearly visible
Main character in center/middle layer is the focus
Top foam is threat, bottom supply is cause
"""

# ========================================
# 文字混入防止ルール（全プロンプト共通末尾）
# ========================================

CRITICAL_RULES = """
[CRITICAL RULES]
No text, no letters, no words, no captions, no subtitles, no watermarks, no labels
Pixar-style 3D render, cinematic quality
"""

# ========================================
# セリフ＝画像の状況一致ルール
# ========================================

SCENE_CONSISTENCY_RULES = {
    "洗顔やめて": "Foam/bubbles must be visible flowing from above",
    "詰まってる": "Densely packed, almost no empty space, maximum compression",
    "酸素が消えた": "Dark, compressed environment with no air",
    "居場所がない": "Sebum thin/scarce, environment cleaned out",
    "炎症": "Red swelling, heat-like visual effect",
    "洗面台": "Realistic bathroom sink background",
}

# ========================================
# 汎用オブジェクトキャラテンプレート
# ========================================

GENERIC_OBJECT_TEMPLATE = """Pixar-style 3D render of anthropomorphic {object_name}.
The {object_name} itself IS the character — it has a face and personality.
{texture_description}

[FACE]
Eyes: {eye_expression}
Eyebrows: {eyebrow_expression}
Mouth: {mouth_expression}
Arms: {arm_pose}

[COMPOSITION]
Character centered in vertical 9:16 frame
Face occupies ~60% of screen for mobile readability
Space at top for text overlay

[SETTING]
{setting_description}
"""


def _match_emotion(character_emotions: dict, inferred_emotion: str) -> str:
    """推定感情にマッチするemotion設定を返す"""
    # 完全一致
    if inferred_emotion in character_emotions:
        return character_emotions[inferred_emotion]

    # 部分一致
    for key, value in character_emotions.items():
        if key in inferred_emotion or inferred_emotion in key:
            return value

    # デフォルト: 最初のemotion
    return next(iter(character_emotions.values()))


def _check_washing_scene(lines: list[str]) -> bool:
    """洗顔シーンかどうか判定"""
    combined = "".join(lines)
    washing_keywords = ["洗顔", "泡", "洗い", "洗って", "やめて"]
    return any(kw in combined for kw in washing_keywords)


def _get_consistency_additions(lines: list[str]) -> str:
    """セリフに対応する状況一致ルールを追加"""
    combined = "".join(lines)
    additions = []
    for keyword, rule in SCENE_CONSISTENCY_RULES.items():
        if keyword in combined:
            additions.append(rule)
    if additions:
        return "\n[SCENE CONSISTENCY]\n" + "\n".join(additions)
    return ""


def load_learned_rules(character_name: str, feedback_log_path: str = None) -> str:
    """feedback_log.jsonから学習ルールを読み込みプロンプトに反映"""
    if feedback_log_path is None:
        feedback_log_path = os.path.join(
            os.path.dirname(__file__), "feedback_log.json"
        )

    if not os.path.exists(feedback_log_path):
        return ""

    with open(feedback_log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    additions = []

    # キャラクタープロファイルから学習
    profile = log.get("character_profiles", {}).get(character_name, {})
    for pattern in profile.get("successful_prompt_patterns", []):
        additions.append(pattern)
    for pattern in profile.get("failed_prompt_patterns", []):
        additions.append(f"DO NOT: {pattern}")

    # グローバルルール
    for rule in log.get("global_rules_learned", []):
        if character_name in rule:
            additions.append(rule)

    if additions:
        return "\n[LEARNED RULES]\n" + "\n".join(additions)
    return ""


def generate_prompt(scene: dict, feedback_log_path: str = None) -> str:
    """
    シーン情報からPixar風3D画像生成プロンプトを生成

    Args:
        scene: doc_reader.pyのparse_script()が返すシーン辞書
        feedback_log_path: feedback_log.jsonのパス（省略時はデフォルト）

    Returns:
        画像生成用プロンプト文字列
    """
    character = scene["character"]
    emotion = scene["inferred_emotion"]
    lines = scene["lines"]

    # キャラクターデザインを取得
    design = CHARACTER_DESIGNS.get(character)

    if design:
        return _generate_known_character_prompt(
            character, design, emotion, lines, feedback_log_path
        )
    else:
        return _generate_generic_prompt(character, emotion, lines, feedback_log_path)


def _generate_known_character_prompt(
    character: str,
    design: dict,
    emotion: str,
    lines: list[str],
    feedback_log_path: str = None,
) -> str:
    """既知キャラクターのプロンプト生成"""
    # 洗顔シーン判定
    is_washing = _check_washing_scene(lines)

    if is_washing and character in ("皮脂", "毛穴"):
        # 三層構成テンプレート使用
        material = "golden sebum" if character == "皮脂" else "sebum and debris"
        prompt = THREE_LAYER_TEMPLATE.format(
            character_description=design["base"].split("\n")[0],
            material=material,
        )
    else:
        # 通常テンプレート
        emotion_desc = _match_emotion(design.get("emotions", {}), emotion)
        prompt = f"Pixar-style 3D render, vertical 9:16 composition, of {design['base'].split(chr(10))[0]}\n\n"
        prompt += f"[CHARACTER DESIGN]\n{design['base']}\n\n"
        prompt += f"[FACE EXPRESSION]\n{emotion_desc}\n\n"

        # 設定オーバーライド
        if "setting_override" in design:
            prompt += f"{design['setting_override']}\n\n"

        prompt += f"{design['composition']}\n"

    # 洞窟化防止
    if design.get("cave_prevention_needed"):
        prompt += f"\n{CAVE_PREVENTION_RULES}\n"

    # 皮脂ルール（アクネ菌シーン用）
    if "sebum_rule" in design:
        prompt += f"\n{design['sebum_rule']}\n"

    # 禁止事項
    if design.get("forbidden"):
        prompt += f"\n{design['forbidden']}\n"

    # セリフ状況一致
    prompt += _get_consistency_additions(lines)

    # 学習ルール
    prompt += load_learned_rules(character, feedback_log_path)

    # 文字混入防止（必須末尾）
    prompt += f"\n{CRITICAL_RULES}"

    return prompt.strip()


def _generate_generic_prompt(
    character: str,
    emotion: str,
    lines: list[str],
    feedback_log_path: str = None,
) -> str:
    """未知のキャラクター用汎用プロンプト生成"""
    # 感情からデフォルトの表情を推定
    emotion_expressions = {
        "パニック": {
            "eye": "wide and panicked",
            "eyebrow": "raised high in alarm",
            "mouth": "open, shouting",
            "arm": "waving frantically",
        },
        "悪役・支配": {
            "eye": "sinister, gleaming",
            "eyebrow": "angled sharply down",
            "mouth": "evil grin",
            "arm": "spread wide confidently",
        },
        "苦しみ": {
            "eye": "squinting in pain",
            "eyebrow": "pushed together",
            "mouth": "compressed, gasping",
            "arm": "clutching body",
        },
        "指導・冷静": {
            "eye": "calm, confident",
            "eyebrow": "slightly raised",
            "mouth": "gentle smile",
            "arm": "gesturing calmly",
        },
    }

    expr = emotion_expressions.get(
        emotion,
        {
            "eye": "expressive, matching emotion",
            "eyebrow": "natural",
            "mouth": "matching emotion",
            "arm": "natural pose",
        },
    )

    prompt = GENERIC_OBJECT_TEMPLATE.format(
        object_name=character,
        texture_description=f"Realistic texture and color matching real {character}",
        eye_expression=expr["eye"],
        eyebrow_expression=expr["eyebrow"],
        mouth_expression=expr["mouth"],
        arm_pose=expr["arm"],
        setting_description=f"Realistic environment matching {character}'s natural context",
    )

    prompt += _get_consistency_additions(lines)
    prompt += load_learned_rules(character, feedback_log_path)
    prompt += f"\n{CRITICAL_RULES}"

    return prompt.strip()


def apply_retry_fix(original_prompt: str, retry_suggestion: str, ng_reason: str) -> str:
    """
    NG評価に基づいてプロンプトを修正

    Args:
        original_prompt: 元のプロンプト
        retry_suggestion: 評価システムからの修正提案
        ng_reason: NG理由

    Returns:
        修正されたプロンプト
    """
    fix_section = f"""
[RETRY FIX - ADDRESSING PREVIOUS FAILURE]
Previous issue: {ng_reason}
Fix applied: {retry_suggestion}
IMPORTANT: This is a retry — pay extra attention to the above fix.
"""
    # CRITICAL RULESの直前に挿入
    if "[CRITICAL RULES]" in original_prompt:
        return original_prompt.replace("[CRITICAL RULES]", fix_section + "\n[CRITICAL RULES]")
    return original_prompt + "\n" + fix_section
