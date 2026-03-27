"""TikTok スキンケア企画メーカー - CSV参考台本から企画を自動生成する."""

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


# ===== 肌悩みトピック辞書 =====
SKIN_TOPICS = {
    "ニキビ": ["ニキビ", "にきび", "吹き出物", "ブツブツ", "ぶつぶつ", "アクネ"],
    "毛穴": ["毛穴", "角栓", "黒ずみ", "いちご鼻", "開き毛穴", "たるみ毛穴", "詰まり毛穴"],
    "シミ・くすみ": ["シミ", "くすみ", "色素沈着", "そばかす", "肝斑", "トーンアップ", "透明感"],
    "乾燥・保湿": ["乾燥", "保湿", "カサカサ", "つっぱり", "インナードライ", "バリア機能"],
    "シワ・たるみ": ["シワ", "しわ", "たるみ", "ほうれい線", "エイジング", "ハリ", "弾力"],
    "赤み・敏感肌": ["赤み", "敏感肌", "肌荒れ", "かゆみ", "ヒリヒリ", "鎮静", "CICA", "シカ"],
    "テカリ・皮脂": ["テカリ", "皮脂", "脂性肌", "オイリー", "べたつき", "崩れ"],
    "美白・トーンアップ": ["美白", "ブライトニング", "トーンアップ", "ビタミンC", "アルブチン"],
    "スキンケア全般": ["スキンケア", "ルーティン", "朝ケア", "夜ケア", "洗顔", "クレンジング"],
    "成分・解説": ["成分", "レチノール", "ナイアシンアミド", "ヒアルロン酸", "セラミド", "BHA", "AHA"],
}

# ===== フックタイプ分類 =====
HOOK_TYPES = {
    "問題提起型": ["なのに", "してるのに", "なぜ", "原因は", "やめて", "ダメ", "間違い", "逆効果"],
    "驚き・衝撃型": ["衝撃", "ヤバい", "やばい", "マジで", "まじで", "実は", "知らないと"],
    "共感型": ["あるある", "わかる", "同じ悩み", "私も", "みんな", "あなたも"],
    "権威型": ["皮膚科", "医師", "プロ", "専門", "美容部員", "現役", "歴"],
    "数字型": [r"\d+選", r"\d+つ", r"\d+%", r"\d+万", r"\d+日", r"\d+ヶ月"],
    "好奇心型": ["秘密", "裏技", "知ってた", "意外", "まさか", "本当の"],
    "ネガティブ型": ["損", "危険", "注意", "NG", "やってはいけない", "絶対"],
    "疑問型": ["知ってる", "なんで", "どうして", "どれが", "何が"],
}


@dataclass
class ReferenceScript:
    """参考台本データ."""
    url: str = ""
    transcript: str = ""
    views: int = 0
    date: str = ""
    title: str = ""
    duration: int = 0
    # 解析結果
    hook_text: str = ""          # 冒頭～30文字
    hook_type: str = ""          # フックの分類
    topics: list = field(default_factory=list)  # 該当する肌悩みトピック
    is_recent: bool = False      # 直近3ヶ月以内か
    full_structure: dict = field(default_factory=dict)  # 台本構造


@dataclass
class ScriptPlan:
    """生成された企画台本."""
    hook_text: str = ""          # 冒頭訴求テキスト
    hook_source: dict = field(default_factory=dict)  # フック元ネタ情報
    topic: str = ""              # メインのスキンケアトピック
    content_summary: str = ""    # 中身の要約
    content_sources: list = field(default_factory=list)  # コンテンツ元ネタ
    full_script: str = ""        # 台本全体
    structure: dict = field(default_factory=dict)  # 構成


def parse_csv(file_content: str, encoding: str = "utf-8") -> list[ReferenceScript]:
    """CSVファイルを解析してReferenceScriptのリストを返す."""
    scripts = []

    # BOM除去
    if file_content.startswith("\ufeff"):
        file_content = file_content[1:]

    reader = csv.DictReader(io.StringIO(file_content))
    if not reader.fieldnames:
        return scripts

    # カラム名の柔軟なマッピング
    col_map = _detect_columns(reader.fieldnames)

    for row in reader:
        script = ReferenceScript()

        # URL
        if col_map.get("url"):
            script.url = row.get(col_map["url"], "").strip()

        # 文字起こし/台本
        if col_map.get("transcript"):
            script.transcript = row.get(col_map["transcript"], "").strip()

        # 再生数
        if col_map.get("views"):
            raw = row.get(col_map["views"], "0").strip()
            script.views = _parse_number(raw)

        # 日付
        if col_map.get("date"):
            script.date = row.get(col_map["date"], "").strip()

        # タイトル
        if col_map.get("title"):
            script.title = row.get(col_map["title"], "").strip()

        # 動画長
        if col_map.get("duration"):
            raw = row.get(col_map["duration"], "0").strip()
            script.duration = _parse_number(raw)

        if script.transcript or script.title:
            scripts.append(script)

    return scripts


def _detect_columns(fieldnames: list[str]) -> dict:
    """CSVのカラム名を柔軟にマッピングする."""
    col_map = {}
    patterns = {
        "url": ["url", "URL", "リンク", "link", "動画URL", "video_url", "動画リンク"],
        "transcript": ["transcript", "文字起こし", "台本", "テキスト", "text", "script",
                       "内容", "content", "字幕", "セリフ", "transcription"],
        "views": ["views", "再生数", "view_count", "再生回数", "play_count", "視聴数",
                  "再生", "playCount"],
        "date": ["date", "日付", "投稿日", "upload_date", "投稿日時", "createTime",
                 "created", "公開日"],
        "title": ["title", "タイトル", "説明", "description", "desc", "概要"],
        "duration": ["duration", "動画長", "秒数", "長さ", "時間"],
    }

    for key, candidates in patterns.items():
        for col in fieldnames:
            col_lower = col.strip().lower()
            for candidate in candidates:
                if candidate.lower() == col_lower or candidate.lower() in col_lower:
                    col_map[key] = col.strip()
                    break
            if key in col_map:
                break

    return col_map


def _parse_number(raw: str) -> int:
    """文字列から数値を抽出する（カンマ・万・億対応）."""
    if not raw:
        return 0
    raw = raw.replace(",", "").replace("，", "").strip()

    # 万・億の処理
    m = re.match(r"([\d.]+)\s*億", raw)
    if m:
        return int(float(m.group(1)) * 100_000_000)
    m = re.match(r"([\d.]+)\s*万", raw)
    if m:
        return int(float(m.group(1)) * 10_000)

    # 数字のみ抽出
    m = re.match(r"[\d.]+", raw)
    if m:
        return int(float(m.group(0)))
    return 0


def _parse_date(date_str: str) -> Optional[datetime]:
    """日付文字列をdatetimeに変換する."""
    if not date_str:
        return None

    # Unix timestamp
    if date_str.isdigit() and len(date_str) >= 10:
        try:
            return datetime.fromtimestamp(int(date_str))
        except (ValueError, OSError):
            pass

    # 各種日付フォーマット
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
        "%Y%m%d", "%m/%d/%Y", "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip()[:19], fmt)
        except ValueError:
            continue
    return None


def analyze_scripts(scripts: list[ReferenceScript], min_views: int = 500_000,
                    recent_months: int = 3) -> dict:
    """参考台本を分析し、フックとコンテンツに分類する."""
    now = datetime.now()
    cutoff_date = now - timedelta(days=recent_months * 30)

    for script in scripts:
        text = script.transcript or script.title or ""

        # 冒頭フック抽出（最初の30文字）
        script.hook_text = text[:30].strip()

        # フックタイプ分類
        script.hook_type = _classify_hook(script.hook_text)

        # 肌悩みトピック抽出
        script.topics = _detect_topics(text)

        # 日付判定
        parsed_date = _parse_date(script.date)
        if parsed_date:
            script.is_recent = parsed_date >= cutoff_date
        else:
            script.is_recent = False

        # 台本構造分析
        script.full_structure = _analyze_structure(text)

    # フィルタリング
    viral_scripts = [s for s in scripts if s.views >= min_views]

    # フック候補: 直近3ヶ月 + 50万再生以上
    hook_candidates = [
        s for s in viral_scripts
        if s.is_recent and s.hook_text
    ]
    hook_candidates.sort(key=lambda s: s.views, reverse=True)

    # コンテンツ候補: 50万再生以上（期間不問）、肌悩みトピックあり
    content_candidates = [
        s for s in viral_scripts
        if s.topics and s.transcript and len(s.transcript) > 50
    ]
    content_candidates.sort(key=lambda s: s.views, reverse=True)

    # トピック別に集約
    topics_summary = {}
    for s in content_candidates:
        for topic in s.topics:
            if topic not in topics_summary:
                topics_summary[topic] = []
            topics_summary[topic].append(s)

    # フックタイプ集計
    hook_type_counts = Counter(s.hook_type for s in hook_candidates if s.hook_type)

    return {
        "total_scripts": len(scripts),
        "viral_count": len(viral_scripts),
        "hook_candidates": hook_candidates,
        "content_candidates": content_candidates,
        "topics_summary": topics_summary,
        "hook_type_counts": dict(hook_type_counts.most_common()),
    }


def _classify_hook(text: str) -> str:
    """フックテキストをタイプ分類する."""
    if not text:
        return "その他"
    for hook_type, patterns in HOOK_TYPES.items():
        for p in patterns:
            if re.search(p, text):
                return hook_type
    return "ストレート型"


def _detect_topics(text: str) -> list[str]:
    """テキストから肌悩みトピックを検出する."""
    found = []
    for topic, keywords in SKIN_TOPICS.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                found.append(topic)
                break
    return found


def _analyze_structure(text: str) -> dict:
    """台本の構造を分析する."""
    if not text or len(text) < 10:
        return {}

    total = len(text)
    # 3分割: 導入・本題・締め
    third = max(total // 3, 1)
    intro = text[:third]
    body = text[third:third * 2]
    outro = text[third * 2:]

    return {
        "intro": intro[:100],
        "body": body[:150],
        "outro": outro[:100],
        "total_length": total,
    }


def generate_plans(analysis: dict, max_plans: int = 6) -> list[ScriptPlan]:
    """フックとコンテンツを組み合わせて企画台本を生成する."""
    hook_candidates = analysis.get("hook_candidates", [])
    content_candidates = analysis.get("content_candidates", [])
    topics_summary = analysis.get("topics_summary", {})

    if not hook_candidates or not content_candidates:
        return []

    plans = []
    used_hooks = set()
    used_content_ids = set()

    # 各フック候補に対して、マッチするコンテンツを探す
    for hook_script in hook_candidates:
        if len(plans) >= max_plans:
            break
        if hook_script.hook_text in used_hooks:
            continue

        # フックのトピックに関連するコンテンツを探す
        best_content = _find_matching_content(
            hook_script, content_candidates, used_content_ids
        )

        if not best_content:
            # トピック不一致でも、汎用的なフックなら使える
            for c in content_candidates:
                content_id = c.url or c.transcript[:20]
                if content_id not in used_content_ids:
                    best_content = c
                    break

        if not best_content:
            continue

        plan = _build_plan(hook_script, best_content)
        plans.append(plan)
        used_hooks.add(hook_script.hook_text)
        content_id = best_content.url or best_content.transcript[:20]
        used_content_ids.add(content_id)

    # まだ足りない場合：トピック別にクロス生成
    if len(plans) < max_plans:
        for topic, scripts in topics_summary.items():
            if len(plans) >= max_plans:
                break
            for hook_script in hook_candidates:
                if len(plans) >= max_plans:
                    break
                if hook_script.hook_text in used_hooks:
                    continue
                for content_script in scripts:
                    content_id = content_script.url or content_script.transcript[:20]
                    if content_id in used_content_ids:
                        continue
                    plan = _build_plan(hook_script, content_script)
                    plans.append(plan)
                    used_hooks.add(hook_script.hook_text)
                    used_content_ids.add(content_id)
                    break

    return plans


def _find_matching_content(hook_script: ReferenceScript,
                           content_candidates: list[ReferenceScript],
                           used_ids: set) -> Optional[ReferenceScript]:
    """フックに関連するコンテンツを探す."""
    hook_topics = set(hook_script.topics)

    # 1. 同じトピックのコンテンツを優先
    if hook_topics:
        for c in content_candidates:
            content_id = c.url or c.transcript[:20]
            if content_id in used_ids:
                continue
            if set(c.topics) & hook_topics:
                return c

    # 2. フックと異なる動画で、トピックありのコンテンツ
    for c in content_candidates:
        content_id = c.url or c.transcript[:20]
        hook_id = hook_script.url or hook_script.transcript[:20]
        if content_id in used_ids or content_id == hook_id:
            continue
        if c.topics:
            return c

    return None


def _build_plan(hook_script: ReferenceScript,
                content_script: ReferenceScript) -> ScriptPlan:
    """フックとコンテンツから企画台本を組み立てる."""
    plan = ScriptPlan()

    # フック情報
    plan.hook_text = hook_script.hook_text
    plan.hook_source = {
        "url": hook_script.url,
        "views": hook_script.views,
        "date": hook_script.date,
        "hook_type": hook_script.hook_type,
        "full_hook": hook_script.transcript[:80] if hook_script.transcript else "",
    }

    # トピック
    plan.topic = content_script.topics[0] if content_script.topics else "スキンケア全般"

    # コンテンツ要約
    content_text = content_script.transcript or content_script.title or ""
    plan.content_summary = _summarize_content(content_text)

    # コンテンツ元ネタ
    plan.content_sources = [{
        "url": content_script.url,
        "views": content_script.views,
        "date": content_script.date,
        "title": content_script.title,
        "topics": content_script.topics,
    }]

    # 台本構造
    plan.structure = {
        "hook": plan.hook_text,
        "bridge": _generate_bridge(plan.hook_text, plan.topic),
        "body": plan.content_summary,
        "cta": _generate_cta(plan.topic),
    }

    # 全体台本生成
    plan.full_script = _compose_script(plan)

    return plan


def _summarize_content(text: str) -> str:
    """コンテンツテキストからハウツー部分を要約する."""
    if not text:
        return ""

    # 冒頭をスキップして本題部分を抽出
    total = len(text)
    if total <= 100:
        return text

    # 導入（1/4）をスキップし、本題（2/4）を取得
    quarter = total // 4
    body = text[quarter:quarter * 3]
    return body[:300]


def _generate_bridge(hook_text: str, topic: str) -> str:
    """フックとコンテンツをつなぐブリッジ文を生成する."""
    bridges = {
        "ニキビ": "そのニキビ、実は原因が違うかもしれません。",
        "毛穴": "毛穴が目立つのには理由があるんです。",
        "シミ・くすみ": "くすみの原因を知れば対策が変わります。",
        "乾燥・保湿": "保湿の仕方、間違っていませんか？",
        "シワ・たるみ": "正しいケアで変わります。",
        "赤み・敏感肌": "敏感肌でもできるケアがあります。",
        "テカリ・皮脂": "テカリの本当の原因、知っていますか？",
        "美白・トーンアップ": "透明感を出すにはコツがあります。",
        "スキンケア全般": "正しい順番とやり方を解説します。",
        "成分・解説": "成分を知れば選び方が変わります。",
    }
    return bridges.get(topic, "今日はそのポイントを詳しく解説します。")


def _generate_cta(topic: str) -> str:
    """締めのCTA文を生成する."""
    ctas = [
        "他にも知りたい方はフォローしてね！",
        "保存して見返してね！",
        "もっと詳しく知りたい人はコメントで教えて！",
        "参考になったらいいねしてね！",
    ]
    # トピックに応じてCTAを選択
    idx = hash(topic) % len(ctas)
    return ctas[idx]


def _compose_script(plan: ScriptPlan) -> str:
    """企画台本の全文を組み立てる."""
    parts = []

    # 冒頭（0-5秒）
    parts.append(f"【冒頭 0-5秒】\n{plan.hook_text}")

    # ブリッジ（5-10秒）
    bridge = plan.structure.get("bridge", "")
    if bridge:
        parts.append(f"\n【つなぎ 5-10秒】\n{bridge}")

    # 本題（10秒-）
    body = plan.content_summary
    if body:
        parts.append(f"\n【本題 10秒-】\n{body}")

    # 締め
    cta = plan.structure.get("cta", "")
    if cta:
        parts.append(f"\n【締め】\n{cta}")

    return "\n".join(parts)


def format_plans_for_display(plans: list[ScriptPlan]) -> list[dict]:
    """企画台本をフロント表示用に整形する."""
    result = []
    for i, plan in enumerate(plans, 1):
        result.append({
            "plan_number": i,
            "hook_text": plan.hook_text,
            "hook_type": plan.hook_source.get("hook_type", ""),
            "hook_source": {
                "url": plan.hook_source.get("url", ""),
                "views": plan.hook_source.get("views", 0),
                "date": plan.hook_source.get("date", ""),
                "full_hook": plan.hook_source.get("full_hook", ""),
            },
            "topic": plan.topic,
            "content_summary": plan.content_summary[:200],
            "content_sources": plan.content_sources,
            "structure": plan.structure,
            "full_script": plan.full_script,
        })
    return result


def get_analysis_summary(analysis: dict) -> dict:
    """分析結果のサマリーを返す."""
    hook_candidates = analysis.get("hook_candidates", [])
    content_candidates = analysis.get("content_candidates", [])
    topics_summary = analysis.get("topics_summary", {})

    # トピック別件数
    topic_counts = {t: len(scripts) for t, scripts in topics_summary.items()}

    # 上位フック
    top_hooks = []
    for s in hook_candidates[:10]:
        top_hooks.append({
            "text": s.hook_text,
            "type": s.hook_type,
            "views": s.views,
            "url": s.url,
            "date": s.date,
        })

    return {
        "total_scripts": analysis.get("total_scripts", 0),
        "viral_count": analysis.get("viral_count", 0),
        "hook_count": len(hook_candidates),
        "content_count": len(content_candidates),
        "topic_counts": topic_counts,
        "hook_type_counts": analysis.get("hook_type_counts", {}),
        "top_hooks": top_hooks,
    }
