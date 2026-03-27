let csvFileData = null;
let currentJobId = null;
let pollTimer = null;

// ===== キーワード入力 =====
function setKeyword(kw) {
    document.getElementById('searchKeyword').value = kw;
}

document.getElementById('searchKeyword').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startResearch();
});

// ===== ファイルアップロード =====
const uploadArea = document.getElementById('uploadArea');
const csvInput = document.getElementById('csvFile');

uploadArea.addEventListener('click', () => csvInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
csvInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFile(e.target.files[0]);
});

function handleFile(file) {
    if (!file.name.match(/\.(csv|tsv|txt)$/i)) {
        alert('CSV/TSV/TXTファイルを選択してください');
        return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
        csvFileData = e.target.result;
        document.getElementById('fileInfo').classList.remove('hidden');
        document.getElementById('fileName').textContent = `${file.name} (${formatFileSize(file.size)})`;
        uploadArea.classList.add('hidden');
    };
    reader.readAsText(file, 'UTF-8');
}

function clearFile() {
    csvFileData = null;
    csvInput.value = '';
    document.getElementById('fileInfo').classList.add('hidden');
    uploadArea.classList.remove('hidden');
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ===== リサーチ開始 =====
function startResearch() {
    const keyword = document.getElementById('searchKeyword').value.trim();
    if (!keyword) {
        alert('検索キーワードを入力してください');
        return;
    }

    const params = {
        keyword: keyword,
        min_views: parseInt(document.getElementById('minViews').value),
        hook_period_months: parseInt(document.getElementById('hookPeriod').value),
        search_period_months: parseInt(document.getElementById('searchPeriod').value),
        max_plans: parseInt(document.getElementById('maxPlans').value),
        csv_content: csvFileData || "",
    };

    document.getElementById('inputSection').classList.add('hidden');
    document.getElementById('loadingSection').classList.remove('hidden');
    updateResearchStep('rs1', 'active');

    fetch('/api/planner/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showPlannerError(data.error);
            return;
        }
        currentJobId = data.job_id;
        pollTimer = setInterval(pollResearchStatus, 2000);
    })
    .catch(() => showPlannerError('サーバーに接続できません'));
}

function pollResearchStatus() {
    if (!currentJobId) return;
    fetch(`/api/planner/status/${currentJobId}`)
        .then(res => res.json())
        .then(job => {
            updateResearchProgress(job);
            if (job.status === 'completed') {
                clearInterval(pollTimer);
                document.getElementById('loadingSection').classList.add('hidden');
                showPlannerResults(job.result);
            } else if (job.status === 'error') {
                clearInterval(pollTimer);
                showPlannerError(job.message);
            }
        })
        .catch(() => {});
}

function updateResearchProgress(job) {
    document.getElementById('researchMessage').textContent = job.message || '';

    const stageMap = {
        'searching': ['rs1', 25],
        'transcribing': ['rs2', 50],
        'analyzing': ['rs3', 75],
        'generating': ['rs4', 90],
        'completed': ['rs4', 100],
    };

    const [activeStep, pct] = stageMap[job.status] || ['rs1', 10];
    document.getElementById('researchProgressBar').style.width = `${pct}%`;

    // ステップ状態更新
    const steps = ['rs1', 'rs2', 'rs3', 'rs4'];
    const activeIdx = steps.indexOf(activeStep);
    steps.forEach((s, i) => {
        const el = document.getElementById(s);
        if (i < activeIdx) el.dataset.status = 'done';
        else if (i === activeIdx) el.dataset.status = job.status === 'completed' ? 'done' : 'active';
        else el.dataset.status = 'waiting';
    });

    // 文字起こし進捗
    if (job.status === 'transcribing' && job.total > 0) {
        document.getElementById('researchProgressBar').style.width =
            `${25 + (job.progress / job.total) * 25}%`;
    }
}

function updateResearchStep(stepId, status) {
    document.getElementById(stepId).dataset.status = status;
}

// ===== エラー / リセット =====
function showPlannerError(message) {
    document.getElementById('loadingSection').classList.add('hidden');
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('plannerError').textContent = message;
}

function resetPlanner() {
    currentJobId = null;
    if (pollTimer) clearInterval(pollTimer);
    document.getElementById('inputSection').classList.remove('hidden');
    document.getElementById('loadingSection').classList.add('hidden');
    document.getElementById('errorSection').classList.add('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    ['rs1','rs2','rs3','rs4'].forEach(s => document.getElementById(s).dataset.status = 'waiting');
    document.getElementById('researchProgressBar').style.width = '0%';
}

// ===== 結果表示 =====
function showPlannerResults(data) {
    document.getElementById('resultSection').classList.remove('hidden');
    renderSummary(data.summary);
    renderPlans(data.plans);
    renderResearchedVideos(data.summary.all_videos || []);
    renderHookCandidates(data.summary.top_hooks);
    renderTopics(data.summary.topic_counts, data.summary.hook_type_counts);
}

function renderSummary(s) {
    document.getElementById('summaryCard').innerHTML = `
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value">${s.total_videos}</div><div class="stat-label">リサーチ動画数</div></div>
            <div class="stat-card"><div class="stat-value">${s.hook_count}</div><div class="stat-label">フック候補（直近）</div></div>
            <div class="stat-card"><div class="stat-value">${s.content_count}</div><div class="stat-label">コンテンツ候補</div></div>
            <div class="stat-card"><div class="stat-value">${Object.keys(s.topic_counts || {}).length}</div><div class="stat-label">検出トピック数</div></div>
        </div>`;
}

function renderPlans(plans) {
    const el = document.getElementById('plansList');
    if (!plans || !plans.length) {
        el.innerHTML = '<div class="empty-state"><p>生成できる企画がありませんでした。</p><p>キーワードを変えるか、フィルタ条件を緩めてみてください。</p></div>';
        return;
    }

    el.innerHTML = plans.map((plan, i) => `
        <div class="plan-card" id="plan-${i}">
            <div class="plan-header" onclick="togglePlan(${i})">
                <div class="plan-number">${plan.plan_number}</div>
                <div class="plan-title-area">
                    <div class="plan-hook-preview">「${esc(plan.hook_text)}」</div>
                    <div class="plan-meta">
                        <span class="badge badge-topic">${esc(plan.topic)}</span>
                        <span class="badge badge-hook-type">${esc(plan.hook_type)}</span>
                    </div>
                </div>
                <span class="expand-icon">&#9660;</span>
            </div>
            <div class="plan-body" id="plan-body-${i}">
                <div class="source-block">
                    <h4>冒頭訴求の元ネタ</h4>
                    <div class="source-info">
                        <span class="source-views">${fmtNum(plan.hook_source.views)}再生</span>
                        <span class="source-date">${esc(plan.hook_source.date)}</span>
                        ${plan.hook_source.account_name ? `<a href="#" class="account-link" onclick="showAccount('${esc(plan.hook_source.account_url)}', event)">@${esc(plan.hook_source.account_name)}</a>` : ''}
                        ${plan.hook_source.url ? `<a href="${esc(plan.hook_source.url)}" target="_blank" rel="noopener" class="source-link">元動画 ↗</a>` : ''}
                    </div>
                    <div class="source-transcript">「${esc(plan.hook_source.full_hook)}」</div>
                </div>

                ${(plan.content_sources || []).map(src => `
                    <div class="source-block">
                        <h4>ハウツー内容の元ネタ</h4>
                        <div class="source-info">
                            <span class="source-views">${fmtNum(src.views)}再生</span>
                            <span class="source-date">${esc(src.date || '')}</span>
                            ${src.account_name ? `<a href="#" class="account-link" onclick="showAccount('${esc(src.account_url)}', event)">@${esc(src.account_name)}</a>` : ''}
                            ${src.url ? `<a href="${esc(src.url)}" target="_blank" rel="noopener" class="source-link">元動画 ↗</a>` : ''}
                        </div>
                        ${src.topics ? `<div class="source-topics">${src.topics.map(t => `<span class="badge badge-topic">${esc(t)}</span>`).join('')}</div>` : ''}
                    </div>
                `).join('')}

                <div class="script-block">
                    <h4>企画台本</h4>
                    <div class="script-structure">
                        <div class="script-section script-hook"><div class="script-label">冒頭 0-5秒</div><div class="script-text">${esc(plan.structure.hook || '')}</div></div>
                        <div class="script-section script-bridge"><div class="script-label">つなぎ 5-10秒</div><div class="script-text">${esc(plan.structure.bridge || '')}</div></div>
                        <div class="script-section script-body"><div class="script-label">本題</div><div class="script-text">${esc(plan.content_summary || '')}</div></div>
                        <div class="script-section script-cta"><div class="script-label">締め</div><div class="script-text">${esc(plan.structure.cta || '')}</div></div>
                    </div>
                </div>

                <div class="script-full">
                    <div class="script-full-header">
                        <h4>台本全文</h4>
                        <button class="btn-copy" onclick="copyScript(${i})">コピー</button>
                    </div>
                    <pre class="script-full-text" id="script-text-${i}">${esc(plan.full_script)}</pre>
                </div>
            </div>
        </div>
    `).join('');
}

function renderResearchedVideos(videos) {
    const el = document.getElementById('researchedVideos');
    if (!videos || !videos.length) {
        el.innerHTML = '<div class="empty-state"><p>リサーチ動画がありません。</p></div>';
        return;
    }

    el.innerHTML = '<h3 class="section-subtitle">リサーチで取得した動画一覧</h3>' +
        videos.map((v, i) => `
            <div class="video-card" id="rv-${i}">
                <div class="video-header" onclick="toggleResearchVideo(${i})">
                    <div class="video-info">
                        <strong>${esc(v.title || v.hook_text || '(タイトルなし)')}</strong>
                        <div class="video-meta">
                            <span class="video-views">${fmtNum(v.views)}再生</span>
                            <span>${v.duration}秒</span>
                            <span>${esc(v.upload_date)}</span>
                            ${v.account_name ? `<a href="#" class="account-link" onclick="showAccount('${esc(v.account_url)}', event)">@${esc(v.account_name)}</a>` : ''}
                        </div>
                        <div style="margin-top:.3rem">
                            ${(v.topics || []).map(t => `<span class="badge badge-topic">${esc(t)}</span>`).join('')}
                            <span class="badge badge-hook-type">${esc(v.hook_type)}</span>
                            ${v.has_transcript ? '<span class="badge" style="background:rgba(52,211,153,.15);color:var(--green)">文字起こし済</span>' : ''}
                        </div>
                    </div>
                    <span class="expand-icon">&#9660;</span>
                </div>
                <div class="video-body" id="rv-body-${i}">
                    ${v.url ? `<a href="${esc(v.url)}" target="_blank" rel="noopener" class="video-link">TikTokで開く ↗</a>` : ''}
                    ${v.transcript ? `<div class="video-transcript">${esc(v.transcript)}</div>` : '<p style="color:var(--text-dim);font-size:.85rem">（文字起こしなし）</p>'}
                </div>
            </div>
        `).join('');
}

function renderHookCandidates(hooks) {
    const el = document.getElementById('hooksCandidates');
    if (!hooks || !hooks.length) {
        el.innerHTML = '<div class="empty-state"><p>直近期間のフック候補がありません。</p></div>';
        return;
    }

    el.innerHTML = '<h3 class="section-subtitle">直近の高再生フック一覧（冒頭30文字）</h3>' +
        hooks.map(h => `
            <div class="hook-card">
                <div class="hook-header">
                    <span class="hook-views">${fmtNum(h.views)}再生</span>
                    <span class="badge badge-hook-type">${esc(h.type)}</span>
                    <span class="hook-date">${esc(h.date)}</span>
                    ${h.account_name ? `<a href="#" class="account-link" onclick="showAccount('${esc(h.account_url)}', event)">@${esc(h.account_name)}</a>` : ''}
                </div>
                <div class="hook-text">「${esc(h.text)}」</div>
                ${h.url ? `<a href="${esc(h.url)}" target="_blank" rel="noopener" class="source-link" style="font-size:.8rem;margin-top:.3rem;display:inline-block">元動画 ↗</a>` : ''}
            </div>
        `).join('');
}

function renderTopics(topicCounts, hookTypeCounts) {
    const el = document.getElementById('topicsAnalysis');
    let html = '';

    if (topicCounts && Object.keys(topicCounts).length) {
        const max = Math.max(...Object.values(topicCounts), 1);
        html += '<div class="card"><h3 class="section-subtitle">肌悩みトピック分布</h3>';
        Object.entries(topicCounts).sort((a,b) => b[1]-a[1]).forEach(([name, count]) => {
            html += `<div class="duration-row"><span class="duration-label" style="width:140px;text-align:left">${esc(name)}</span><div class="duration-bar-bg"><div class="duration-bar-fill" style="width:${(count/max)*100}%;background:linear-gradient(90deg,#0891b2,#22d3ee)">${count}本</div></div></div>`;
        });
        html += '</div>';
    }

    if (hookTypeCounts && Object.keys(hookTypeCounts).length) {
        const max = Math.max(...Object.values(hookTypeCounts), 1);
        html += '<div class="card" style="margin-top:1.5rem"><h3 class="section-subtitle">フックタイプ分布</h3>';
        Object.entries(hookTypeCounts).sort((a,b) => b[1]-a[1]).forEach(([name, count]) => {
            html += `<div class="duration-row"><span class="duration-label" style="width:140px;text-align:left">${esc(name)}</span><div class="duration-bar-bg"><div class="duration-bar-fill" style="width:${(count/max)*100}%;background:linear-gradient(90deg,#7c3aed,#a78bfa)">${count}本</div></div></div>`;
        });
        html += '</div>';
    }

    el.innerHTML = html || '<div class="empty-state"><p>トピックデータがありません。</p></div>';
}

// ===== アカウント情報モーダル =====
function showAccount(accountUrl, event) {
    if (event) event.preventDefault();
    if (!accountUrl) return;

    const modal = document.getElementById('accountModal');
    const content = document.getElementById('accountContent');
    modal.classList.remove('hidden');
    content.innerHTML = '<div class="spinner" style="margin:2rem auto"></div><p style="text-align:center;color:var(--text-dim)">アカウント情報を取得中...</p>';

    fetch('/api/planner/account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_url: accountUrl }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            content.innerHTML = `<p style="color:var(--accent)">${esc(data.error)}</p>`;
            return;
        }
        const a = data.account;
        content.innerHTML = `
            <div class="account-header">
                ${a.avatar ? `<img src="${esc(a.avatar)}" class="account-avatar">` : '<div class="account-avatar-placeholder"></div>'}
                <div>
                    <h3 class="account-display-name">${esc(a.display_name || a.username)}</h3>
                    <a href="${esc(a.url)}" target="_blank" rel="noopener" class="account-username">@${esc(a.username)} ↗</a>
                </div>
            </div>
            ${a.bio ? `<p class="account-bio">${esc(a.bio)}</p>` : ''}
            <div class="account-stats-grid">
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.follower_count)}</div><div class="account-stat-label">フォロワー</div></div>
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.following_count)}</div><div class="account-stat-label">フォロー中</div></div>
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.like_count)}</div><div class="account-stat-label">いいね</div></div>
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.video_count)}</div><div class="account-stat-label">動画数</div></div>
            </div>
            ${a.recent_month_views ? `<div class="account-extra"><span>直近1ヶ月の再生数:</span> <strong>${fmtNum(a.recent_month_views)}</strong></div>` : ''}
            ${a.first_post_date ? `<div class="account-extra"><span>初投稿:</span> <strong>${esc(a.first_post_date)}</strong></div>` : ''}
        `;
    })
    .catch(() => {
        content.innerHTML = '<p style="color:var(--accent)">取得に失敗しました</p>';
    });
}

function closeAccountModal(event) {
    if (event && event.target !== document.getElementById('accountModal')) return;
    document.getElementById('accountModal').classList.add('hidden');
}

// ===== UI操作 =====
function togglePlan(i) {
    document.getElementById(`plan-${i}`).classList.toggle('open');
    document.getElementById(`plan-body-${i}`).classList.toggle('open');
}

function toggleResearchVideo(i) {
    document.getElementById(`rv-${i}`).classList.toggle('open');
    document.getElementById(`rv-body-${i}`).classList.toggle('open');
}

function copyScript(i) {
    const text = document.getElementById(`script-text-${i}`).textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        btn.textContent = 'コピー済み!';
        setTimeout(() => btn.textContent = 'コピー', 2000);
    });
}

function switchPlannerTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(`ptab-${name}`).classList.add('active');
}

// ===== ユーティリティ =====
function fmtNum(num) {
    if (typeof num === 'string') return num;
    if (!num) return '0';
    if (num >= 100000000) return (num / 100000000).toFixed(1) + '億';
    if (num >= 10000) return (num / 10000).toFixed(1) + '万';
    return num.toLocaleString();
}

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
