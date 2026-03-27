"""美容コンテンツ企画ツール - Beauty Content Planner.

競合チャンネル分析 → トレンド発見 → 企画生成 → 台本生成 を一貫して行うツール。
"""

import json
import os
import traceback
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

CONFIG_PATH = Path(__file__).parent / ".beauty_config.json"
CHANNELS_PATH = Path(__file__).parent / ".beauty_channels.json"
TRENDS_PATH = Path(__file__).parent / ".beauty_trends.json"
PLANS_PATH = Path(__file__).parent / ".beauty_plans.json"


def load_json(path, default=None):
    if default is None:
        default = {}
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_anthropic_client():
    """Anthropic クライアントを取得."""
    config = load_json(CONFIG_PATH)
    api_key = config.get("anthropic_api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API キーが設定されていません")
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


# --- 参考データ読み込み ---
from beauty_planner.reference_data import (
    KARAKUCHI_REFERENCE,
    ZUNDAMON_STYLE,
    SUNO_AI_STYLE,
    BEAUTY_CATEGORIES,
)


@app.route("/")
def index():
    return send_from_directory("templates", "beauty.html")


# === API キー管理 ===
@app.route("/api/config", methods=["GET"])
def get_config():
    config = load_json(CONFIG_PATH)
    key = config.get("anthropic_api_key", "")
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else ""
    return jsonify({"has_key": bool(key), "masked_key": masked})


@app.route("/api/config", methods=["POST"])
def save_config():
    data = request.json
    config = load_json(CONFIG_PATH)
    config["anthropic_api_key"] = data.get("anthropic_api_key", "")
    save_json(CONFIG_PATH, config)
    return jsonify({"ok": True})


# === チャンネル管理 ===
@app.route("/api/channels", methods=["GET"])
def get_channels():
    channels = load_json(CHANNELS_PATH, [])
    return jsonify(channels)


@app.route("/api/channels", methods=["POST"])
def save_channels():
    channels = request.json
    save_json(CHANNELS_PATH, channels)
    return jsonify({"ok": True})


# === トレンド分析 ===
@app.route("/api/analyze-trends", methods=["POST"])
def analyze_trends():
    """Claude web_search でトレンド分析を実行."""
    try:
        client = get_anthropic_client()
        data = request.json
        channels = data.get("channels", [])
        period = data.get("period", "1week")
        min_views = data.get("min_views", 0)
        categories = data.get("categories", [])

        period_text = {
            "1week": "直近1週間",
            "3months": "直近3ヶ月",
            "6months": "直近6ヶ月",
            "1year": "直近1年",
            "over1year": "1年以上前",
        }.get(period, "直近1ヶ月")

        views_text = ""
        if min_views > 0:
            views_text = f"\n- 最低再生数フィルター: {min_views:,}回以上"

        channels_text = ""
        if channels:
            ch_list = "\n".join([f"  - {ch.get('name', '')} ({ch.get('platform', 'TikTok')}): {ch.get('url', '')}" for ch in channels])
            channels_text = f"\n\n【分析対象チャンネル】\n{ch_list}"

        categories_text = ""
        if categories:
            categories_text = f"\n- 注目カテゴリ: {', '.join(categories)}"

        prompt = f"""あなたは美容系TikTok/Instagramのトレンド分析の専門家です。
以下の条件でweb検索を行い、最新の美容トレンドを分析してください。

【分析条件】
- 期間: {period_text}
- プラットフォーム: TikTok, Instagram{views_text}{categories_text}{channels_text}

【分析してほしい内容】
1. **トレンド商品TOP10**: 今バズっている美容商品（商品名、ブランド、カテゴリ、推定バズ度）
2. **ホットキーワード**: 検索ボリュームの大きいキーワード（美容関連）
3. **共通トピック**: 複数のアカウントが取り上げているテーマ
4. **注目アカウント情報**: 各アカウントの最近の投稿傾向、月間投稿頻度、エンゲージメント傾向
5. **季節トレンド**: 今の時期に特に需要が高いカテゴリ
6. **視聴者インサイト**: コメント欄で多い悩み・要望

必ず以下のJSON形式で回答してください（JSONのみ、説明文なし）:
```json
{{
  "trending_products": [
    {{
      "rank": 1,
      "product_name": "商品名",
      "brand": "ブランド名",
      "category": "カテゴリ",
      "buzz_score": 95,
      "estimated_views": "500万+",
      "why_trending": "バズっている理由",
      "platforms": ["TikTok", "Instagram"],
      "related_hashtags": ["#ハッシュタグ"]
    }}
  ],
  "hot_keywords": [
    {{
      "keyword": "キーワード",
      "volume": "大/中/小",
      "trend_direction": "上昇/安定/下降",
      "related_category": "関連カテゴリ"
    }}
  ],
  "common_topics": [
    {{
      "topic": "トピック名",
      "description": "説明",
      "mentioned_by": ["アカウント名"],
      "content_angle": "どういう切り口で取り上げられているか"
    }}
  ],
  "account_insights": [
    {{
      "account_name": "アカウント名",
      "platform": "TikTok/Instagram",
      "recent_focus": "最近の投稿テーマ",
      "posting_frequency": "月間○本程度",
      "engagement_trend": "上昇/安定/下降",
      "top_recent_video": "最近一番伸びた動画のテーマ",
      "estimated_monthly_views": "推定月間再生数"
    }}
  ],
  "seasonal_trends": [
    {{
      "category": "カテゴリ",
      "demand_level": "高/中/低",
      "reason": "理由",
      "peak_timing": "ピーク時期"
    }}
  ],
  "viewer_pain_points": [
    {{
      "pain_point": "悩み",
      "frequency": "頻出度(高/中/低)",
      "target_skin_type": "対象肌タイプ",
      "content_opportunity": "コンテンツ化のチャンス"
    }}
  ],
  "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
  "period": "{period_text}"
}}
```"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}],
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        # JSONを抽出
        json_start = result_text.find("{")
        json_end = result_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            trend_data = json.loads(result_text[json_start:json_end])
        else:
            trend_data = {"raw_response": result_text, "error": "JSON解析失敗"}

        # 保存
        all_trends = load_json(TRENDS_PATH, [])
        trend_data["_timestamp"] = datetime.now().isoformat()
        all_trends.insert(0, trend_data)
        if len(all_trends) > 30:
            all_trends = all_trends[:30]
        save_json(TRENDS_PATH, all_trends)

        return jsonify({"ok": True, "data": trend_data})

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# === 企画生成 ===
@app.route("/api/generate-plans", methods=["POST"])
def generate_plans():
    """トレンドデータから企画案を生成."""
    try:
        client = get_anthropic_client()
        data = request.json
        trend_data = data.get("trend_data", {})
        num_plans = data.get("num_plans", 5)
        custom_request = data.get("custom_request", "")

        custom_text = ""
        if custom_request:
            custom_text = f"\n\n【追加リクエスト】\n{custom_request}"

        prompt = f"""あなたは美容系ショート動画の企画プロデューサーです。
以下のトレンドデータを元に、{num_plans}本の企画案を生成してください。

【トレンドデータ】
{json.dumps(trend_data, ensure_ascii=False, indent=2)[:6000]}

【参考: 伸びている企画のパターン】
- 「プチプラで1番良い○○はこれだぜっ☆」→ 再生数400万+
- 「市販で1番良い○○」→ 再生数400万+
- 「{'{season}'}でも崩れない○○」→ 季節需要で300万+
- 「圧倒的リピナシの○○」→ 逆張りで300万+
- 商品4〜5個紹介、最初は辛口→最後にイチオシ
- 冒頭10秒でテーマへの共感を作る
- プチプラ（〜1500円）が視聴者に最も刺さる

【視聴者の心理】
- 失敗したくない、お金も失いたくない、損をしたくない
- なるべく少ないお金で綺麗になりたい
- 自分も「レビュアー」になりたがっている
- 定番＝正解という空気への不信感{custom_text}

以下のJSON形式で回答（JSONのみ）:
```json
{{
  "plans": [
    {{
      "id": 1,
      "title": "企画タイトル（冒頭訴求テキスト）",
      "category": "美容カテゴリ",
      "target_products": ["紹介予定の商品名"],
      "hook": "冒頭の引き（10秒以内）",
      "structure": "構成の概要",
      "why_this_works": "この企画が伸びる理由",
      "estimated_engagement": "高/中/低",
      "recommended_script_type": "辛口レビュー/ずんだもん/Suno AI歌",
      "target_duration_sec": 35,
      "seasonal_relevance": "季節との関連",
      "keywords": ["関連キーワード"],
      "comment_bait": "コメントが盛り上がりそうなポイント"
    }}
  ]
}}
```"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        json_start = result_text.find("{")
        json_end = result_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            plans_data = json.loads(result_text[json_start:json_end])
        else:
            plans_data = {"raw_response": result_text}

        # 保存
        all_plans = load_json(PLANS_PATH, [])
        plans_data["_timestamp"] = datetime.now().isoformat()
        all_plans.insert(0, plans_data)
        if len(all_plans) > 50:
            all_plans = all_plans[:50]
        save_json(PLANS_PATH, all_plans)

        return jsonify({"ok": True, "data": plans_data})

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# === 台本生成 ===
@app.route("/api/generate-script", methods=["POST"])
def generate_script():
    """企画から台本を生成. 3タイプ対応."""
    try:
        client = get_anthropic_client()
        data = request.json
        plan = data.get("plan", {})
        script_type = data.get("script_type", "karakuchi")
        custom_tone = data.get("custom_tone", "")
        target_duration = data.get("target_duration", 35)

        # スタイル別のプロンプト構築
        if script_type == "karakuchi":
            style_prompt = _build_karakuchi_prompt(plan, target_duration, custom_tone)
        elif script_type == "zundamon":
            style_prompt = _build_zundamon_prompt(plan, target_duration, custom_tone)
        elif script_type == "suno":
            style_prompt = _build_suno_prompt(plan, target_duration, custom_tone)
        else:
            return jsonify({"ok": False, "error": f"不明な台本タイプ: {script_type}"}), 400

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": style_prompt}],
        )

        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        return jsonify({
            "ok": True,
            "script": result_text,
            "script_type": script_type,
            "plan_title": plan.get("title", ""),
        })

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


def _build_karakuchi_prompt(plan, target_duration, custom_tone):
    """辛口レビュー台本プロンプト."""
    ref = KARAKUCHI_REFERENCE
    example_scripts = "\n\n---\n\n".join([
        f"【参考台本: {s['title']}（{s['views']}万再生）】\n{s['script']}"
        for s in ref["scripts"][:3]
    ])

    return f"""あなたは美容系TikTokの辛口レビュー台本を書く専門ライターです。
以下の参考データとスタイルガイドに完全に従って台本を生成してください。

{ref['style_notes']}

【参考台本（この口調を完全に再現すること）】
{example_scripts}

【視聴者インサイト】
{ref['audience_insights']}

【今回の企画】
- タイトル: {plan.get('title', '')}
- カテゴリ: {plan.get('category', '')}
- 紹介商品: {json.dumps(plan.get('target_products', []), ensure_ascii=False)}
- 冒頭フック: {plan.get('hook', '')}
- 構成: {plan.get('structure', '')}
- 目標秒数: {target_duration}秒
- コメント誘発ポイント: {plan.get('comment_bait', '')}

{'【追加トーン指定】' + custom_tone if custom_tone else ''}

【生成ルール】
1. 参考台本の口調（「〜だぜっ☆」「カスぅ」「し〜↑」等）を完全再現
2. 冒頭10秒はテーマへの共感（AI歌 or ギャグ要素）
3. 否定商品3〜4 → イチオシ1の構成
4. 価格叫びを入れる
5. 「はい、お買い上げ〜^^」or「はい、お会計〜^^」で締める
6. {target_duration}秒で読める長さにする（1秒あたり約4〜5文字）
7. 「死ぬ」表現は使わない
8. ディスりすぎない（品を保つ）

台本のみを出力してください。"""


def _build_zundamon_prompt(plan, target_duration, custom_tone):
    """ずんだもん台本プロンプト."""
    ref = ZUNDAMON_STYLE
    return f"""あなたは「ずんだもん」というキャラクターの台本を書く専門ライターです。

{ref['style_notes']}

【今回の企画】
- タイトル: {plan.get('title', '')}
- カテゴリ: {plan.get('category', '')}
- 紹介商品: {json.dumps(plan.get('target_products', []), ensure_ascii=False)}
- 冒頭フック: {plan.get('hook', '')}
- 構成: {plan.get('structure', '')}
- 目標秒数: {target_duration}秒

{'【追加トーン指定】' + custom_tone if custom_tone else ''}

【生成ルール】
1. 語尾は必ず「〜なのだ」「〜のだ」
2. 一人称は「ボク」
3. 明るくテンション高めだが、レビューは正直に
4. 美容知識を分かりやすく解説
5. 否定も「うーん、これはちょっとダメなのだ…」のように柔らかく
6. 推し商品は「これは最高なのだ！！」と熱く
7. {target_duration}秒で読める長さ
8. 視聴者に語りかける親しみやすいトーン

台本のみを出力してください。"""


def _build_suno_prompt(plan, target_duration, custom_tone):
    """Suno AI歌詞プロンプト."""
    ref = SUNO_AI_STYLE
    return f"""あなたはSuno AIで美容系ショート動画のBGM歌詞を作る専門作詞家です。

{ref['style_notes']}

【今回の企画】
- タイトル: {plan.get('title', '')}
- カテゴリ: {plan.get('category', '')}
- 紹介商品: {json.dumps(plan.get('target_products', []), ensure_ascii=False)}
- 冒頭フック: {plan.get('hook', '')}
- 目標秒数: {target_duration}秒

{'【追加トーン指定】' + custom_tone if custom_tone else ''}

【生成ルール】
1. Suno AIのメタタグ形式で出力（[Intro], [Verse], [Chorus]等）
2. 冒頭に [Genre], [Tempo], [Mood], [Voice] を指定
3. 美容の悩みへの共感から入る
4. 商品名を自然に歌詞に織り込む
5. サビはキャッチーでリピートしやすいフレーズ
6. {target_duration}秒のショート動画向け構成
7. 日本語歌詞
8. 参考: 冒頭で有名曲の替え歌風にすると維持率が上がる

以下の形式で出力:
---
[メタタグ]
[Genre: ...]
[Tempo: ...]
[Mood: ...]
[Voice: ...]

[Intro]
...

[Verse 1]
...

[Chorus]
...
---

歌詞のみを出力してください。"""


# === 履歴 ===
@app.route("/api/trends-history", methods=["GET"])
def get_trends_history():
    trends = load_json(TRENDS_PATH, [])
    return jsonify(trends)


@app.route("/api/plans-history", methods=["GET"])
def get_plans_history():
    plans = load_json(PLANS_PATH, [])
    return jsonify(plans)


# === カテゴリ一覧 ===
@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(BEAUTY_CATEGORIES)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
