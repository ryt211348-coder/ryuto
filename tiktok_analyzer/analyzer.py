"""バイラル動画の台本から共通項を分析する."""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .extractor import VideoInfo

console = Console()


@dataclass
class AnalysisResult:
    total_videos: int = 0
    avg_duration: float = 0.0
    avg_views: float = 0.0
    avg_likes: float = 0.0

    # 構造パターン
    hook_patterns: list[dict] = field(default_factory=list)
    ending_patterns: list[dict] = field(default_factory=list)

    # コンテンツパターン
    common_phrases: list[tuple[str, int]] = field(default_factory=list)
    common_topics: list[tuple[str, int]] = field(default_factory=list)

    # 形式パターン
    duration_distribution: dict[str, int] = field(default_factory=dict)
    avg_script_length: float = 0.0
    question_usage_rate: float = 0.0
    cta_usage_rate: float = 0.0

    # 感情・トーン
    urgency_words_rate: float = 0.0
    negative_hook_rate: float = 0.0
    number_usage_rate: float = 0.0


# 日本語のバイラルパターン用キーワード
HOOK_KEYWORDS = [
    "知ってた", "知ってますか", "実は", "衝撃", "ヤバい", "やばい",
    "マジで", "まじで", "びっくり", "驚き", "秘密", "裏技",
    "知らないと損", "損してる", "危険", "注意", "絶対", "必ず",
    "最強", "神", "プロ", "99%", "誰も知らない", "禁断",
    "閲覧注意", "これ見て", "聞いて", "待って", "えっ",
]

CTA_KEYWORDS = [
    "フォロー", "いいね", "コメント", "シェア", "保存",
    "プロフィール", "リンク", "詳しく", "続き", "パート2",
    "part2", "次回", "また", "お楽しみに",
]

URGENCY_KEYWORDS = [
    "今すぐ", "急いで", "早く", "限定", "期間", "最後",
    "ラスト", "終了", "なくなる", "売り切れ", "残り",
]

NEGATIVE_HOOK_KEYWORDS = [
    "やめて", "ダメ", "危険", "注意", "失敗", "後悔",
    "損", "最悪", "絶対にやるな", "知らないと",
]


def analyze_hook(transcript: str) -> dict:
    """冒頭部分（フック）のパターンを分析する."""
    # 最初の30文字をフックとして分析
    hook = transcript[:80] if len(transcript) > 80 else transcript
    hook_lower = hook.lower()

    patterns = {
        "text": hook,
        "has_question": "?" in hook or "？" in hook,
        "has_number": bool(re.search(r"\d+", hook)),
        "has_hook_keyword": any(kw in hook for kw in HOOK_KEYWORDS),
        "has_negative_hook": any(kw in hook for kw in NEGATIVE_HOOK_KEYWORDS),
        "matched_keywords": [kw for kw in HOOK_KEYWORDS if kw in hook],
    }
    return patterns


def analyze_ending(transcript: str) -> dict:
    """終盤部分（CTA）のパターンを分析する."""
    ending = transcript[-80:] if len(transcript) > 80 else transcript

    patterns = {
        "text": ending,
        "has_cta": any(kw in ending for kw in CTA_KEYWORDS),
        "has_question": "?" in ending or "？" in ending,
        "matched_cta": [kw for kw in CTA_KEYWORDS if kw in ending],
    }
    return patterns


def extract_phrases(transcript: str, min_len: int = 3, max_len: int = 15) -> list[str]:
    """台本からフレーズを抽出する."""
    # 句読点やスペースで分割
    parts = re.split(r"[。、！？!?\s\n,.]", transcript)
    phrases = []
    for part in parts:
        part = part.strip()
        if min_len <= len(part) <= max_len:
            phrases.append(part)
    return phrases


def categorize_duration(seconds: int) -> str:
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


def analyze_viral_patterns(
    videos: list[VideoInfo],
    transcripts: dict[str, str],
) -> AnalysisResult:
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

    # 台本分析
    all_phrases = []
    question_count = 0
    cta_count = 0
    urgency_count = 0
    negative_hook_count = 0
    number_in_hook_count = 0
    script_lengths = []

    for video in videos:
        transcript = transcripts.get(video.video_id, "")
        if not transcript:
            continue

        script_lengths.append(len(transcript))

        # フック分析
        hook_info = analyze_hook(transcript)
        result.hook_patterns.append({
            "video_id": video.video_id,
            "views": video.view_count,
            **hook_info,
        })

        if hook_info["has_question"]:
            question_count += 1
        if hook_info["has_negative_hook"]:
            negative_hook_count += 1
        if hook_info["has_number"]:
            number_in_hook_count += 1

        # エンディング分析
        ending_info = analyze_ending(transcript)
        result.ending_patterns.append({
            "video_id": video.video_id,
            "views": video.view_count,
            **ending_info,
        })

        if ending_info["has_cta"]:
            cta_count += 1

        # 緊急性キーワード
        if any(kw in transcript for kw in URGENCY_KEYWORDS):
            urgency_count += 1

        # フレーズ抽出
        all_phrases.extend(extract_phrases(transcript))

    transcribed_count = len(script_lengths)
    if transcribed_count > 0:
        result.avg_script_length = sum(script_lengths) / transcribed_count
        result.question_usage_rate = question_count / transcribed_count
        result.cta_usage_rate = cta_count / transcribed_count
        result.urgency_words_rate = urgency_count / transcribed_count
        result.negative_hook_rate = negative_hook_count / transcribed_count
        result.number_usage_rate = number_in_hook_count / transcribed_count

    # 頻出フレーズ
    phrase_counter = Counter(all_phrases)
    result.common_phrases = phrase_counter.most_common(30)

    return result


def print_analysis(result: AnalysisResult) -> None:
    """分析結果をコンソールに出力する."""
    console.print(Panel("[bold]バイラル動画分析レポート[/bold]", style="cyan"))

    # 基本統計
    table = Table(title="基本統計")
    table.add_column("指標", style="cyan")
    table.add_column("値", style="green")
    table.add_row("分析動画数", f"{result.total_videos} 本")
    table.add_row("平均再生数", f"{result.avg_views:,.0f}")
    table.add_row("平均いいね数", f"{result.avg_likes:,.0f}")
    table.add_row("平均動画長", f"{result.avg_duration:.0f} 秒")
    table.add_row("平均台本文字数", f"{result.avg_script_length:.0f} 文字")
    console.print(table)

    # 動画長分布
    if result.duration_distribution:
        table = Table(title="動画長の分布")
        table.add_column("カテゴリ", style="cyan")
        table.add_column("本数", style="green")
        for cat, count in result.duration_distribution.items():
            bar = "█" * count
            table.add_row(cat, f"{count} {bar}")
        console.print(table)

    # パターン使用率
    table = Table(title="台本パターン使用率")
    table.add_column("パターン", style="cyan")
    table.add_column("使用率", style="green")
    table.add_column("効果", style="yellow")
    table.add_row("冒頭で疑問文", f"{result.question_usage_rate:.0%}", "視聴者の注意を引く")
    table.add_row("ネガティブフック", f"{result.negative_hook_rate:.0%}", "不安・好奇心を刺激")
    table.add_row("冒頭に数字", f"{result.number_usage_rate:.0%}", "具体性で信頼感UP")
    table.add_row("CTA（行動喚起）", f"{result.cta_usage_rate:.0%}", "フォロー・いいね誘導")
    table.add_row("緊急性キーワード", f"{result.urgency_words_rate:.0%}", "即時行動を促す")
    console.print(table)

    # フック例
    if result.hook_patterns:
        console.print("\n[bold]冒頭フック例（再生数上位）:[/bold]")
        sorted_hooks = sorted(result.hook_patterns, key=lambda x: x["views"], reverse=True)
        for hook in sorted_hooks[:5]:
            kws = ", ".join(hook.get("matched_keywords", []))
            console.print(
                f"  [cyan]{hook['views']:>12,}再生[/cyan] | "
                f"「{hook['text'][:60]}」"
                f"{f' [yellow]({kws})[/yellow]' if kws else ''}"
            )

    # 頻出フレーズ
    if result.common_phrases:
        console.print("\n[bold]頻出フレーズ（2回以上出現）:[/bold]")
        for phrase, count in result.common_phrases:
            if count >= 2:
                console.print(f"  {count:3d}回 | {phrase}")


def generate_report(
    videos: list[VideoInfo],
    transcripts: dict[str, str],
    result: AnalysisResult,
    output_path: Path,
) -> None:
    """分析レポートをMarkdownファイルとして出力する."""
    lines = [
        "# TikTok バイラル動画分析レポート\n",
        f"## 概要\n",
        f"- **分析動画数**: {result.total_videos} 本（100万再生以上）",
        f"- **平均再生数**: {result.avg_views:,.0f}",
        f"- **平均いいね数**: {result.avg_likes:,.0f}",
        f"- **平均動画長**: {result.avg_duration:.0f} 秒",
        f"- **平均台本文字数**: {result.avg_script_length:.0f} 文字\n",
        "---\n",
        "## 動画長の分布\n",
        "| カテゴリ | 本数 |",
        "|---------|------|",
    ]
    for cat, count in result.duration_distribution.items():
        lines.append(f"| {cat} | {count} |")

    lines.extend([
        "\n---\n",
        "## 台本パターン分析\n",
        "### 使用率\n",
        "| パターン | 使用率 | 効果 |",
        "|---------|--------|------|",
        f"| 冒頭で疑問文 | {result.question_usage_rate:.0%} | 視聴者の注意を引く |",
        f"| ネガティブフック | {result.negative_hook_rate:.0%} | 不安・好奇心を刺激 |",
        f"| 冒頭に数字 | {result.number_usage_rate:.0%} | 具体性で信頼感UP |",
        f"| CTA（行動喚起） | {result.cta_usage_rate:.0%} | フォロー・いいね誘導 |",
        f"| 緊急性キーワード | {result.urgency_words_rate:.0%} | 即時行動を促す |",
    ])

    # フック例
    if result.hook_patterns:
        lines.extend(["\n---\n", "## 冒頭フック例（再生数上位）\n"])
        sorted_hooks = sorted(result.hook_patterns, key=lambda x: x["views"], reverse=True)
        for i, hook in enumerate(sorted_hooks[:10], 1):
            kws = ", ".join(hook.get("matched_keywords", []))
            lines.append(
                f"{i}. **{hook['views']:,}再生** - 「{hook['text'][:80]}」"
                f"{f' → キーワード: {kws}' if kws else ''}"
            )

    # エンディングパターン
    if result.ending_patterns:
        lines.extend(["\n---\n", "## エンディング・CTAパターン\n"])
        cta_hooks = [e for e in result.ending_patterns if e.get("has_cta")]
        if cta_hooks:
            for e in sorted(cta_hooks, key=lambda x: x["views"], reverse=True)[:10]:
                ctas = ", ".join(e.get("matched_cta", []))
                lines.append(f"- **{e['views']:,}再生** - CTA: {ctas}")

    # 頻出フレーズ
    if result.common_phrases:
        lines.extend(["\n---\n", "## 頻出フレーズ\n"])
        lines.append("| フレーズ | 出現回数 |")
        lines.append("|---------|---------|")
        for phrase, count in result.common_phrases:
            if count >= 2:
                lines.append(f"| {phrase} | {count} |")

    # 全動画の台本
    lines.extend(["\n---\n", "## 全動画台本一覧\n"])
    for video in sorted(videos, key=lambda v: v.view_count, reverse=True):
        transcript = transcripts.get(video.video_id, "（文字起こしなし）")
        lines.extend([
            f"### {video.view_count:,}再生 | {video.duration}秒 | {video.title[:50]}\n",
            f"**URL**: {video.url}\n",
            f"```",
            transcript,
            f"```\n",
        ])

    # 共通項まとめ
    lines.extend([
        "\n---\n",
        "## バイラル共通項まとめ\n",
        "### 1. フック（冒頭）の特徴",
        f"- 疑問文で始める動画: **{result.question_usage_rate:.0%}**",
        f"- ネガティブフックを使う動画: **{result.negative_hook_rate:.0%}**",
        f"- 具体的な数字を冒頭に入れる動画: **{result.number_usage_rate:.0%}**",
        "",
        "### 2. 構成の特徴",
        f"- 最も多い動画長: **{max(result.duration_distribution, key=result.duration_distribution.get) if result.duration_distribution else 'N/A'}**",
        f"- 平均台本文字数: **{result.avg_script_length:.0f}文字**",
        "",
        "### 3. CTA（行動喚起）",
        f"- CTA使用率: **{result.cta_usage_rate:.0%}**",
        f"- 緊急性キーワード使用率: **{result.urgency_words_rate:.0%}**",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"\n  [green]レポート保存: {output_path}[/green]")
