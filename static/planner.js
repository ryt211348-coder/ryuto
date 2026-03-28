let currentPlatform = 'tiktok';
let currentJobId = null;
let pollTimer = null;

// ===== プラットフォーム切り替え =====
function switchPlatform(platform) {
    currentPlatform = platform;
    document.querySelectorAll('.platform-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${platform}`).classList.add('active');
    document.getElementById('videoList').innerHTML = '';
    document.getElementById('resultSummary').classList.add('hidden');
}

// ===== 検索開始 =====
function startSearch() {
    const period = parseInt(document.getElementById('periodFilter').value);
    const minViews = parseInt(document.getElementById('minViewsFilter').value);
    const limit = parseInt(document.getElementById('limitFilter').value);

    document.getElementById('searchBtn').disabled = true;
    document.getElementById('searchStatus').classList.remove('hidden');
    document.getElementById('searchMessage').textContent = `${currentPlatform === 'tiktok' ? 'TikTok' : 'Instagram'}の美容動画を検索中...`;
    document.getElementById('videoList').innerHTML = '';
    document.getElementById('resultSummary').classList.add('hidden');

    fetch('/api/research/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            platform: currentPlatform,
            period_days: period,
            min_views: minViews,
            limit: limit,
        }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.job_id) {
            currentJobId = data.job_id;
            pollTimer = setInterval(pollSearch, 2000);
        } else if (data.error) {
            showSearchError(data.error);
        }
    })
    .catch(() => showSearchError('サーバーに接続できません'));
}

function pollSearch() {
    if (!currentJobId) return;
    fetch(`/api/research/status/${currentJobId}`)
        .then(r => r.json())
        .then(job => {
            document.getElementById('searchMessage').textContent = job.message || '検索中...';
            if (job.status === 'completed') {
                clearInterval(pollTimer);
                document.getElementById('searchStatus').classList.add('hidden');
                document.getElementById('searchBtn').disabled = false;
                showResults(job.result);
            } else if (job.status === 'error') {
                clearInterval(pollTimer);
                showSearchError(job.message);
            }
        }).catch(() => {});
}

function showSearchError(msg) {
    document.getElementById('searchStatus').classList.add('hidden');
    document.getElementById('searchBtn').disabled = false;
    document.getElementById('videoList').innerHTML = `<div class="empty-state"><p>${esc(msg)}</p></div>`;
}

// ===== 結果表示 =====
function showResults(result) {
    const videos = result.videos || [];
    const summary = result.summary || {};

    // サマリー
    const sumEl = document.getElementById('resultSummary');
    sumEl.classList.remove('hidden');
    sumEl.innerHTML = `
        <div class="summary-stat"><div class="summary-stat-value">${videos.length}</div><div class="summary-stat-label">動画数</div></div>
        <div class="summary-stat"><div class="summary-stat-value">${fmtNum(summary.total_views || 0)}</div><div class="summary-stat-label">合計再生数</div></div>
        <div class="summary-stat"><div class="summary-stat-value">${fmtNum(summary.avg_views || 0)}</div><div class="summary-stat-label">平均再生数</div></div>
        <div class="summary-stat"><div class="summary-stat-value">${summary.unique_accounts || 0}</div><div class="summary-stat-label">ユニークアカウント</div></div>
    `;

    // 動画リスト
    const listEl = document.getElementById('videoList');
    if (!videos.length) {
        listEl.innerHTML = '<div class="empty-state"><p>動画が見つかりませんでした。フィルタ条件を変更してください。</p></div>';
        return;
    }

    listEl.innerHTML = videos.map((v, i) => `
        <div class="video-row">
            <div class="video-rank ${i < 3 ? 'top3' : ''}">${i + 1}</div>
            ${v.thumbnail ? `<img src="${esc(v.thumbnail)}" class="video-thumb-small" loading="lazy">` : '<div class="video-thumb-small"></div>'}
            <div class="video-main">
                <div class="video-title-text">${esc(v.title || v.description || '(タイトルなし)')}</div>
                <div class="video-stats-row">
                    <span class="video-views-badge">${fmtNum(v.views)}再生</span>
                    <span>${fmtNum(v.likes)}いいね</span>
                    <span>${fmtNum(v.comments)}コメント</span>
                    <span>${v.duration || 0}秒</span>
                    <span>${esc(v.upload_date || '')}</span>
                    ${v.account_name ? `<a class="video-account-link" onclick="showAccount('${esc(v.account_url)}', '${esc(v.account_name)}', event)">@${esc(v.account_name)}</a>` : ''}
                </div>
            </div>
            ${v.url ? `<a href="${esc(v.url)}" target="_blank" rel="noopener" class="video-ext-link" title="動画を見る">↗</a>` : ''}
        </div>
    `).join('');
}

// ===== アカウント詳細モーダル =====
function showAccount(url, name, event) {
    if (event) event.preventDefault();
    if (!url && !name) return;
    const modal = document.getElementById('accountModal');
    const content = document.getElementById('accountContent');
    modal.classList.remove('hidden');
    content.innerHTML = '<div class="spinner" style="margin:2rem auto"></div><p style="text-align:center;color:var(--text-dim)">アカウント情報を取得中...</p>';

    fetch('/api/research/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_url: url, username: name }),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) { content.innerHTML = `<p style="color:var(--accent)">${esc(data.error)}</p>`; return; }
        const a = data.account;
        content.innerHTML = `
            <div class="acct-header">
                ${a.avatar ? `<img src="${esc(a.avatar)}" class="acct-avatar">` : ''}
                <div>
                    <div class="acct-name">${esc(a.display_name || a.username)}</div>
                    <a href="${esc(a.url)}" target="_blank" rel="noopener" class="acct-username">@${esc(a.username)} ↗</a>
                </div>
            </div>
            ${a.bio ? `<div class="acct-bio">${esc(a.bio)}</div>` : ''}
            <div class="acct-stats">
                <div class="acct-stat"><div class="acct-stat-val">${fmtNum(a.follower_count)}</div><div class="acct-stat-lbl">フォロワー</div></div>
                <div class="acct-stat"><div class="acct-stat-val">${fmtNum(a.following_count)}</div><div class="acct-stat-lbl">フォロー中</div></div>
                <div class="acct-stat"><div class="acct-stat-val">${fmtNum(a.like_count)}</div><div class="acct-stat-lbl">総いいね</div></div>
                <div class="acct-stat"><div class="acct-stat-val">${fmtNum(a.video_count)}</div><div class="acct-stat-lbl">動画数</div></div>
                <div class="acct-stat"><div class="acct-stat-val">${a.activity_months || '-'}ヶ月</div><div class="acct-stat-lbl">活動期間</div></div>
                <div class="acct-stat"><div class="acct-stat-val">${fmtNum(a.recent_month_views)}</div><div class="acct-stat-lbl">月間再生数</div></div>
            </div>
            ${a.first_post_date ? `<div class="acct-extra"><span>初投稿日:</span> <strong>${esc(a.first_post_date)}</strong></div>` : ''}
            ${a.is_personality_driven !== undefined ? `<div class="acct-extra"><span>タイプ:</span> <strong style="color:${a.is_personality_driven ? 'var(--yellow)' : 'var(--green)'}">${a.is_personality_driven ? '属人型' : 'コンテンツ型'}</strong> <span style="font-size:.75rem">${esc(a.personality_reason || '')}</span></div>` : ''}
            ${a.trending_products && a.trending_products.length ? `<div class="acct-extra"><span>トレンド商品:</span> ${a.trending_products.map(p => `<span style="display:inline-block;background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:.15rem .5rem;margin:.1rem .2rem;font-size:.75rem">${esc(p)}</span>`).join('')}</div>` : ''}
        `;
    }).catch(() => { content.innerHTML = '<p style="color:var(--accent)">取得に失敗しました</p>'; });
}

function closeModal(event) {
    if (event && event.target !== document.getElementById('accountModal')) return;
    document.getElementById('accountModal').classList.add('hidden');
}

// ===== ユーティリティ =====
function fmtNum(n) { if(typeof n==='string')return n; if(!n)return '0'; if(n>=1e8)return(n/1e8).toFixed(1)+'億'; if(n>=1e4)return(n/1e4).toFixed(1)+'万'; return n.toLocaleString(); }
function esc(s) { if(!s)return ''; const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
