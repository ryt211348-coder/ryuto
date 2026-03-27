let currentJobId = null;
let pollInterval = null;

function startAnalysis() {
    const url = document.getElementById('accountUrl').value.trim();
    if (!url) {
        alert('TikTokアカウントのURLを入力してください');
        return;
    }

    const minViews = document.getElementById('minViews').value;
    const whisperModel = document.getElementById('whisperModel').value;

    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('inputSection').classList.add('hidden');
    document.getElementById('progressSection').classList.remove('hidden');
    document.getElementById('cancelBtn').classList.remove('hidden');

    fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            account_url: url,
            min_views: parseInt(minViews),
            whisper_model: whisperModel,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            return;
        }
        currentJobId = data.job_id;
        pollInterval = setInterval(pollStatus, 1500);
    })
    .catch(() => showError('サーバーに接続できません'));
}

function pollStatus() {
    if (!currentJobId) return;

    fetch(`/api/status/${currentJobId}`)
        .then(res => res.json())
        .then(job => {
            updateProgress(job);

            if (job.status === 'completed') {
                clearInterval(pollInterval);
                showResults(job.result);
            } else if (job.status === 'error') {
                clearInterval(pollInterval);
                showError(job.message);
            } else if (job.status === 'no_results') {
                clearInterval(pollInterval);
                showNoResults(job);
            }
        })
        .catch(() => {});
}

function updateProgress(job) {
    const msg = document.getElementById('progressMessage');
    const bar = document.getElementById('progressBar');
    msg.textContent = job.message || '';

    // ステップ更新
    const statusMap = {
        'queued':       [0, 0],
        'fetching':     [1, 0],
        'filtering':    [1, 1],
        'downloading':  [2, 1],
        'transcribing': [3, 2],
        'analyzing':    [4, 3],
        'completed':    [4, 4],
    };

    const [active, done] = statusMap[job.status] || [0, 0];
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`step${i}`);
        if (i <= done) step.dataset.status = 'done';
        else if (i === active) step.dataset.status = 'active';
        else step.dataset.status = 'waiting';
    }

    // プログレスバー
    if (job.total > 0 && job.progress !== undefined) {
        bar.style.width = `${(job.progress / job.total) * 100}%`;
    } else {
        const baseProgress = { queued: 5, fetching: 15, filtering: 30, downloading: 45, transcribing: 65, analyzing: 85, completed: 100 };
        bar.style.width = `${baseProgress[job.status] || 0}%`;
    }
}

function showError(message) {
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
}

function showNoResults(job) {
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = job.message;

    if (job.top_videos && job.top_videos.length) {
        const container = document.getElementById('topVideos');
        let html = '<p style="color:var(--text-dim);margin:1rem 0 0.5rem">再生数上位の動画:</p>';
        job.top_videos.forEach((v, i) => {
            html += `<p style="color:var(--text-dim);font-size:0.85rem">${i + 1}. ${formatNumber(v.views)}再生 - ${v.title || '(タイトルなし)'}</p>`;
        });
        container.innerHTML = html;
    }
}

function showResults(result) {
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('resultSection').classList.remove('hidden');

    renderStats(result.stats);
    renderFormats(result.content_formats, result.top_insights);
    renderDurationChart(result.duration_dist);
    renderAppeals(result.appeal_types, result.emotional_triggers);
    renderHookRates(result.hook_technique_rates);
    renderStructure(result.structure_patterns);
    renderHooks(result.hooks);
    renderProducts(result.product_mentions);
    renderPhrases(result.phrases);
    renderVideos(result.videos);
}

function renderStats(stats) {
    const grid = document.getElementById('statsGrid');
    const items = [
        { value: stats.total, label: '分析動画数', suffix: '本' },
        { value: formatNumber(Math.round(stats.avg_views)), label: '平均再生数', suffix: '' },
        { value: formatNumber(Math.round(stats.avg_likes)), label: '平均いいね', suffix: '' },
        { value: Math.round(stats.avg_duration), label: '平均動画長', suffix: '秒' },
        { value: Math.round(stats.avg_script_length), label: '平均台本文字数', suffix: '字' },
    ];

    grid.innerHTML = items.map(item =>
        `<div class="stat-card">
            <div class="stat-value">${item.value}${item.suffix}</div>
            <div class="stat-label">${item.label}</div>
        </div>`
    ).join('');
}

function renderBarChart(containerId, title, items, colorStart, colorEnd) {
    const container = document.getElementById(containerId);
    if (!items || !items.length) { container.innerHTML = ''; return; }
    const max = Math.max(...items.map(i => i.count), 1);
    let html = `<div class="card"><h3 style="font-size:.95rem;color:var(--text);margin-bottom:1rem">${title}</h3>`;
    items.forEach((item, idx) => {
        const pct = (item.count / max) * 100;
        html += `<div class="duration-row">
            <span class="duration-label" style="width:140px;text-align:left">${item.name}</span>
            <div class="duration-bar-bg">
                <div class="duration-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${colorStart},${colorEnd})">${item.count}本</div>
            </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function renderFormats(formats, insights) {
    renderBarChart('formatsChart', '企画フォーマット（どんな形式の動画が伸びているか）', formats, 'var(--accent)', 'var(--purple)');

    const container = document.getElementById('topInsights');
    if (!insights || !insights.length) { container.innerHTML = ''; return; }
    let html = '<div class="card" style="margin-top:1rem"><h3 style="font-size:.95rem;color:var(--text);margin-bottom:.75rem">再生数TOP5の動画に共通する特徴</h3>';
    insights.forEach(insight => {
        html += `<p style="color:var(--cyan);font-weight:600;margin-bottom:.3rem">${insight.label}</p>`;
        if (insight.items && insight.items.length) {
            insight.items.forEach(([name, count]) => {
                html += `<span class="badge badge-keyword" style="margin-right:.4rem;margin-bottom:.3rem;display:inline-block;padding:.2rem .6rem">${name} (${count}本)</span>`;
            });
        }
        html += '<br style="margin-bottom:.5rem">';
    });
    html += '</div>';
    container.innerHTML = html;
}

function renderAppeals(appeals, emotions) {
    renderBarChart('appealsChart', '訴求パターン（どんな切り口で視聴者を惹きつけているか）', appeals, 'var(--cyan)', 'var(--green)');
    renderBarChart('emotionsChart', '感情トリガー（どの感情に訴えかけているか）', emotions, 'var(--yellow)', 'var(--accent)');
}

function renderHookRates(rates) {
    const container = document.getElementById('hookRates');
    if (!rates || !Object.keys(rates).length) { container.innerHTML = ''; return; }
    const colors = ['var(--yellow)', 'var(--cyan)', 'var(--accent)', 'var(--purple)', 'var(--green)'];
    let html = '<div class="card"><h3 style="font-size:.95rem;color:var(--text);margin-bottom:1rem">フック手法の使用率</h3><div class="patterns-grid">';
    Object.entries(rates).forEach(([name, value], i) => {
        const color = colors[i % colors.length];
        html += `<div class="pattern-card">
            <div class="pattern-name">${name}</div>
            <div class="pattern-bar-bg"><div class="pattern-bar-fill" style="width:${value*100}%;background:${color}"></div></div>
            <div class="pattern-value" style="color:${color}">${Math.round(value*100)}%</div>
        </div>`;
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderStructure(patterns) {
    renderBarChart('structureChart', '台本構成パターン', patterns, 'var(--purple)', 'var(--cyan)');
}

function renderProducts(products) {
    const container = document.getElementById('productsList');
    if (!products || !products.length) {
        container.innerHTML = '<p style="color:var(--dim)">商品・ブランド・ハッシュタグの言及なし</p>';
        return;
    }
    let html = '<div class="card"><h3 style="font-size:.95rem;color:var(--text);margin-bottom:1rem">よく登場する商品・ブランド・タグ</h3>';
    products.forEach(p => {
        html += `<span style="display:inline-block;background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:.3rem .8rem;margin:.2rem .3rem;font-size:.85rem">${escapeHtml(p.name)} <span style="color:var(--cyan);font-weight:600">${p.count}</span></span>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function renderDurationChart(dist) {
    const container = document.getElementById('durationChart');
    if (!dist || !Object.keys(dist).length) {
        container.innerHTML = '';
        return;
    }

    const max = Math.max(...Object.values(dist));
    let html = '<h3>動画長の分布</h3>';
    for (const [label, count] of Object.entries(dist)) {
        const pct = max > 0 ? (count / max) * 100 : 0;
        html += `
            <div class="duration-row">
                <span class="duration-label">${label}</span>
                <div class="duration-bar-bg">
                    <div class="duration-bar-fill" style="width:${pct}%">${count}本</div>
                </div>
            </div>`;
    }
    container.innerHTML = html;
}

function renderHooks(hooks) {
    const container = document.getElementById('hooksList');
    if (!hooks || !hooks.length) {
        container.innerHTML = '<p style="color:var(--text-dim)">フックデータがありません</p>';
        return;
    }

    container.innerHTML = '<h3 style="font-size:.95rem;color:var(--text);margin-bottom:1rem">冒頭フック例（再生数上位）</h3>' + hooks.map(h => {
        let badges = '';
        if (h.has_question) badges += '<span class="badge badge-question">疑問文</span>';
        if (h.has_negative) badges += '<span class="badge badge-negative">ネガティブ</span>';
        if (h.has_curiosity) badges += '<span class="badge badge-keyword">好奇心</span>';
        (h.formats || []).forEach(f => { badges += `<span class="badge" style="background:rgba(167,139,250,.15);color:var(--purple)">${f}</span>`; });
        (h.appeals || []).forEach(a => { badges += `<span class="badge" style="background:rgba(52,211,153,.15);color:var(--green)">${a}</span>`; });

        return `
            <div class="hook-card">
                <div class="hook-header">
                    <span class="hook-views">${formatNumber(h.views)}再生</span>
                    <div class="hook-badges">${badges}</div>
                </div>
                <div class="hook-text">「${escapeHtml(h.text)}」</div>
            </div>`;
    }).join('');
}

function renderPhrases(phrases) {
    const container = document.getElementById('phrasesList');
    if (!phrases || !phrases.length) {
        container.innerHTML = '<p style="color:var(--text-dim)">頻出フレーズがありません</p>';
        return;
    }

    container.innerHTML = phrases.map(p =>
        `<div class="phrase-row">
            <span class="phrase-count">${p.count}</span>
            <span class="phrase-text">${escapeHtml(p.phrase)}</span>
        </div>`
    ).join('');
}

function renderVideos(videos) {
    const container = document.getElementById('videosList');
    if (!videos || !videos.length) {
        container.innerHTML = '<p style="color:var(--text-dim)">動画データがありません</p>';
        return;
    }

    container.innerHTML = videos.map((v, i) =>
        `<div class="video-card" id="vc-${i}">
            <div class="video-header" onclick="toggleVideo(${i})">
                ${v.thumbnail ? `<img src="${escapeHtml(v.thumbnail)}" alt="" class="video-thumb">` : '<div class="video-thumb-placeholder"></div>'}
                <div class="video-info">
                    <strong>${escapeHtml(v.title || '(タイトルなし)')}</strong>
                    <div class="video-meta">
                        <span class="video-views">${formatNumber(v.views)}再生</span>
                        <span>${formatNumber(v.likes)}いいね</span>
                        <span>${v.duration}秒</span>
                    </div>
                </div>
                <span class="expand-icon">&#9660;</span>
            </div>
            <div class="video-body" id="vb-${i}">
                ${v.description ? `<p style="color:var(--text-dim);font-size:0.85rem;margin-bottom:0.5rem">${escapeHtml(v.description)}</p>` : ''}
                <a href="${escapeHtml(v.url)}" target="_blank" rel="noopener" class="video-link">TikTokで開く ↗</a>
                <div class="video-transcript">${v.transcript ? escapeHtml(v.transcript) : '（文字起こしなし）'}</div>
            </div>
        </div>`
    ).join('');
}

function toggleVideo(index) {
    const card = document.getElementById(`vc-${index}`);
    const body = document.getElementById(`vb-${index}`);
    card.classList.toggle('open');
    body.classList.toggle('open');
}

function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`tab-${name}`).classList.add('active');
}

function resetForm() {
    currentJobId = null;
    if (pollInterval) clearInterval(pollInterval);

    document.getElementById('inputSection').classList.remove('hidden');
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('errorSection').classList.add('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    document.getElementById('analyzeBtn').disabled = false;

    // リセットステップ
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`step${i}`).dataset.status = 'waiting';
    }
    document.getElementById('progressBar').style.width = '0%';
}

function formatNumber(num) {
    if (typeof num === 'string') return num;
    if (num >= 100000000) return (num / 100000000).toFixed(1) + '億';
    if (num >= 10000) return (num / 10000).toFixed(1) + '万';
    return num.toLocaleString();
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Enterキーで分析開始
document.getElementById('accountUrl').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startAnalysis();
});
