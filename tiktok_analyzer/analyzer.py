"""バイラル動画の台本から企画転用可能な共通項を分析する."""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from .extractor import VideoInfo

console = Console()


@dataclass
class AnalysisResult:
    total_videos: int = 0
    avg_duration: float = 0.0
    avg_views: float = 0.0
    avg_likes: float = 0.0
    avg_script_length: float = 0.0

    # 動画長分布
    duration_distribution: dict = field(default_factory=dict)

    # === 企画分析 ===
    content_formats: list = field(default_factory=list)       # 企画フォーマット分類
    topic_categories: list = field(default_factory=list)      # 扱っているテーマ/商品カテゴリ
    product_mentions: list = field(default_factory=list)      # 言及されている商品・ブランド

    # === 台本構成分析 ===
    hook_patterns: list = field(default_factory=list)         # フック（冒頭）
    structure_patterns: list = field(default_factory=list)    # 台本の構成パターン
    ending_patterns: list = field(default_factory=list)       # エンディング

    # === 訴求軸分析 ===
    appeal_types: list = field(default_factory=list)          # 訴求の種類（悩み解決/比較/ランキング等）
    emotional_triggers: list = field(default_factory=list)    # 感情トリガー

    # === 使用率 ===
    format_rates: dict = field(default_factory=dict)
    hook_technique_rates: dict = field(default_factory=dict)
    appeal_rates: dict = field(default_factory=dict)

    # === 頻出フレーズ ===
    common_phrases: list = field(default_factory=list)

    # === 再生数との相関 ===
    top_performing_insights: list = field(default_factory=list)


# ===== 企画フォーマット =====
FORMAT_PATTERNS = {
    "ランキング・〇選": [r"\d+選", r"ランキング", r"TOP\s?\d+", r"トップ\d+", r"ベスト\d+", r"おすすめ\d+"],
    "比較・対決": ["比較", "vs", "VS", "対決", "違い", "どっち", "どちら"],
    "ビフォーアフター": ["ビフォーアフター", "before", "after", "変化", "使う前", "使った後", "1ヶ月後", "1週間後"],
    "How-to・やり方": ["やり方", "方法", "手順", "ステップ", "コツ", "テクニック", "裏技", "ハウツー", "how to"],
    "レビュー・紹介": ["レビュー", "紹介", "買ってみた", "試してみた", "使ってみた", "開封", "正直", "本音"],
    "暴露・裏側": ["暴露", "裏側", "真実", "本当は", "業界", "闇", "秘密", "内緒"],
    "ルーティン": ["ルーティン", "ルーティーン", "routine", "モーニング", "ナイト", "1日"],
    "Q&A・質問回答": ["質問", "Q&A", "回答", "聞かれ", "よく聞く", "教えて"],
    "ストーリー・体験談": ["体験", "経験", "ストーリー", "実話", "あの時", "過去に"],
    "まとめ・解説": ["まとめ", "解説", "徹底", "完全版", "全て", "すべて"],
}

# ===== 訴求パターン =====
APPEAL_PATTERNS = {
    "悩み解決型": ["悩み", "困って", "解決", "改善", "なくす", "消す", "治す", "直す", "対策", "防ぐ"],
    "損失回避型": ["知らないと損", "損してる", "もったいない", "損する", "やめて", "NG", "ダメ", "絶対やるな"],
    "権威・プロ型": ["プロ", "専門", "美容師", "皮膚科", "医師", "薬剤師", "現役", "元", "歴\d+年"],
    "コスパ・お得型": ["コスパ", "安い", "プチプラ", "お得", "節約", "半額", "セール", "円"],
    "驚き・衝撃型": ["衝撃", "ヤバい", "やばい", "驚き", "マジで", "まじで", "信じられない", "えっ"],
    "限定・希少型": ["限定", "今だけ", "期間", "なくなる", "売り切れ", "残り", "新発売", "新作"],
    "共感・あるある型": ["あるある", "わかる", "共感", "同じ", "みんな", "あなたも"],
    "数字・具体型": [r"\d+%", r"\d+倍", r"\d+日", r"\d+ヶ月", r"\d+万", r"\d+円"],
}

# ===== 感情トリガー =====
EMOTION_PATTERNS = {
    "好奇心": ["実は", "知ってた", "意外", "まさか", "秘密", "裏", "隠された"],
    "不安・恐怖": ["危険", "注意", "怖い", "リスク", "副作用", "失敗", "後悔"],
    "期待・希望": ["変わる", "人生", "最高", "神", "最強", "革命", "感動"],
    "怒り・不満": ["許せない", "ひどい", "最悪", "詐欺", "嘘", "騙され"],
    "安心・信頼": ["安心", "安全", "信頼", "実績", "証明", "エビデンス"],
}

# ===== 台本構成パターン =====
STRUCTURE_PATTERNS = {
    "問題提起→解決": ["でも大丈夫", "そこで", "解決策", "答えは", "実は簡単"],
    "結論ファースト": [],  # 冒頭に結論がある場合（別途判定）
    "リスト型": [r"一つ目", r"二つ目", r"1つ目", r"2つ目", r"まず", r"次に", r"最後に", r"ポイント\d"],
    "ストーリー型": ["ある日", "最初は", "きっかけ", "そしたら", "結果的に"],
    "Before→After型": ["前は", "以前は", "今は", "今では", "変わった", "使い始めて"],
}


# 企画に役立たない接続詞・助詞・文末表現などのストップワード
STOPWORDS = {
    # 接続詞・つなぎ言葉
    "そして", "さらに", "また", "しかし", "でも", "ただ", "ところで", "ちなみに",
    "それで", "だから", "なので", "つまり", "要するに", "というわけで",
    "それから", "あとは", "次に", "まず", "最後に", "ということで",
    # 指示語・代名詞
    "これは", "それは", "あれは", "ここで", "そこで", "これが", "それが",
    "こちら", "そちら", "あちら", "これを", "それを", "こちらは",
    "このように", "そのように",
    # 文末・フィラー
    "なんですけど", "なんですが", "なんですよ", "ですけど", "ですが",
    "ということで", "と思います", "と思う", "になります", "になりました",
    "してみてください", "してください", "しています", "なっています",
    "ぜひ参考にしてみてください", "参考にしてみてください", "チェックしてみてね",
    "すめです", "おすすめです",
    # 列挙マーカー
    "一つ目は", "二つ目は", "三つ目は", "四つ目は", "五つ目は",
    "1つ目は", "2つ目は", "3つ目は", "4つ目は", "5つ目は",
    "六つ目は", "七つ目は", "八つ目は", "九つ目は",
    "6つ目は", "7つ目は", "8つ目は", "9つ目は",
    # 一般的すぎる表現
    "いうことで", "ある", "いる", "する", "なる", "できる",
    "ない", "ある", "いい", "よい", "すごい", "すごく",
    "本当に", "めちゃくちゃ", "かなり", "とても", "非常に",
    "やっぱり", "やはり", "実際に", "個人的に",
}


def _is_stopword(phrase):
    """フレーズがストップワードに該当するか判定."""
    p = phrase.strip()
    # 完全一致
    if p in STOPWORDS:
        return True
    # 短すぎて意味がない（ひらがな・カタカナのみで4文字以下）
    if len(p) <= 4 and all('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in p):
        return True
    # 助詞だけで終わる短いフレーズ
    if len(p) <= 5 and p.endswith(("は", "が", "を", "に", "で", "と", "も", "の", "へ", "から", "まで", "より")):
        return True
    return False


def _match_patterns(text, pattern_dict):
    """テキストに対してパターン辞書をマッチングする."""
    matched = {}
    for category, patterns in pattern_dict.items():
        count = 0
        for p in patterns:
            if re.search(p, text):
                count += 1
        if count > 0:
            matched[category] = count
    return matched


def _extract_products(text):
    """テキストから商品名・ブランド名を抽出する."""
    products = []
    # 「」で囲まれた固有名詞
    quoted = re.findall(r"[「『](.*?)[」』]", text)
    products.extend(quoted)
    # #ハッシュタグ
    hashtags = re.findall(r"#(\w+)", text)
    products.extend(hashtags)
    return products


def _analyze_script_structure(transcript):
    """台本の構造を分析する."""
    total_len = len(transcript)
    if total_len == 0:
        return {}

    # 3分割して分析
    third = total_len // 3
    intro = transcript[:third]
    body = transcript[third:third*2]
    outro = transcript[third*2:]

    structure = {
        "intro_text": intro[:100],
        "body_text": body[:100],
        "outro_text": outro[:100],
        "total_length": total_len,
    }

    # 構成パターンの判定
    matched = _match_patterns(transcript, STRUCTURE_PATTERNS)
    structure["patterns"] = list(matched.keys())

    # リスト型の検出（数字列挙）
    list_markers = len(re.findall(r"[一二三四五六七八九十]つ目|[\d１２３４５６７８９]つ目|\d+\.|第\d", transcript))
    if list_markers >= 2:
        if "リスト型" not in structure["patterns"]:
            structure["patterns"].append("リスト型")
    structure["list_count"] = list_markers

    return structure


def categorize_duration(seconds):
    """動画の長さをカテゴリに分類."""
    if seconds <= 15:
        return "~15秒"
    elif seconds <= 30:
        return "16~30秒"
    elif seconds <= 60:
        return "31~60秒"
    elif seconds <= 180:
        return "1~3分"
    else:
        return "3分以上"


def analyze_viral_patterns(videos, transcripts):
    """バイラル動画の共通パターンを総合分析する."""
    console.print("\n[bold cyan]バイラルパターン分析中...[/bold cyan]\n")

    result = AnalysisResult()
    result.total_videos = len(videos)

    if not videos:
        return result

    # 基本統計
    result.avg_duration = sum(v.duration for v in videos) / len(videos)
    result.avg_views = sum(v.view_count for v in videos) / len(videos)
    result.avg_likes = sum(v.like_count for v in videos) / len(videos)

    # 動画長分布
    duration_counts = Counter(categorize_duration(v.duration) for v in videos)
    result.duration_distribution = dict(duration_counts.most_common())

    # 各動画を分析
    format_counter = Counter()
    appeal_counter = Counter()
    emotion_counter = Counter()
    structure_counter = Counter()
    all_products = []
    all_phrases = []
    script_lengths = []
    video_analyses = []

    for video in videos:
        transcript = transcripts.get(video.video_id, "")
        full_text = transcript + " " + video.description
        if not full_text.strip():
            continue

        script_lengths.append(len(transcript))

        analysis = {"video_id": video.video_id, "views": video.view_count}

        # 企画フォーマット
        formats = _match_patterns(full_text, FORMAT_PATTERNS)
        for fmt in formats:
            format_counter[fmt] += 1
        analysis["formats"] = list(formats.keys())

        # 訴求パターン
        appeals = _match_patterns(full_text, APPEAL_PATTERNS)
        for ap in appeals:
            appeal_counter[ap] += 1
        analysis["appeals"] = list(appeals.keys())

        # 感情トリガー
        emotions = _match_patterns(full_text, EMOTION_PATTERNS)
        for em in emotions:
            emotion_counter[em] += 1
        analysis["emotions"] = list(emotions.keys())

        # フック（冒頭80文字）
        hook = transcript[:80] if len(transcript) > 80 else transcript
        analysis["hook_text"] = hook
        analysis["hook_has_question"] = bool(re.search(r"[?？]", hook))
        analysis["hook_has_number"] = bool(re.search(r"\d+", hook))
        analysis["hook_has_negative"] = any(kw in hook for kw in ["やめて", "ダメ", "危険", "注意", "損", "NG"])
        analysis["hook_has_curiosity"] = any(kw in hook for kw in ["実は", "知ってた", "意外", "秘密", "衝撃"])

        # エンディング（末尾80文字）
        ending = transcript[-80:] if len(transcript) > 80 else transcript
        analysis["ending_text"] = ending
        analysis["ending_has_cta"] = any(kw in ending for kw in ["フォロー", "いいね", "コメント", "保存", "シェア"])
        analysis["ending_has_next"] = any(kw in ending for kw in ["続き", "次回", "パート2", "part2"])

        # 台本構造
        structure = _analyze_script_structure(transcript)
        for sp in structure.get("patterns", []):
            structure_counter[sp] += 1
        analysis["structure"] = structure

        # 商品・ブランド抽出
        products = _extract_products(full_text)
        all_products.extend(products)
        analysis["products"] = products

        # フレーズ抽出（ストップワード除外）
        parts = re.split(r"[。、！？!?\s\n,.]", transcript)
        for part in parts:
            part = part.strip()
            if 3 <= len(part) <= 20 and not _is_stopword(part):
                all_phrases.append(part)

        video_analyses.append(analysis)
        result.hook_patterns.append(analysis)

    transcribed_count = len(script_lengths)
    if transcribed_count > 0:
        result.avg_script_length = sum(script_lengths) / transcribed_count

    # === 企画フォーマット集計 ===
    result.content_formats = format_counter.most_common(15)
    if transcribed_count > 0:
        result.format_rates = {k: v / transcribed_count for k, v in format_counter.items()}

    # === 訴求パターン集計 ===
    result.appeal_types = appeal_counter.most_common(15)
    if transcribed_count > 0:
        result.appeal_rates = {k: v / transcribed_count for k, v in appeal_counter.items()}

    # === 感情トリガー集計 ===
    result.emotional_triggers = emotion_counter.most_common(10)

    # === 台本構成集計 ===
    result.structure_patterns = structure_counter.most_common(10)

    # === フック手法の使用率（排他分類・合計100%） ===
    if transcribed_count > 0:
        hook_type_counter = Counter()
        for a in video_analyses:
            # 優先順位で1つだけ分類
            if a.get("hook_has_negative"):
                hook_type_counter["ネガティブフック"] += 1
            elif a.get("hook_has_curiosity"):
                hook_type_counter["好奇心フック"] += 1
            elif a.get("hook_has_question"):
                hook_type_counter["疑問文フック"] += 1
            elif a.get("hook_has_number"):
                hook_type_counter["数字フック"] += 1
            else:
                hook_type_counter["ストレート型"] += 1

        result.hook_technique_rates = {
            k: v / transcribed_count for k, v in hook_type_counter.most_common()
        }

    # === 商品・ブランド集計 ===
    product_counter = Counter(all_products)
    result.product_mentions = product_counter.most_common(30)

    # === 頻出フレーズ ===
    phrase_counter = Counter(all_phrases)
    result.common_phrases = [(p, c) for p, c in phrase_counter.most_common(30) if c >= 2]

    # === 再生数トップの特徴抽出 ===
    sorted_analyses = sorted(video_analyses, key=lambda x: x["views"], reverse=True)
    top_5 = sorted_analyses[:5]
    if top_5:
        top_formats = Counter()
        top_appeals = Counter()
        for a in top_5:
            for f in a.get("formats", []):
                top_formats[f] += 1
            for ap in a.get("appeals", []):
                top_appeals[ap] += 1
        result.top_performing_insights = [
            {"label": "上位5本で最も多い企画", "items": top_formats.most_common(3)},
            {"label": "上位5本で最も多い訴求", "items": top_appeals.most_common(3)},
        ]

    return result


def print_analysis(result):
    """分析結果をコンソールに出力する（簡易版）."""
    console.print(f"  分析動画数: {result.total_videos}")
    console.print(f"  平均再生数: {result.avg_views:,.0f}")
    console.print(f"  企画フォーマット: {len(result.content_formats)} 種類")
    console.print(f"  訴求パターン: {len(result.appeal_types)} 種類")


def generate_report(videos, transcripts, result, output_path):
    """分析レポートをMarkdownファイルとして出力する."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# TikTok バイラル動画分析レポート\n",
        f"分析動画数: {result.total_videos}本\n",
    ]

    # 企画フォーマット
    if result.content_formats:
        lines.append("## 企画フォーマット\n")
        for fmt, count in result.content_formats:
            lines.append(f"- {fmt}: {count}本")

    # 訴求パターン
    if result.appeal_types:
        lines.append("\n## 訴求パターン\n")
        for ap, count in result.appeal_types:
            lines.append(f"- {ap}: {count}本")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"\n  [green]レポート保存: {output_path}[/green]")
