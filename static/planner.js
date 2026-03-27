let currentJobId = null;
let pollTimer = null;
let selectedKeywords = new Set();

// ===== Step 1: トレンドキーワード自動発見 =====
function startDiscovery() {
    const params = {
        min_views: parseInt(document.getElementById('minViews').value),
        search_period_months: parseInt(document.getElementById('searchPeriod').value),
    };

    document.getElementById('inputSection').classList.add('hidden');
    document.getElementById('loadingSection').classList.remove('hidden');
    updateStep('rs1', 'active');
    document.getElementById('researchMessage').textContent = 'トレンドキーワードを自動発見中...';
    document.getElementById('researchProgressBar').style.width = '15%';

    fetch('/api/planner/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('loadingSection').classList.add('hidden');
        if (data.error) { showError(data.error); return; }
        showKeywordSelection(data.keywords);
    })
    .catch(() => showError('サーバーに接続できません'));
}

function showKeywordSelection(keywords) {
    const section = document.getElementById('keywordSection');
    section.classList.remove('hidden');
    const grid = document.getElementById('keywordGrid');

    if (!keywords || !keywords.length) {
        grid.innerHTML = '<div class="empty-state"><p>キーワードが見つかりませんでした。</p></div>';
        return;
    }

    grid.innerHTML = keywords.map((kw, i) => `
        <div class="keyword-card ${i < 3 ? 'recommended' : ''}" id="kw-${i}" onclick="toggleKeyword(${i}, '${esc(kw.keyword)}')">
            <div class="kw-header">
                <span class="kw-name">${esc(kw.keyword)}</span>
                ${i < 3 ? '<span class="badge" style="background:rgba(255,45,85,.15);color:var(--accent);font-size:.65rem">おすすめ</span>' : ''}
                <span class="kw-check" id="kw-check-${i}"></span>
            </div>
            <div class="kw-stats">
                <span>${fmtNum(kw.estimated_volume)}総再生</span>
                <span>${kw.video_count}本</span>
                <span>平均${fmtNum(kw.avg_views)}再生</span>
                <span>Eng ${kw.avg_engagement}%</span>
            </div>
            ${kw.sample_hooks && kw.sample_hooks.length ? `<div class="kw-hooks">${kw.sample_hooks.map(h => `<span class="kw-hook">「${esc(h)}」</span>`).join('')}</div>` : ''}
        </div>
    `).join('');

    // 上位3つを自動選択
    keywords.slice(0, 3).forEach((kw, i) => {
        selectedKeywords.add(kw.keyword);
        document.getElementById(`kw-${i}`).classList.add('selected');
        document.getElementById(`kw-check-${i}`).textContent = '✓';
    });
}

function toggleKeyword(index, keyword) {
    const el = document.getElementById(`kw-${index}`);
    const check = document.getElementById(`kw-check-${index}`);
    if (selectedKeywords.has(keyword)) {
        selectedKeywords.delete(keyword);
        el.classList.remove('selected');
        check.textContent = '';
    } else {
        selectedKeywords.add(keyword);
        el.classList.add('selected');
        check.textContent = '✓';
    }
}

// ===== Step 2: 選択したキーワードでリサーチ =====
function startResearchWithKeywords() {
    const custom = document.getElementById('customKeyword').value.trim();
    if (custom) selectedKeywords.add(custom);

    if (selectedKeywords.size === 0) { alert('キーワードを1つ以上選択してください'); return; }

    const params = {
        keywords: Array.from(selectedKeywords),
        min_views: parseInt(document.getElementById('minViews').value),
        hook_period_months: parseInt(document.getElementById('hookPeriod').value),
        search_period_months: parseInt(document.getElementById('searchPeriod').value),
        max_plans: parseInt(document.getElementById('maxPlans').value),
    };

    document.getElementById('keywordSection').classList.add('hidden');
    document.getElementById('loadingSection').classList.remove('hidden');
    updateStep('rs1', 'done');
    updateStep('rs2', 'active');
    document.getElementById('researchMessage').textContent = 'リサーチ開始中...';
    document.getElementById('researchProgressBar').style.width = '25%';

    fetch('/api/planner/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { showError(data.error); return; }
        currentJobId = data.job_id;
        pollTimer = setInterval(pollStatus, 2000);
    })
    .catch(() => showError('サーバーに接続できません'));
}

function pollStatus() {
    if (!currentJobId) return;
    fetch(`/api/planner/status/${currentJobId}`)
        .then(res => res.json())
        .then(job => {
            updateProgress(job);
            if (job.status === 'completed') {
                clearInterval(pollTimer);
                document.getElementById('loadingSection').classList.add('hidden');
                showResults(job.result);
            } else if (job.status === 'error') {
                clearInterval(pollTimer);
                showError(job.message);
            }
        }).catch(() => {});
}

function updateProgress(job) {
    document.getElementById('researchMessage').textContent = job.message || '';
    const map = { searching: ['rs2', 30], transcribing: ['rs3', 55], analyzing: ['rs4', 80], generating: ['rs4', 90], completed: ['rs4', 100] };
    const [step, pct] = map[job.status] || ['rs2', 25];
    document.getElementById('researchProgressBar').style.width = `${pct}%`;
    const steps = ['rs1','rs2','rs3','rs4'];
    const idx = steps.indexOf(step);
    steps.forEach((s,i) => {
        document.getElementById(s).dataset.status = i < idx ? 'done' : (i === idx ? (job.status === 'completed' ? 'done' : 'active') : 'waiting');
    });
    if (job.status === 'transcribing' && job.total > 0)
        document.getElementById('researchProgressBar').style.width = `${30 + (job.progress/job.total)*25}%`;
}

function updateStep(id, status) { document.getElementById(id).dataset.status = status; }

// ===== エラー / リセット =====
function showError(msg) { document.getElementById('loadingSection').classList.add('hidden'); document.getElementById('errorSection').classList.remove('hidden'); document.getElementById('plannerError').textContent = msg; }
function resetPlanner() {
    currentJobId = null; selectedKeywords.clear();
    if (pollTimer) clearInterval(pollTimer);
    ['inputSection'].forEach(s => document.getElementById(s).classList.remove('hidden'));
    ['loadingSection','errorSection','resultSection','keywordSection'].forEach(s => document.getElementById(s).classList.add('hidden'));
    ['rs1','rs2','rs3','rs4'].forEach(s => document.getElementById(s).dataset.status = 'waiting');
    document.getElementById('researchProgressBar').style.width = '0%';
}

// ===== 結果表示 =====
function showResults(data) {
    document.getElementById('resultSection').classList.remove('hidden');
    renderSummary(data.summary);
    renderPlans(data.plans);
    renderVideos(data.summary.all_videos || []);
    renderHooks(data.summary.top_hooks);
    renderTopics(data.summary.topic_counts, data.summary.hook_type_counts);
    renderReference(data.reference_style);
}

function renderSummary(s) {
    document.getElementById('summaryCard').innerHTML = `
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value">${s.total_videos}</div><div class="stat-label">リサーチ動画数</div></div>
            <div class="stat-card"><div class="stat-value">${s.hook_count}</div><div class="stat-label">フック候補（直近）</div></div>
            <div class="stat-card"><div class="stat-value">${s.content_count}</div><div class="stat-label">コンテンツ候補</div></div>
            <div class="stat-card"><div class="stat-value">${Object.keys(s.topic_counts||{}).length}</div><div class="stat-label">検出トピック</div></div>
        </div>`;
}

function renderPlans(plans) {
    const el = document.getElementById('plansList');
    if (!plans||!plans.length) { el.innerHTML = '<div class="empty-state"><p>生成できる企画がありませんでした。</p></div>'; return; }
    el.innerHTML = plans.map((p,i) => `
        <div class="plan-card" id="plan-${i}">
            <div class="plan-header" onclick="togglePlan(${i})">
                <div class="plan-number">${p.plan_number}</div>
                <div class="plan-title-area">
                    <div class="plan-hook-preview">「${esc(p.hook_text)}」</div>
                    <div class="plan-meta">
                        <span class="badge badge-topic">${esc(p.topic)}</span>
                        <span class="badge badge-hook-type">${esc(p.hook_type)}</span>
                    </div>
                </div>
                <span class="expand-icon">&#9660;</span>
            </div>
            <div class="plan-body" id="pb-${i}">
                <div class="source-block"><h4>冒頭訴求の元ネタ</h4>
                    <div class="source-info">
                        <span class="source-views">${fmtNum(p.hook_source.views)}再生</span>
                        <span class="source-date">${esc(p.hook_source.date)}</span>
                        ${p.hook_source.account_name?`<a href="#" class="account-link" onclick="showAccount('${esc(p.hook_source.account_url)}',event)">@${esc(p.hook_source.account_name)}</a>`:''}
                        ${p.hook_source.url?`<a href="${esc(p.hook_source.url)}" target="_blank" rel="noopener" class="source-link">元動画 ↗</a>`:''}
                    </div>
                    <div class="source-transcript">「${esc(p.hook_source.full_hook)}」</div>
                </div>
                ${(p.content_sources||[]).map(src => `
                    <div class="source-block"><h4>ハウツー内容の元ネタ</h4>
                        <div class="source-info">
                            <span class="source-views">${fmtNum(src.views)}再生</span>
                            ${src.account_name?`<a href="#" class="account-link" onclick="showAccount('${esc(src.account_url)}',event)">@${esc(src.account_name)}</a>`:''}
                            ${src.url?`<a href="${esc(src.url)}" target="_blank" rel="noopener" class="source-link">元動画 ↗</a>`:''}
                        </div>
                        ${src.topics?`<div class="source-topics">${src.topics.map(t=>`<span class="badge badge-topic">${esc(t)}</span>`).join('')}</div>`:''}
                    </div>`).join('')}
                <div class="script-block"><h4>企画台本</h4>
                    <div class="script-structure">
                        <div class="script-section script-hook"><div class="script-label">冒頭 0-5秒</div><div class="script-text">${esc(p.structure.hook||'')}</div></div>
                        <div class="script-section script-bridge"><div class="script-label">つなぎ 5-10秒</div><div class="script-text">${esc(p.structure.bridge||'')}</div></div>
                        <div class="script-section script-body"><div class="script-label">本題</div><div class="script-text">${esc(p.content_summary||'')}</div></div>
                        <div class="script-section script-cta"><div class="script-label">締め</div><div class="script-text">${esc(p.structure.cta||'')}</div></div>
                    </div>
                </div>
                <div class="script-full">
                    <div class="script-full-header"><h4>台本全文</h4><button class="btn-copy" onclick="copyScript(${i})">コピー</button></div>
                    <pre class="script-full-text" id="st-${i}">${esc(p.full_script)}</pre>
                </div>
            </div>
        </div>`).join('');
}

function renderVideos(videos) {
    const el = document.getElementById('researchedVideos');
    if (!videos||!videos.length) { el.innerHTML = '<div class="empty-state"><p>動画なし</p></div>'; return; }
    el.innerHTML = '<h3 class="section-subtitle">リサーチ動画一覧（エンゲージメント順）</h3>' +
        videos.map((v,i) => `
            <div class="video-card" id="rv-${i}">
                <div class="video-header" onclick="toggleRV(${i})">
                    <div class="video-info">
                        <strong>${esc(v.title||v.hook_text||'(タイトルなし)')}</strong>
                        <div class="video-meta">
                            <span class="video-views">${fmtNum(v.views)}再生</span>
                            <span>${fmtNum(v.likes)}いいね</span>
                            <span>${fmtNum(v.comments)}コメント</span>
                            <span>Eng ${v.engagement_rate}%</span>
                            ${v.account_name?`<a href="#" class="account-link" onclick="showAccount('${esc(v.account_url)}',event)">@${esc(v.account_name)}</a>`:''}
                        </div>
                        <div style="margin-top:.3rem">
                            ${(v.topics||[]).map(t=>`<span class="badge badge-topic">${esc(t)}</span>`).join('')}
                            <span class="badge badge-hook-type">${esc(v.hook_type)}</span>
                            ${v.has_transcript?'<span class="badge" style="background:rgba(52,211,153,.15);color:var(--green)">文字起こし済</span>':''}
                        </div>
                    </div>
                    <span class="expand-icon">&#9660;</span>
                </div>
                <div class="video-body" id="rvb-${i}">
                    ${v.url?`<a href="${esc(v.url)}" target="_blank" rel="noopener" class="video-link">TikTokで開く ↗</a>`:''}
                    ${v.transcript?`<div class="video-transcript">${esc(v.transcript)}</div>`:'<p style="color:var(--text-dim);font-size:.85rem">（文字起こしなし）</p>'}
                </div>
            </div>`).join('');
}

function renderHooks(hooks) {
    const el = document.getElementById('hooksCandidates');
    if (!hooks||!hooks.length) { el.innerHTML = '<div class="empty-state"><p>フック候補なし</p></div>'; return; }
    el.innerHTML = '<h3 class="section-subtitle">直近の高再生フック一覧</h3>' +
        hooks.map(h => `
            <div class="hook-card">
                <div class="hook-header">
                    <span class="hook-views">${fmtNum(h.views)}再生</span>
                    <span class="badge badge-hook-type">${esc(h.type)}</span>
                    <span class="hook-date">${esc(h.date)}</span>
                    ${h.account_name?`<a href="#" class="account-link" onclick="showAccount('${esc(h.account_url)}',event)">@${esc(h.account_name)}</a>`:''}
                </div>
                <div class="hook-text">「${esc(h.text)}」</div>
            </div>`).join('');
}

function renderTopics(tc, htc) {
    const el = document.getElementById('topicsAnalysis');
    let html = '';
    if (tc && Object.keys(tc).length) {
        const max = Math.max(...Object.values(tc),1);
        html += '<div class="card"><h3 class="section-subtitle">肌悩みトピック分布</h3>';
        Object.entries(tc).sort((a,b)=>b[1]-a[1]).forEach(([n,c])=>{
            html += `<div class="duration-row"><span class="duration-label" style="width:140px;text-align:left">${esc(n)}</span><div class="duration-bar-bg"><div class="duration-bar-fill" style="width:${(c/max)*100}%;background:linear-gradient(90deg,#0891b2,#22d3ee)">${c}本</div></div></div>`;
        });
        html += '</div>';
    }
    if (htc && Object.keys(htc).length) {
        const max = Math.max(...Object.values(htc),1);
        html += '<div class="card" style="margin-top:1.5rem"><h3 class="section-subtitle">フックタイプ分布</h3>';
        Object.entries(htc).sort((a,b)=>b[1]-a[1]).forEach(([n,c])=>{
            html += `<div class="duration-row"><span class="duration-label" style="width:140px;text-align:left">${esc(n)}</span><div class="duration-bar-bg"><div class="duration-bar-fill" style="width:${(c/max)*100}%;background:linear-gradient(90deg,#7c3aed,#a78bfa)">${c}本</div></div></div>`;
        });
        html += '</div>';
    }
    el.innerHTML = html || '<div class="empty-state"><p>データなし</p></div>';
}

function renderReference(ref) {
    const el = document.getElementById('referenceAnalysis');
    if (!ref || !ref.script_count) { el.innerHTML = '<div class="empty-state"><p>参考台本CSVがアップロードされていません</p></div>'; return; }
    let html = `<div class="card"><h3 class="section-subtitle">参考台本の分析結果</h3>
        <div class="stats-grid" style="margin-bottom:1rem">
            <div class="stat-card"><div class="stat-value">${ref.script_count}</div><div class="stat-label">参考台本数</div></div>
            <div class="stat-card"><div class="stat-value">${ref.success_count||0}</div><div class="stat-label">成功パターン</div></div>
            <div class="stat-card"><div class="stat-value">${ref.failure_count||0}</div><div class="stat-label">失敗パターン</div></div>
            <div class="stat-card"><div class="stat-value">${ref.avg_length||0}字</div><div class="stat-label">平均台本長</div></div>
        </div>`;

    if (ref.success_patterns && ref.success_patterns.length) {
        html += '<h4 style="color:var(--green);margin:1rem 0 .5rem">伸びたパターンの特徴</h4>';
        ref.success_patterns.forEach(p => {
            html += `<div style="background:var(--bg);border-radius:8px;padding:.75rem;margin-bottom:.5rem;border-left:3px solid var(--green)">
                <div style="font-size:.8rem;color:var(--green);font-weight:600">${fmtNum(p.views)}万再生 ― 「${esc(p.hook)}」</div>
                <div style="font-size:.85rem;color:var(--text-dim);margin-top:.3rem">${esc(p.note)}</div>
            </div>`;
        });
    }

    if (ref.failure_patterns && ref.failure_patterns.length) {
        html += '<h4 style="color:var(--accent);margin:1rem 0 .5rem">伸びなかったパターン（避けるべき）</h4>';
        ref.failure_patterns.forEach(p => {
            html += `<div style="background:var(--bg);border-radius:8px;padding:.75rem;margin-bottom:.5rem;border-left:3px solid var(--accent)">
                <div style="font-size:.8rem;color:var(--accent);font-weight:600">${fmtNum(p.views)}万再生 ― 「${esc(p.hook)}」</div>
                <div style="font-size:.85rem;color:var(--text-dim);margin-top:.3rem">${esc(p.note)}</div>
            </div>`;
        });
    }

    if (ref.voice_samples && ref.voice_samples.length) {
        html += '<h4 style="color:var(--purple);margin:1rem 0 .5rem">声の雰囲気サンプル</h4>';
        ref.voice_samples.forEach(v => { html += `<div style="background:var(--bg);border-radius:8px;padding:.75rem;margin-bottom:.5rem;font-size:.85rem;color:var(--text-dim)">${esc(v)}</div>`; });
    }
    html += '</div>';
    el.innerHTML = html;
}

// ===== アカウント情報モーダル =====
function showAccount(url, event) {
    if (event) event.preventDefault();
    if (!url) return;
    const modal = document.getElementById('accountModal');
    const content = document.getElementById('accountContent');
    modal.classList.remove('hidden');
    content.innerHTML = '<div class="spinner" style="margin:2rem auto"></div><p style="text-align:center;color:var(--text-dim)">アカウント情報を取得中...</p>';

    fetch('/api/planner/account', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account_url: url }) })
    .then(r => r.json())
    .then(data => {
        if (data.error) { content.innerHTML = `<p style="color:var(--accent)">${esc(data.error)}</p>`; return; }
        const a = data.account;
        content.innerHTML = `
            <div class="account-header">
                ${a.avatar?`<img src="${esc(a.avatar)}" class="account-avatar">`:'<div class="account-avatar-placeholder"></div>'}
                <div>
                    <h3 class="account-display-name">${esc(a.display_name||a.username)}</h3>
                    <a href="${esc(a.url)}" target="_blank" rel="noopener" class="account-username">@${esc(a.username)} ↗</a>
                </div>
            </div>
            ${a.bio?`<p class="account-bio">${esc(a.bio)}</p>`:''}
            <div class="account-stats-grid">
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.follower_count)}</div><div class="account-stat-label">フォロワー</div></div>
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.following_count)}</div><div class="account-stat-label">フォロー中</div></div>
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.like_count)}</div><div class="account-stat-label">いいね</div></div>
                <div class="account-stat"><div class="account-stat-value">${fmtNum(a.video_count)}</div><div class="account-stat-label">動画数</div></div>
            </div>
            ${a.activity_months?`<div class="account-extra"><span>活動期間:</span> <strong>約${a.activity_months}ヶ月</strong></div>`:''}
            ${a.recent_month_views?`<div class="account-extra"><span>直近1ヶ月の再生数:</span> <strong>${fmtNum(a.recent_month_views)}</strong></div>`:''}
            ${a.first_post_date?`<div class="account-extra"><span>初投稿:</span> <strong>${esc(a.first_post_date)}</strong></div>`:''}
            <div class="account-extra">
                <span>アカウントタイプ:</span>
                <strong style="color:${a.is_personality_driven?'var(--yellow)':'var(--green)'}">${a.is_personality_driven?'属人型（人に人気）':'コンテンツ型'}</strong>
            </div>
            ${a.personality_reason?`<div style="font-size:.8rem;color:var(--text-dim);margin-top:.3rem">判定理由: ${esc(a.personality_reason)}</div>`:''}
            ${a.trending_products&&a.trending_products.length?`<div class="account-extra"><span>扱っているトレンド商品:</span><br>${a.trending_products.map(p=>`<span class="badge badge-topic" style="margin:.15rem .2rem">${esc(p)}</span>`).join('')}</div>`:''}
        `;
    }).catch(() => { content.innerHTML = '<p style="color:var(--accent)">取得に失敗しました</p>'; });
}
function closeAccountModal(e) { if(e&&e.target!==document.getElementById('accountModal'))return; document.getElementById('accountModal').classList.add('hidden'); }

// ===== UI操作 =====
function togglePlan(i) { document.getElementById(`plan-${i}`).classList.toggle('open'); document.getElementById(`pb-${i}`).classList.toggle('open'); }
function toggleRV(i) { document.getElementById(`rv-${i}`).classList.toggle('open'); document.getElementById(`rvb-${i}`).classList.toggle('open'); }
function copyScript(i) { navigator.clipboard.writeText(document.getElementById(`st-${i}`).textContent).then(()=>{ const b=event.target; b.textContent='コピー済み!'; setTimeout(()=>b.textContent='コピー',2000); }); }
function switchPlannerTab(name) { document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active')); document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active')); event.target.classList.add('active'); document.getElementById(`ptab-${name}`).classList.add('active'); }

function fmtNum(n) { if(typeof n==='string')return n; if(!n)return '0'; if(n>=1e8)return(n/1e8).toFixed(1)+'億'; if(n>=1e4)return(n/1e4).toFixed(1)+'万'; return n.toLocaleString(); }
function esc(s) { if(!s)return ''; const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
