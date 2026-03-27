"""TikTok スキンケア企画メーカー - リサーチ結果＋参考台本で企画を自動生成する."""

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .researcher import TikTokVideo, search_tiktok_videos, get_video_transcript


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
    """CSV参考台本データ（スタイル参考用）."""
    url: str = ""
    transcript: str = ""
    views: int = 0
    date: str = ""
    title: str = ""
    duration: int = 0
    hook_text: str = ""
    topics: list = field(default_factory=list)
    structure: dict = field(default_factory=dict)


@dataclass
class AnalyzedVideo:
    """リサーチ結果の分析済み動画."""
    video: TikTokVideo = field(default_factory=TikTokVideo)
    hook_text: str = ""
    hook_type: str = ""
    topics: list = field(default_factory=list)
    structure: dict = field(default_factory=dict)


@dataclass
class ScriptPlan:
    """生成された企画台本."""
    hook_text: str = ""
    hook_source: dict = field(default_factory=dict)
    topic: str = ""
    content_summary: str = ""
    content_sources: list = field(default_factory=list)
    reference_style: dict = field(default_factory=dict)
    full_script: str = ""
    structure: dict = field(default_factory=dict)


# ===== CSV参考台本パース =====

def parse_csv(file_content: str) -> list[ReferenceScript]:
    """CSVファイルを解析してReferenceScriptのリストを返す."""
    scripts = []

    if file_content.startswith("\ufeff"):
        file_content = file_content[1:]

    reader = csv.DictReader(io.StringIO(file_content))
    if not reader.fieldnames:
        return scripts

    col_map = _detect_columns(reader.fieldnames)

    for row in reader:
        script = ReferenceScript()

        if col_map.get("url"):
            script.url = row.get(col_map["url"], "").strip()
        if col_map.get("transcript"):
            script.transcript = row.get(col_map["transcript"], "").strip()
        if col_map.get("views"):
            script.views = _parse_number(row.get(col_map["views"], "0"))
        if col_map.get("date"):
            script.date = row.get(col_map["date"], "").strip()
        if col_map.get("title"):
            script.title = row.get(col_map["title"], "").strip()
        if col_map.get("duration"):
            script.duration = _parse_number(row.get(col_map["duration"], "0"))

        if script.transcript or script.title:
            text = script.transcript or script.title
            script.hook_text = text[:30].strip()
            script.topics = _detect_topics(text)
            script.structure = _analyze_structure(text)
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
    if not raw:
        return 0
    raw = raw.replace(",", "").replace("，", "").strip()
    m = re.match(r"([\d.]+)\s*億", raw)
    if m:
        return int(float(m.group(1)) * 100_000_000)
    m = re.match(r"([\d.]+)\s*万", raw)
    if m:
        return int(float(m.group(1)) * 10_000)
    m = re.match(r"[\d.]+", raw)
    if m:
        return int(float(m.group(0)))
    return 0


# ===== リサーチ動画の分析 =====

def analyze_researched_videos(videos: list[TikTokVideo],
                              hook_period_months: int = 3) -> dict:
    """リサーチで取得した動画を分析する."""
    cutoff = datetime.now() - timedelta(days=hook_period_months * 30)
    analyzed = []

    for video in videos:
        text = video.transcript or video.description or video.title or ""
        av = AnalyzedVideo(video=video)

        # 冒頭フック（最初の30文字）
        av.hook_text = text[:30].strip()
        av.hook_type = _classify_hook(av.hook_text)

        # トピック検出
        av.topics = _detect_topics(text)

        # 構造分析
        av.structure = _analyze_structure(text)

        analyzed.append(av)

    # フック候補: 直近N ヶ月のみ
    hook_candidates = []
    content_candidates = []

    for av in analyzed:
        is_recent = False
        v = av.video
        if v.upload_timestamp:
            try:
                vdate = datetime.fromtimestamp(v.upload_timestamp)
                is_recent = vdate >= cutoff
            except (ValueError, OSError):
                pass
        elif v.upload_date:
            parsed = _parse_date_str(v.upload_date)
            if parsed:
                is_recent = parsed >= cutoff

        if is_recent and av.hook_text:
            hook_candidates.append(av)

        # コンテンツ候補: トピックがあれば期間不問
        if av.topics:
            content_candidates.append(av)

    hook_candidates.sort(key=lambda a: a.video.views, reverse=True)
    content_candidates.sort(key=lambda a: a.video.views, reverse=True)

    # トピック別集約
    topics_summary = {}
    for av in content_candidates:
        for topic in av.topics:
            if topic not in topics_summary:
                topics_summary[topic] = []
            topics_summary[topic].append(av)

    # フックタイプ集計
    hook_type_counts = Counter(a.hook_type for a in hook_candidates if a.hook_type)

    return {
        "total_videos": len(videos),
        "analyzed": analyzed,
        "hook_candidates": hook_candidates,
        "content_candidates": content_candidates,
        "topics_summary": topics_summary,
        "hook_type_counts": dict(hook_type_counts.most_common()),
    }


def _parse_date_str(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    if date_str.isdigit() and len(date_str) >= 10:
        try:
            return datetime.fromtimestamp(int(date_str))
        except (ValueError, OSError):
            pass
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(date_str[:19], fmt)
        except ValueError:
            continue
    return None


# ===== 企画台本生成 =====

def generate_plans(analysis: dict, reference_scripts: list[ReferenceScript] = None,
                   max_plans: int = 6) -> list[ScriptPlan]:
    """フック×コンテンツ×参考台本で企画台本を生成する."""
    hook_candidates = analysis.get("hook_candidates", [])
    content_candidates = analysis.get("content_candidates", [])
    topics_summary = analysis.get("topics_summary", {})

    if not hook_candidates and not content_candidates:
        return []

    # 参考台本のスタイルを抽出
    ref_style = _extract_reference_style(reference_scripts or [])

    plans = []
    used_hooks = set()
    used_content_ids = set()

    # 1. フック×マッチするコンテンツ
    for hook_av in hook_candidates:
        if len(plans) >= max_plans:
            break
        if hook_av.hook_text in used_hooks:
            continue

        best_content = _find_matching_content_av(
            hook_av, content_candidates, used_content_ids
        )
        if not best_content:
            for c in content_candidates:
                cid = c.video.video_id or c.video.url
                if cid not in used_content_ids:
                    best_content = c
                    break
        if not best_content:
            continue

        plan = _build_plan_from_research(hook_av, best_content, ref_style)
        plans.append(plan)
        used_hooks.add(hook_av.hook_text)
        cid = best_content.video.video_id or best_content.video.url
        used_content_ids.add(cid)

    # 2. クロス生成でパターンを増やす
    if len(plans) < max_plans:
        for topic, avs in topics_summary.items():
            if len(plans) >= max_plans:
                break
            for hook_av in hook_candidates:
                if len(plans) >= max_plans:
                    break
                if hook_av.hook_text in used_hooks:
                    continue
                for content_av in avs:
                    cid = content_av.video.video_id or content_av.video.url
                    if cid in used_content_ids:
                        continue
                    plan = _build_plan_from_research(hook_av, content_av, ref_style)
                    plans.append(plan)
                    used_hooks.add(hook_av.hook_text)
                    used_content_ids.add(cid)
                    break

    return plans


def _extract_reference_style(scripts: list[ReferenceScript]) -> dict:
    """参考台本群からスタイル情報を抽出する."""
    if not scripts:
        return {}

    # 平均的な構造を把握
    intro_samples = []
    body_samples = []
    outro_samples = []
    total_lengths = []

    for s in scripts:
        st = s.structure
        if st:
            if st.get("intro"):
                intro_samples.append(st["intro"])
            if st.get("body"):
                body_samples.append(st["body"])
            if st.get("outro"):
                outro_samples.append(st["outro"])
            if st.get("total_length"):
                total_lengths.append(st["total_length"])

    avg_length = int(sum(total_lengths) / len(total_lengths)) if total_lengths else 0

    return {
        "avg_length": avg_length,
        "intro_samples": intro_samples[:3],
        "body_samples": body_samples[:3],
        "outro_samples": outro_samples[:3],
        "script_count": len(scripts),
    }


def _find_matching_content_av(hook_av: AnalyzedVideo,
                              content_candidates: list[AnalyzedVideo],
                              used_ids: set) -> Optional[AnalyzedVideo]:
    """フックに関連するコンテンツを探す."""
    hook_topics = set(hook_av.topics)

    if hook_topics:
        for c in content_candidates:
            cid = c.video.video_id or c.video.url
            if cid in used_ids:
                continue
            if set(c.topics) & hook_topics:
                return c

    for c in content_candidates:
        cid = c.video.video_id or c.video.url
        hid = hook_av.video.video_id or hook_av.video.url
        if cid in used_ids or cid == hid:
            continue
        if c.topics:
            return c

    return None


def _build_plan_from_research(hook_av: AnalyzedVideo,
                              content_av: AnalyzedVideo,
                              ref_style: dict) -> ScriptPlan:
    """リサーチ動画からの企画台本組み立て."""
    plan = ScriptPlan()
    hv = hook_av.video
    cv = content_av.video

    # フック
    plan.hook_text = hook_av.hook_text
    plan.hook_source = {
        "url": hv.url,
        "views": hv.views,
        "date": hv.upload_date,
        "hook_type": hook_av.hook_type,
        "full_hook": (hv.transcript or hv.description or hv.title)[:80],
        "account_name": hv.account_name,
        "account_url": hv.account_url,
    }

    # トピック
    plan.topic = content_av.topics[0] if content_av.topics else "スキンケア全般"

    # コンテンツ
    content_text = cv.transcript or cv.description or cv.title or ""
    plan.content_summary = _summarize_content(content_text)
    plan.content_sources = [{
        "url": cv.url,
        "views": cv.views,
        "date": cv.upload_date,
        "title": cv.title or cv.description[:50] if cv.description else "",
        "topics": content_av.topics,
        "account_name": cv.account_name,
        "account_url": cv.account_url,
    }]

    # 参考台本スタイル
    plan.reference_style = ref_style

    # 台本構造
    plan.structure = {
        "hook": plan.hook_text,
        "bridge": _generate_bridge(plan.hook_text, plan.topic),
        "body": plan.content_summary,
        "cta": _generate_cta(plan.topic),
    }

    # 全体台本
    plan.full_script = _compose_script(plan, ref_style)

    return plan


# ===== 台本生成ヘルパー =====

def _classify_hook(text: str) -> str:
    if not text:
        return "その他"
    for hook_type, patterns in HOOK_TYPES.items():
        for p in patterns:
            if re.search(p, text):
                return hook_type
    return "ストレート型"


def _detect_topics(text: str) -> list[str]:
    found = []
    for topic, keywords in SKIN_TOPICS.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                found.append(topic)
                break
    return found


def _analyze_structure(text: str) -> dict:
    if not text or len(text) < 10:
        return {}
    total = len(text)
    third = max(total // 3, 1)
    return {
        "intro": text[:third][:100],
        "body": text[third:third * 2][:150],
        "outro": text[third * 2:][:100],
        "total_length": total,
    }


def _summarize_content(text: str) -> str:
    if not text:
        return ""
    total = len(text)
    if total <= 100:
        return text
    quarter = total // 4
    return text[quarter:quarter * 3][:300]


def _generate_bridge(hook_text: str, topic: str) -> str:
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
    ctas = [
        "他にも知りたい方はフォローしてね！",
        "保存して見返してね！",
        "もっと詳しく知りたい人はコメントで教えて！",
        "参考になったらいいねしてね！",
    ]
    return ctas[hash(topic) % len(ctas)]


def _compose_script(plan: ScriptPlan, ref_style: dict = None) -> str:
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

    # 参考台本スタイルの注記
    if ref_style and ref_style.get("avg_length"):
        parts.append(f"\n【参考】台本目安文字数: 約{ref_style['avg_length']}文字 "
                     f"({ref_style.get('script_count', 0)}本の参考台本より)")

    # 締め
    cta = plan.structure.get("cta", "")
    if cta:
        parts.append(f"\n【締め】\n{cta}")

    return "\n".join(parts)


# ===== フロント表示用整形 =====

def format_plans_for_display(plans: list[ScriptPlan]) -> list[dict]:
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
                "account_name": plan.hook_source.get("account_name", ""),
                "account_url": plan.hook_source.get("account_url", ""),
            },
            "topic": plan.topic,
            "content_summary": plan.content_summary[:200],
            "content_sources": plan.content_sources,
            "reference_style": plan.reference_style,
            "structure": plan.structure,
            "full_script": plan.full_script,
        })
    return result


def get_research_summary(analysis: dict) -> dict:
    hook_candidates = analysis.get("hook_candidates", [])
    content_candidates = analysis.get("content_candidates", [])
    topics_summary = analysis.get("topics_summary", {})

    topic_counts = {t: len(avs) for t, avs in topics_summary.items()}

    top_hooks = []
    for a in hook_candidates[:10]:
        top_hooks.append({
            "text": a.hook_text,
            "type": a.hook_type,
            "views": a.video.views,
            "url": a.video.url,
            "date": a.video.upload_date,
            "account_name": a.video.account_name,
            "account_url": a.video.account_url,
        })

    # リサーチ動画一覧
    all_videos = []
    for a in analysis.get("analyzed", []):
        v = a.video
        all_videos.append({
            "video_id": v.video_id,
            "url": v.url,
            "title": v.title,
            "views": v.views,
            "likes": v.likes,
            "duration": v.duration,
            "upload_date": v.upload_date,
            "account_name": v.account_name,
            "account_url": v.account_url,
            "transcript": v.transcript[:100] if v.transcript else "",
            "has_transcript": bool(v.transcript),
            "hook_text": a.hook_text,
            "hook_type": a.hook_type,
            "topics": a.topics,
        })
    all_videos.sort(key=lambda x: x["views"], reverse=True)

    return {
        "total_videos": analysis.get("total_videos", 0),
        "hook_count": len(hook_candidates),
        "content_count": len(content_candidates),
        "topic_counts": topic_counts,
        "hook_type_counts": analysis.get("hook_type_counts", {}),
        "top_hooks": top_hooks,
        "all_videos": all_videos[:30],
    }
