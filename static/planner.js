let csvFileData = null;

// ===== ファイルアップロード =====
const uploadArea = document.getElementById('uploadArea');
const csvInput = document.getElementById('csvFile');

uploadArea.addEventListener('click', () => csvInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

csvInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
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
        document.getElementById('generateBtn').disabled = false;
        uploadArea.classList.add('hidden');
    };
    reader.readAsText(file, 'UTF-8');
}

function clearFile() {
    csvFileData = null;
    csvInput.value = '';
    document.getElementById('fileInfo').classList.add('hidden');
    document.getElementById('generateBtn').disabled = true;
    uploadArea.classList.remove('hidden');
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

// ===== 企画生成 =====
function generatePlans() {
    if (!csvFileData) {
        alert('CSVファイルをアップロードしてください');
        return;
    }

    const minViews = parseInt(document.getElementById('minViewsPlanner').value);
    const recentMonths = parseInt(document.getElementById('recentMonths').value);
    const maxPlans = parseInt(document.getElementById('maxPlans').value);

    document.getElementById('uploadSection').classList.add('hidden');
    document.getElementById('loadingSection').classList.remove('hidden');

    fetch('/api/planner/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            csv_content: csvFileData,
            min_views: minViews,
            recent_months: recentMonths,
            max_plans: maxPlans,
        }),
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('loadingSection').classList.add('hidden');
        if (data.error) {
            showPlannerError(data.error);
            return;
        }
        showPlannerResults(data);
    })
    .catch(() => {
        document.getElementById('loadingSection').classList.add('hidden');
        showPlannerError('サーバーに接続できません');
    });
}

function showPlannerError(message) {
    document.getElementById('errorSection').classList.remove('hidden');
    document.getElementById('plannerError').textContent = message;
}

function resetPlanner() {
    clearFile();
    document.getElementById('uploadSection').classList.remove('hidden');
    document.getElementById('loadingSection').classList.add('hidden');
    document.getElementById('errorSection').classList.add('hidden');
    document.getElementById('resultSection').classList.add('hidden');
}

// ===== 結果表示 =====
function showPlannerResults(data) {
    document.getElementById('resultSection').classList.remove('hidden');

    renderSummary(data.summary);
    renderPlans(data.plans);
    renderHookCandidates(data.summary.top_hooks);
    renderTopics(data.summary.topic_counts, data.summary.hook_type_counts);
}

function renderSummary(summary) {
    const el = document.getElementById('summaryCard');
    el.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${summary.total_scripts}</div>
                <div class="stat-label">CSV総数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${summary.viral_count}</div>
                <div class="stat-label">基準以上</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${summary.hook_count}</div>
                <div class="stat-label">フック候補（直近）</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${summary.content_count}</div>
                <div class="stat-label">コンテンツ候補</div>
            </div>
        </div>
    `;
}

function renderPlans(plans) {
    const el = document.getElementById('plansList');
    if (!plans || !plans.length) {
        el.innerHTML = '<div class="empty-state"><p>生成できる企画がありませんでした。</p><p>CSVにもっと多くの台本データを追加するか、フィルタ条件を緩めてみてください。</p></div>';
        return;
    }

    el.innerHTML = plans.map((plan, i) => `
        <div class="plan-card" id="plan-${i}">
            <div class="plan-header" onclick="togglePlan(${i})">
                <div class="plan-number">${plan.plan_number}</div>
                <div class="plan-title-area">
                    <div class="plan-hook-preview">「${escapeHtml(plan.hook_text)}」</div>
                    <div class="plan-meta">
                        <span class="badge badge-topic">${escapeHtml(plan.topic)}</span>
                        <span class="badge badge-hook-type">${escapeHtml(plan.hook_type)}</span>
                    </div>
                </div>
                <span class="expand-icon">&#9660;</span>
            </div>
            <div class="plan-body" id="plan-body-${i}">
                <!-- フック元ネタ -->
                <div class="source-block">
                    <h4>冒頭訴求の元ネタ</h4>
                    <div class="source-info">
                        <span class="source-views">${formatNumber(plan.hook_source.views)}再生</span>
                        <span class="source-date">${escapeHtml(plan.hook_source.date)}</span>
                        ${plan.hook_source.url ? `<a href="${escapeHtml(plan.hook_source.url)}" target="_blank" rel="noopener" class="source-link">元動画 ↗</a>` : ''}
                    </div>
                    <div class="source-transcript">「${escapeHtml(plan.hook_source.full_hook)}」</div>
                </div>

                <!-- コンテンツ元ネタ -->
                ${plan.content_sources.map(src => `
                    <div class="source-block">
                        <h4>ハウツー内容の元ネタ</h4>
                        <div class="source-info">
                            <span class="source-views">${formatNumber(src.views)}再生</span>
                            <span class="source-date">${escapeHtml(src.date || '')}</span>
                            ${src.url ? `<a href="${escapeHtml(src.url)}" target="_blank" rel="noopener" class="source-link">元動画 ↗</a>` : ''}
                        </div>
                        ${src.topics ? `<div class="source-topics">${src.topics.map(t => `<span class="badge badge-topic">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
                    </div>
                `).join('')}

                <!-- 台本構成 -->
                <div class="script-block">
                    <h4>企画台本</h4>
                    <div class="script-structure">
                        <div class="script-section script-hook">
                            <div class="script-label">冒頭 0-5秒</div>
                            <div class="script-text">${escapeHtml(plan.structure.hook || '')}</div>
                        </div>
                        <div class="script-section script-bridge">
                            <div class="script-label">つなぎ 5-10秒</div>
                            <div class="script-text">${escapeHtml(plan.structure.bridge || '')}</div>
                        </div>
                        <div class="script-section script-body">
                            <div class="script-label">本題</div>
                            <div class="script-text">${escapeHtml(plan.content_summary || '')}</div>
                        </div>
                        <div class="script-section script-cta">
                            <div class="script-label">締め</div>
                            <div class="script-text">${escapeHtml(plan.structure.cta || '')}</div>
                        </div>
                    </div>
                </div>

                <!-- フル台本コピー -->
                <div class="script-full">
                    <div class="script-full-header">
                        <h4>台本全文</h4>
                        <button class="btn-copy" onclick="copyScript(${i})">コピー</button>
                    </div>
                    <pre class="script-full-text" id="script-text-${i}">${escapeHtml(plan.full_script)}</pre>
                </div>
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
                    <span class="hook-views">${formatNumber(h.views)}再生</span>
                    <span class="badge badge-hook-type">${escapeHtml(h.type)}</span>
                    <span class="hook-date">${escapeHtml(h.date)}</span>
                </div>
                <div class="hook-text">「${escapeHtml(h.text)}」</div>
                ${h.url ? `<a href="${escapeHtml(h.url)}" target="_blank" rel="noopener" class="source-link" style="font-size:.8rem;margin-top:.3rem;display:inline-block">元動画 ↗</a>` : ''}
            </div>
        `).join('');
}

function renderTopics(topicCounts, hookTypeCounts) {
    const el = document.getElementById('topicsAnalysis');
    let html = '';

    // トピック分布
    if (topicCounts && Object.keys(topicCounts).length) {
        const max = Math.max(...Object.values(topicCounts), 1);
        html += '<div class="card"><h3 class="section-subtitle">肌悩みトピック分布</h3>';
        const sorted = Object.entries(topicCounts).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([name, count]) => {
            const pct = (count / max) * 100;
            html += `<div class="duration-row">
                <span class="duration-label" style="width:140px;text-align:left">${escapeHtml(name)}</span>
                <div class="duration-bar-bg">
                    <div class="duration-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,#0891b2,#22d3ee)">${count}本</div>
                </div>
            </div>`;
        });
        html += '</div>';
    }

    // フックタイプ分布
    if (hookTypeCounts && Object.keys(hookTypeCounts).length) {
        const max = Math.max(...Object.values(hookTypeCounts), 1);
        html += '<div class="card" style="margin-top:1.5rem"><h3 class="section-subtitle">フックタイプ分布（直近フック候補）</h3>';
        const sorted = Object.entries(hookTypeCounts).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([name, count]) => {
            const pct = (count / max) * 100;
            html += `<div class="duration-row">
                <span class="duration-label" style="width:140px;text-align:left">${escapeHtml(name)}</span>
                <div class="duration-bar-bg">
                    <div class="duration-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,#7c3aed,#a78bfa)">${count}本</div>
                </div>
            </div>`;
        });
        html += '</div>';
    }

    el.innerHTML = html || '<div class="empty-state"><p>トピックデータがありません。</p></div>';
}

// ===== UI操作 =====
function togglePlan(index) {
    const card = document.getElementById(`plan-${index}`);
    const body = document.getElementById(`plan-body-${index}`);
    card.classList.toggle('open');
    body.classList.toggle('open');
}

function copyScript(index) {
    const text = document.getElementById(`script-text-${index}`).textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        btn.textContent = 'コピー済み!';
        setTimeout(() => { btn.textContent = 'コピー'; }, 2000);
    });
}

function switchPlannerTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(`ptab-${name}`).classList.add('active');
}

// ===== ユーティリティ =====
function formatNumber(num) {
    if (typeof num === 'string') return num;
    if (!num) return '0';
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
