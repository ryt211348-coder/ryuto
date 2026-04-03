"""TikTokアカウントの全データを取得し、スタンドアロンHTMLレポートを生成する.

使い方:
    python generate_report.py https://www.tiktok.com/@username

出力:
    report_username.html（ブラウザで開くだけ）
"""

import json
import html
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tiktok_analyzer.extractor import extract_account_videos, _parse_username
from tiktok_sheet_tool import (
    compute_sheet_data,
    _parse_upload_date,
    _format_number,
    _build_posting_timeline,
)


def _build_video_list_json(videos):
    """動画リストをフロント用JSONに変換."""
    result = []
    for v in videos:
        dt = _parse_upload_date(v.upload_date)
        result.append({
            "id": v.video_id,
            "title": v.title or v.description[:80] or "(タイトルなし)",
            "description": v.description,
            "url": v.url,
            "views": v.view_count,
            "likes": v.like_count,
            "comments": v.comment_count,
            "shares": v.share_count,
            "duration": v.duration,
            "date": dt.strftime("%Y-%m-%d") if dt else "",
            "thumbnail": v.thumbnail,
        })
    return result


def _build_cumulative_views(videos):
    """累計再生数の推移データを作成."""
    dated = []
    for v in videos:
        dt = _parse_upload_date(v.upload_date)
        if dt:
            dated.append((dt, v.view_count))
    dated.sort(key=lambda x: x[0])

    cumulative = []
    total = 0
    for dt, views in dated:
        total += views
        cumulative.append({
            "date": dt.strftime("%Y-%m-%d"),
            "total": total,
        })
    return cumulative


def _build_top_videos(videos, n=20):
    """再生数トップN."""
    sorted_v = sorted(videos, key=lambda v: v.view_count, reverse=True)
    return _build_video_list_json(sorted_v[:n])


def generate_html_report(account_url, videos, sheet_data, output_path):
    """スタンドアロンHTMLレポートを生成."""
    username = _parse_username(account_url)
    all_videos_json = json.dumps(_build_video_list_json(videos), ensure_ascii=False)
    timeline_json = json.dumps(sheet_data.posting_timeline or [], ensure_ascii=False)
    cumulative_json = json.dumps(_build_cumulative_views(videos), ensure_ascii=False)
    top_videos_json = json.dumps(_build_top_videos(videos, 20), ensure_ascii=False)

    # シートデータ
    sd = sheet_data

    report_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TikTok分析: @{html.escape(username)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0f0f1a; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; line-height:1.6; }}
.container {{ max-width:1200px; margin:0 auto; padding:1.5rem; }}
h1 {{ color:#ff79c6; font-size:1.8rem; margin-bottom:0.3rem; }}
h2 {{ color:#bd93f9; font-size:1.2rem; margin:2rem 0 1rem; border-bottom:1px solid #3a3a4a; padding-bottom:0.5rem; }}
h3 {{ color:#f8f8f2; font-size:1rem; margin-bottom:0.8rem; }}
.subtitle {{ color:#6272a4; font-size:0.9rem; margin-bottom:1.5rem; }}
a {{ color:#8be9fd; text-decoration:none; }} a:hover {{ text-decoration:underline; }}

/* 統計カード */
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1rem; margin:1.5rem 0; }}
.stat {{ background:#1e1e2e; border:1px solid #3a3a4a; border-radius:8px; padding:1rem; text-align:center; }}
.stat .label {{ color:#6272a4; font-size:0.8rem; }}
.stat .number {{ color:#50fa7b; font-size:1.5rem; font-weight:700; margin:0.3rem 0; }}
.stat .detail {{ color:#6272a4; font-size:0.75rem; }}

/* シートデータ */
.sheet-table {{ width:100%; border-collapse:collapse; margin:1rem 0; font-size:0.9rem; }}
.sheet-table th,.sheet-table td {{ border:1px solid #3a3a4a; padding:0.6rem 0.8rem; text-align:left; }}
.sheet-table th {{ background:#2a2a3a; color:#ff79c6; font-weight:600; width:25%; }}
.sheet-table td {{ background:#1e1e2e; }}
.col-label {{ color:#bd93f9; font-weight:700; margin-right:0.3rem; }}
.sheet-val {{ color:#50fa7b; font-family:monospace; }}

/* チャート */
.chart-box {{ background:#1e1e2e; border:1px solid #3a3a4a; border-radius:8px; padding:1.5rem; margin:1rem 0; }}
.chart-wrap {{ position:relative; height:300px; }}

/* 動画テーブル */
.controls {{ display:flex; gap:1rem; margin:1rem 0; flex-wrap:wrap; align-items:center; }}
.controls input,.controls select {{ background:#1e1e2e; border:1px solid #3a3a4a; color:#f8f8f2; padding:0.5rem 0.8rem; border-radius:6px; font-size:0.9rem; }}
.controls input {{ flex:1; min-width:200px; }}
.video-table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
.video-table th {{ background:#2a2a3a; color:#ff79c6; padding:0.6rem; text-align:left; cursor:pointer; user-select:none; white-space:nowrap; }}
.video-table th:hover {{ background:#3a3a5a; }}
.video-table td {{ border-bottom:1px solid #2a2a3a; padding:0.6rem; vertical-align:top; }}
.video-table tr:hover td {{ background:#1a1a2a; }}
.video-title {{ color:#f8f8f2; font-weight:500; max-width:350px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.video-title:hover {{ white-space:normal; }}
.num {{ text-align:right; font-family:monospace; color:#50fa7b; }}
.date-col {{ white-space:nowrap; color:#6272a4; }}
.sort-arrow {{ margin-left:4px; font-size:0.7rem; }}

/* タブ */
.tabs {{ display:flex; gap:0; margin-top:2rem; border-bottom:2px solid #3a3a4a; }}
.tab {{ background:none; border:none; color:#6272a4; padding:0.7rem 1.2rem; cursor:pointer; font-size:0.9rem; border-bottom:2px solid transparent; margin-bottom:-2px; }}
.tab.active {{ color:#ff79c6; border-bottom-color:#ff79c6; }}
.tab:hover {{ color:#f8f8f2; }}
.tab-panel {{ display:none; padding-top:1rem; }}
.tab-panel.active {{ display:block; }}

/* コピーボタン */
.copy-btn {{ background:#44475a; border:none; color:#f8f8f2; padding:0.3rem 0.8rem; border-radius:4px; cursor:pointer; font-size:0.8rem; transition:all 0.2s; }}
.copy-btn:hover {{ background:#6272a4; }}
.copy-btn.copied {{ background:#50fa7b; color:#282a36; }}
.copy-all {{ background:#ff79c6; color:#282a36; border:none; padding:0.5rem 1.2rem; border-radius:6px; cursor:pointer; font-weight:600; font-size:0.9rem; margin:1rem 0; }}
.copy-all:hover {{ background:#ff92d0; }}
.badge {{ display:inline-block; background:#44475a; color:#f8f8f2; padding:0.1rem 0.5rem; border-radius:10px; font-size:0.75rem; margin-left:0.3rem; }}
</style>
</head>
<body>
<div class="container">

<h1>@{html.escape(username)} TikTok分析レポート</h1>
<p class="subtitle">生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M')} ｜ 取得動画数: {len(videos)}本 ｜ <a href="{html.escape(account_url)}" target="_blank">TikTokを開く</a></p>

<!-- 統計サマリー -->
<div class="stats">
    <div class="stat">
        <div class="label">総再生数</div>
        <div class="number">{_format_number(sd.total_views)}</div>
        <div class="detail">{sd.total_views:,}回</div>
    </div>
    <div class="stat">
        <div class="label">総動画数</div>
        <div class="number">{sd.total_videos}</div>
        <div class="detail">本</div>
    </div>
    <div class="stat">
        <div class="label">平均再生数/本</div>
        <div class="number">{_format_number(sd.avg_views_per_video)}</div>
        <div class="detail">{sd.avg_views_per_video:,}回</div>
    </div>
    <div class="stat">
        <div class="label">登録者</div>
        <div class="number">{sd.followers or '—'}</div>
    </div>
    <div class="stat">
        <div class="label">月間投稿（直近30日）</div>
        <div class="number">{sd.monthly_posts}</div>
        <div class="detail">本</div>
    </div>
    <div class="stat">
        <div class="label">平均月間投稿数</div>
        <div class="number">{sd.avg_monthly_posts}</div>
        <div class="detail">本/月（活動月のみ）</div>
    </div>
    <div class="stat">
        <div class="label">月間再生回数</div>
        <div class="number">{_format_number(sd.monthly_views)}</div>
        <div class="detail">直近30日</div>
    </div>
    <div class="stat">
        <div class="label">活動期間</div>
        <div class="number">{sd.active_months}<span style="font-size:0.8rem;color:#6272a4">/{sd.total_months_span}</span></div>
        <div class="detail">ヶ月（活動/全体）</div>
    </div>
</div>

<!-- タブ -->
<div class="tabs">
    <button class="tab active" onclick="switchTab('sheet')">シートデータ</button>
    <button class="tab" onclick="switchTab('charts')">チャート</button>
    <button class="tab" onclick="switchTab('videos')">全動画一覧 <span class="badge">{len(videos)}</span></button>
    <button class="tab" onclick="switchTab('top')">再生数TOP20</button>
</div>

<!-- ====== シートデータタブ ====== -->
<div class="tab-panel active" id="panel-sheet">
    <h2>スプレッドシート用データ</h2>
    <button class="copy-all" onclick="copyAllAsRow()">全データを1行コピー（タブ区切り → Sheetsにペースト可）</button>
    <table class="sheet-table">
        <tr><th><span class="col-label">A</span> 媒体</th><td><span class="sheet-val" id="sv-platform">TikTok</span> <button class="copy-btn" onclick="cc('sv-platform',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">B</span> URL</th><td><span class="sheet-val" id="sv-url">{html.escape(account_url)}</span> <button class="copy-btn" onclick="cc('sv-url',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">C</span> 登録者</th><td><span class="sheet-val" id="sv-followers">{html.escape(sd.followers or '取得不可')}</span> <button class="copy-btn" onclick="cc('sv-followers',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">D</span> 総再生数</th><td><span class="sheet-val" id="sv-views">{sd.total_views:,}</span> <button class="copy-btn" onclick="cc('sv-views',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">E</span> 月間再生回数</th><td><span class="sheet-val" id="sv-mviews">{_format_number(sd.monthly_views)}回</span> <button class="copy-btn" onclick="cc('sv-mviews',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">F</span> 月間投稿本数</th><td><span class="sheet-val" id="sv-mposts">{sd.monthly_posts}本（平均 {sd.avg_monthly_posts}本/月）</span> <button class="copy-btn" onclick="cc('sv-mposts',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">G</span> 平均再生数/本</th><td><span class="sheet-val" id="sv-avgv">{_format_number(sd.avg_views_per_video)}回</span> <button class="copy-btn" onclick="cc('sv-avgv',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">H</span> 登録者推移</th><td><span class="sheet-val" id="sv-trend">（要手動入力）</span> <button class="copy-btn" onclick="cc('sv-trend',this)">コピー</button></td></tr>
        <tr><th><span class="col-label">I</span> 初投稿</th><td><span class="sheet-val" id="sv-first">{html.escape(sd.first_post_date or '不明')}</span> <button class="copy-btn" onclick="cc('sv-first',this)">コピー</button></td></tr>
    </table>
</div>

<!-- ====== チャートタブ ====== -->
<div class="tab-panel" id="panel-charts">
    <div class="chart-box">
        <h3>累計再生数の推移</h3>
        <div class="chart-wrap"><canvas id="cumulativeChart"></canvas></div>
    </div>
    <div class="chart-box">
        <h3>月別投稿数の推移（波グラフ）</h3>
        <div class="chart-wrap"><canvas id="postingChart"></canvas></div>
    </div>
    <div class="chart-box">
        <h3>月別再生数の推移</h3>
        <div class="chart-wrap"><canvas id="viewsChart"></canvas></div>
    </div>
</div>

<!-- ====== 全動画一覧タブ ====== -->
<div class="tab-panel" id="panel-videos">
    <h2>全動画一覧</h2>
    <div class="controls">
        <input type="text" id="searchInput" placeholder="タイトル検索..." oninput="filterVideos()">
        <select id="sortSelect" onchange="sortVideos()">
            <option value="views-desc">再生数（多い順）</option>
            <option value="views-asc">再生数（少ない順）</option>
            <option value="likes-desc">いいね（多い順）</option>
            <option value="date-desc">日付（新しい順）</option>
            <option value="date-asc">日付（古い順）</option>
            <option value="comments-desc">コメント（多い順）</option>
        </select>
    </div>
    <div id="videoCountDisplay" style="color:#6272a4;font-size:0.85rem;margin-bottom:0.5rem;"></div>
    <table class="video-table">
        <thead>
            <tr>
                <th style="width:40px">#</th>
                <th>タイトル / 説明</th>
                <th onclick="sortBy('views')" style="width:100px">再生数 <span class="sort-arrow" id="arrow-views"></span></th>
                <th onclick="sortBy('likes')" style="width:90px">いいね <span class="sort-arrow" id="arrow-likes"></span></th>
                <th onclick="sortBy('comments')" style="width:80px">コメント <span class="sort-arrow" id="arrow-comments"></span></th>
                <th onclick="sortBy('shares')" style="width:80px">シェア <span class="sort-arrow" id="arrow-shares"></span></th>
                <th onclick="sortBy('date')" style="width:100px">投稿日 <span class="sort-arrow" id="arrow-date"></span></th>
            </tr>
        </thead>
        <tbody id="videoTableBody"></tbody>
    </table>
</div>

<!-- ====== TOP20タブ ====== -->
<div class="tab-panel" id="panel-top">
    <h2>再生数 TOP20</h2>
    <div id="topVideosList"></div>
</div>

</div><!-- /container -->

<script>
// ── データ ──
const allVideos = {all_videos_json};
const timeline = {timeline_json};
const cumulative = {cumulative_json};
const topVideos = {top_videos_json};
let displayedVideos = [...allVideos];
let currentSort = 'views-desc';

// ── タブ切替 ──
function switchTab(name) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('panel-' + name).classList.add('active');

    // チャートは初回表示時に描画
    if (name === 'charts' && !window._chartsRendered) {{
        renderCharts();
        window._chartsRendered = true;
    }}
}}

// ── チャート描画 ──
function renderCharts() {{
    // 累計再生数
    new Chart(document.getElementById('cumulativeChart'), {{
        type: 'line',
        data: {{
            labels: cumulative.map(d => d.date),
            datasets: [{{
                label: '累計再生数',
                data: cumulative.map(d => d.total),
                borderColor: '#50fa7b',
                backgroundColor: 'rgba(80,250,123,0.1)',
                fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2
            }}]
        }},
        options: chartOpts('累計再生数', formatViews)
    }});

    // 月別投稿数
    const avgPosts = {sd.avg_monthly_posts};
    new Chart(document.getElementById('postingChart'), {{
        type: 'line',
        data: {{
            labels: timeline.map(t => t.month),
            datasets: [
                {{
                    label: '月間投稿数',
                    data: timeline.map(t => t.count),
                    borderColor: '#ff79c6',
                    backgroundColor: 'rgba(255,121,198,0.15)',
                    fill: true, tension: 0.3, pointRadius: 2, borderWidth: 2
                }},
                {{
                    label: '平均 (' + avgPosts + '本/月)',
                    data: Array(timeline.length).fill(avgPosts),
                    borderColor: '#6272a4',
                    borderDash: [6,4], borderWidth: 1.5, pointRadius: 0, fill: false
                }}
            ]
        }},
        options: chartOpts('投稿数', v => v + '本')
    }});

    // 月別再生数
    new Chart(document.getElementById('viewsChart'), {{
        type: 'bar',
        data: {{
            labels: timeline.map(t => t.month),
            datasets: [{{
                label: '月間再生数',
                data: timeline.map(t => t.views),
                backgroundColor: 'rgba(139,233,253,0.5)',
                borderColor: '#8be9fd', borderWidth: 1, borderRadius: 3
            }}]
        }},
        options: chartOpts('再生数', formatViews)
    }});
}}

function chartOpts(label, tickFmt) {{
    return {{
        responsive: true, maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ labels: {{ color: '#f8f8f2', font: {{ size: 12 }} }} }},
            tooltip: {{ callbacks: {{ label: ctx => label + ': ' + tickFmt(ctx.parsed.y) }} }}
        }},
        scales: {{
            x: {{ ticks: {{ color: '#6272a4', maxRotation: 45, autoSkip: true, maxTicksLimit: 24 }}, grid: {{ color: 'rgba(98,114,164,0.15)' }} }},
            y: {{ beginAtZero: true, ticks: {{ color: '#6272a4', callback: v => tickFmt(v) }}, grid: {{ color: 'rgba(98,114,164,0.15)' }} }}
        }}
    }};
}}

function formatViews(v) {{
    if (v >= 1e8) return (v/1e8).toFixed(1) + '億';
    if (v >= 1e4) return (v/1e4).toFixed(1) + '万';
    return v.toLocaleString();
}}

function fmtNum(n) {{
    if (n >= 1e8) return (n/1e8).toFixed(1) + '億';
    if (n >= 1e4) return (n/1e4).toFixed(1) + '万';
    return n.toLocaleString();
}}

// ── 動画テーブル ──
function renderVideoTable() {{
    const tbody = document.getElementById('videoTableBody');
    let html = '';
    displayedVideos.forEach((v, i) => {{
        html += `<tr>
            <td style="color:#6272a4">${{i+1}}</td>
            <td><a href="${{v.url}}" target="_blank" class="video-title">${{escHtml(v.title || v.description || '(なし)')}}</a></td>
            <td class="num">${{fmtNum(v.views)}}</td>
            <td class="num">${{fmtNum(v.likes)}}</td>
            <td class="num">${{fmtNum(v.comments)}}</td>
            <td class="num">${{fmtNum(v.shares)}}</td>
            <td class="date-col">${{v.date}}</td>
        </tr>`;
    }});
    tbody.innerHTML = html;
    document.getElementById('videoCountDisplay').textContent = `表示: ${{displayedVideos.length}} / ${{allVideos.length}} 本`;
}}

function filterVideos() {{
    const q = document.getElementById('searchInput').value.toLowerCase();
    displayedVideos = allVideos.filter(v =>
        (v.title + ' ' + v.description).toLowerCase().includes(q)
    );
    applySortToDisplayed();
    renderVideoTable();
}}

function sortVideos() {{
    currentSort = document.getElementById('sortSelect').value;
    applySortToDisplayed();
    renderVideoTable();
}}

function sortBy(field) {{
    const current = currentSort.split('-');
    if (current[0] === field) {{
        currentSort = field + '-' + (current[1] === 'desc' ? 'asc' : 'desc');
    }} else {{
        currentSort = field + '-desc';
    }}
    document.getElementById('sortSelect').value = currentSort;
    applySortToDisplayed();
    renderVideoTable();
}}

function applySortToDisplayed() {{
    const [field, dir] = currentSort.split('-');
    const mult = dir === 'desc' ? -1 : 1;
    displayedVideos.sort((a, b) => {{
        let va = a[field], vb = b[field];
        if (field === 'date') {{ va = va || ''; vb = vb || ''; return va < vb ? -mult : va > vb ? mult : 0; }}
        return (va - vb) * mult;
    }});
}}

// ── TOP20 ──
function renderTop() {{
    let html = '<div style="display:grid;gap:1rem;">';
    topVideos.forEach((v, i) => {{
        const engRate = v.views > 0 ? ((v.likes + v.comments + v.shares) / v.views * 100).toFixed(2) : 0;
        html += `<div style="background:#1e1e2e;border:1px solid #3a3a4a;border-radius:8px;padding:1rem;display:flex;gap:1rem;align-items:flex-start;">
            <div style="color:#ff79c6;font-size:1.5rem;font-weight:700;min-width:40px;text-align:center;">${{i+1}}</div>
            <div style="flex:1;">
                <a href="${{v.url}}" target="_blank" style="font-weight:600;font-size:0.95rem;">${{escHtml(v.title || '(タイトルなし)')}}</a>
                <div style="display:flex;gap:1.5rem;margin-top:0.5rem;flex-wrap:wrap;font-size:0.85rem;">
                    <span style="color:#50fa7b;font-weight:600;">${{fmtNum(v.views)}}再生</span>
                    <span style="color:#ff79c6;">${{fmtNum(v.likes)}}いいね</span>
                    <span style="color:#8be9fd;">${{fmtNum(v.comments)}}コメント</span>
                    <span style="color:#ffb86c;">${{fmtNum(v.shares)}}シェア</span>
                    <span style="color:#6272a4;">ENG率: ${{engRate}}%</span>
                    <span style="color:#6272a4;">${{v.date}}</span>
                </div>
            </div>
        </div>`;
    }});
    html += '</div>';
    document.getElementById('topVideosList').innerHTML = html;
}}

// ── コピー ──
function cc(id, btn) {{
    navigator.clipboard.writeText(document.getElementById(id).textContent).then(() => {{
        btn.textContent = 'OK!'; btn.classList.add('copied');
        setTimeout(() => {{ btn.textContent = 'コピー'; btn.classList.remove('copied'); }}, 1500);
    }});
}}

function copyAllAsRow() {{
    const ids = ['sv-platform','sv-url','sv-followers','sv-views','sv-mviews','sv-mposts','sv-avgv','sv-trend','sv-first'];
    const row = ids.map(id => document.getElementById(id).textContent).join('\\t');
    navigator.clipboard.writeText(row).then(() => alert('コピーしました！\\nGoogle Sheetsにペーストしてください。'));
}}

function escHtml(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}

// ── 初期化 ──
document.addEventListener('DOMContentLoaded', () => {{
    applySortToDisplayed();
    renderVideoTable();
    renderTop();
}});
</script>
</body>
</html>"""

    Path(output_path).write_text(report_html, encoding="utf-8")
    return output_path


def main():
    if len(sys.argv) < 2:
        print("使い方: python generate_report.py <TikTokアカウントURL>")
        print("例: python generate_report.py https://www.tiktok.com/@misakism13")
        sys.exit(1)

    account_url = sys.argv[1]
    username = _parse_username(account_url)

    print(f"\n{'='*60}")
    print(f"  TikTok分析レポート生成ツール")
    print(f"  対象: @{username}")
    print(f"{'='*60}\n")

    # Step 1: 全動画取得
    print("[1/3] 動画メタデータ取得中...")
    videos = extract_account_videos(account_url)

    if not videos:
        print("エラー: 動画が見つかりませんでした。URLを確認してください。")
        sys.exit(1)

    print(f"  → {len(videos)}本の動画を取得\n")

    # Step 2: シートデータ算出
    print("[2/3] データ算出中...")
    sheet_data = compute_sheet_data(account_url, videos)
    print(f"  → 総再生数: {_format_number(sheet_data.total_views)}")
    print(f"  → 月間投稿: {sheet_data.monthly_posts}本")
    print(f"  → 平均月間投稿: {sheet_data.avg_monthly_posts}本/月\n")

    # Step 3: HTMLレポート生成
    print("[3/3] HTMLレポート生成中...")
    output = f"report_{username}.html"
    generate_html_report(account_url, videos, sheet_data, output)
    print(f"\n  ✓ 完了！レポートファイル: {output}")
    print(f"  → ブラウザで開いてください\n")


if __name__ == "__main__":
    main()
