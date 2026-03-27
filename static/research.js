/* =====================================================
   SNS Research Tool - メインJavaScript
   ===================================================== */

// --- グローバル状態 ---
const state = {
    genre: "food",
    platform: "both",
    period: "1month",
    view: "mindmap",
    level: 1,
    category: "",
    subcategory: "",
    selectedKeyword: "",
};

// --- ユーティリティ ---
function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return n.toString();
}

function volumeClass(vol) {
    if (vol >= 30000) return "high";
    if (vol >= 10000) return "mid";
    return "low";
}

function genreClass() { return state.genre; }

// --- API通信 ---
async function fetchKeywords(level, category, subcategory) {
    const params = new URLSearchParams({
        genre: state.genre, level, period: state.period,
        platform: state.platform, category: category || "",
        subcategory: subcategory || "",
    });
    const res = await fetch(`/api/research/keywords?${params}`);
    return res.json();
}

async function fetchVideos(keyword) {
    const params = new URLSearchParams({
        keyword, period: state.period, platform: state.platform, count: 20,
    });
    const res = await fetch(`/api/research/videos?${params}`);
    return res.json();
}

async function fetchAccounts(keyword) {
    const params = new URLSearchParams({
        keyword, period: state.period, platform: state.platform, count: 15,
    });
    const res = await fetch(`/api/research/accounts?${params}`);
    return res.json();
}

// --- トグル操作 ---
function setupToggles() {
    document.querySelectorAll(".toggle-group").forEach(group => {
        group.querySelectorAll(".toggle-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                group.querySelectorAll(".toggle-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                const groupId = group.id;
                const val = btn.dataset.value;

                if (groupId === "genreToggle") {
                    state.genre = val;
                    resetToLevel1();
                } else if (groupId === "platformToggle") {
                    state.platform = val;
                    refreshCurrentView();
                } else if (groupId === "periodToggle") {
                    state.period = val;
                    refreshCurrentView();
                } else if (groupId === "viewToggle") {
                    state.view = val;
                    switchView(val);
                }
            });
        });
    });
}

function resetToLevel1() {
    state.level = 1;
    state.category = "";
    state.subcategory = "";
    state.selectedKeyword = "";
    updateBreadcrumb();
    refreshCurrentView();
}

function refreshCurrentView() {
    if (state.view === "mindmap") {
        loadMindmap();
    } else if (state.view === "videos") {
        loadVideos();
    } else if (state.view === "accounts") {
        loadAccounts();
    }
}

function switchView(view) {
    document.getElementById("mindmapArea").classList.toggle("hidden", view !== "mindmap");
    document.getElementById("videosArea").classList.toggle("hidden", view !== "videos");
    document.getElementById("accountsArea").classList.toggle("hidden", view !== "accounts");
    refreshCurrentView();
}

// --- パンくずリスト ---
function updateBreadcrumb() {
    const bc = document.getElementById("breadcrumb");
    let html = `<span class="crumb ${state.level === 1 ? 'active' : ''}" data-level="1" onclick="navigateTo(1)">トップ</span>`;

    if (state.category) {
        html += `<span class="crumb-sep">›</span>`;
        html += `<span class="crumb ${state.level === 2 ? 'active' : ''}" data-level="2" onclick="navigateTo(2)">${state.category}</span>`;
    }
    if (state.subcategory) {
        html += `<span class="crumb-sep">›</span>`;
        html += `<span class="crumb ${state.level === 3 ? 'active' : ''}" data-level="3" onclick="navigateTo(3)">${state.subcategory}</span>`;
    }
    bc.innerHTML = html;
}

function navigateTo(level) {
    if (level === 1) {
        state.level = 1; state.category = ""; state.subcategory = "";
    } else if (level === 2) {
        state.level = 2; state.subcategory = "";
    }
    state.selectedKeyword = "";
    updateBreadcrumb();
    refreshCurrentView();
}

// --- マインドマップ描画 ---
async function loadMindmap() {
    const container = document.getElementById("mindmapContainer");
    const loading = document.getElementById("loading");
    loading.classList.remove("hidden");
    container.innerHTML = "";

    try {
        const data = await fetchKeywords(state.level, state.category, state.subcategory);
        loading.classList.add("hidden");

        if (!data.nodes || data.nodes.length === 0) {
            container.innerHTML = '<div style="text-align:center;padding:40px;color:#8b949e;">データがありません</div>';
            return;
        }

        renderNodesGrid(container, data.nodes);
    } catch (err) {
        loading.classList.add("hidden");
        container.innerHTML = `<div style="text-align:center;padding:40px;color:#f85149;">エラー: ${err.message}</div>`;
    }
}

function renderNodesGrid(container, nodes) {
    const maxVol = Math.max(...nodes.map(n => n.volume));
    const grid = document.createElement("div");
    grid.className = "nodes-grid";

    nodes.forEach((node, i) => {
        const card = document.createElement("div");
        card.className = `node-card ${genreClass()}`;
        const pct = Math.round((node.volume / maxVol) * 100);

        card.innerHTML = `
            <div class="node-badge">#${i + 1}</div>
            <div class="node-name">${node.name}</div>
            <div class="node-volume ${volumeClass(node.volume)}">${formatNumber(node.volume)}</div>
            ${node.has_children ? `<div class="node-children-hint">${node.child_count}個のサブカテゴリ ▸</div>` : ""}
            <div class="node-bar"><div class="node-bar-fill ${genreClass()}" style="width:${pct}%"></div></div>
        `;

        card.addEventListener("click", () => handleNodeClick(node));
        grid.appendChild(card);
    });

    container.appendChild(grid);
}

function handleNodeClick(node) {
    if (node.has_children && state.level < 3) {
        if (state.level === 1) {
            state.category = node.name;
            state.level = 2;
        } else if (state.level === 2) {
            state.subcategory = node.name;
            state.level = 3;
        }
        state.selectedKeyword = node.name;
        updateBreadcrumb();
        loadMindmap();
    } else {
        state.selectedKeyword = node.name;
        showSidePanel(node);
    }
}

// --- サイドパネル ---
async function showSidePanel(node) {
    const panel = document.getElementById("sidePanel");
    const title = document.getElementById("panelTitle");
    const body = document.getElementById("panelBody");

    panel.classList.remove("hidden");
    title.textContent = node.name;

    body.innerHTML = '<div class="loading"><div class="spinner"></div><p>読み込み中...</p></div>';

    try {
        const [videosData, accountsData] = await Promise.all([
            fetchVideos(node.name),
            fetchAccounts(node.name),
        ]);

        let html = `
            <div class="panel-section">
                <div class="panel-section-title">キーワード情報</div>
                <div class="panel-stat"><span class="panel-stat-label">ボリューム</span><span class="panel-stat-value">${formatNumber(node.volume)}</span></div>
                <div class="panel-stat"><span class="panel-stat-label">ジャンル</span><span class="panel-stat-value">${state.genre === "food" ? "食品" : "美容"}</span></div>
                <div class="panel-stat"><span class="panel-stat-label">期間</span><span class="panel-stat-value">${state.period}</span></div>
                ${node.parent ? `<div class="panel-stat"><span class="panel-stat-label">親カテゴリ</span><span class="panel-stat-value">${node.parent}</span></div>` : ""}
            </div>
            <div class="panel-section">
                <div class="panel-section-title">トップ動画 (${videosData.videos.length}件)</div>
        `;

        videosData.videos.slice(0, 5).forEach((v, i) => {
            html += `
                <div class="video-card" style="grid-template-columns:32px 1fr auto;padding:8px 10px;margin-bottom:4px;">
                    <div class="video-rank ${i < 3 ? 'top3' : ''}" style="font-size:16px;">${i + 1}</div>
                    <div class="video-info">
                        <div class="video-title" style="font-size:12px;">${v.title}</div>
                        <div class="video-meta">
                            <span class="platform-badge ${v.platform}">${v.platform === "tiktok" ? "TikTok" : "Insta"}</span>
                            <span>${v.days_ago}日前</span>
                        </div>
                    </div>
                    <div class="video-stats">
                        <div class="video-views" style="font-size:13px;">${formatNumber(v.views)}</div>
                    </div>
                </div>
            `;
        });

        html += `</div><div class="panel-section"><div class="panel-section-title">注目アカウント (${accountsData.accounts.length}件)</div>`;

        accountsData.accounts.slice(0, 5).forEach(a => {
            const growthCls = a.growth_rate >= 0 ? "positive" : "negative";
            html += `
                <div class="panel-stat">
                    <span class="panel-stat-label">${a.username}</span>
                    <span class="account-growth ${growthCls}">${a.growth_rate >= 0 ? "+" : ""}${a.growth_rate}%</span>
                </div>
            `;
        });

        html += `</div>
            <div class="panel-section">
                <div class="panel-section-title">関連ハッシュタグ</div>
                <div class="panel-tags">
                    <span class="panel-tag">#${node.name}</span>
                    <span class="panel-tag">#${node.name}おすすめ</span>
                    <span class="panel-tag">#${state.genre === "food" ? "グルメ" : "コスメ"}</span>
                    <span class="panel-tag">#バズり</span>
                    <span class="panel-tag">#おすすめにのりたい</span>
                </div>
            </div>
        `;

        body.innerHTML = html;
    } catch (err) {
        body.innerHTML = `<div style="color:#f85149;padding:12px;">エラー: ${err.message}</div>`;
    }
}

document.getElementById("panelClose").addEventListener("click", () => {
    document.getElementById("sidePanel").classList.add("hidden");
});

// --- 動画一覧 ---
async function loadVideos() {
    const grid = document.getElementById("videosGrid");
    const title = document.getElementById("videosTitle");
    const keyword = state.selectedKeyword || (state.genre === "food" ? "食品" : "美容");
    title.textContent = `「${keyword}」のバズり動画`;
    grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const data = await fetchVideos(keyword);
        grid.innerHTML = "";
        data.videos.forEach((v, i) => {
            const card = document.createElement("div");
            card.className = "video-card";
            card.innerHTML = `
                <div class="video-rank ${i < 3 ? 'top3' : ''}">${i + 1}</div>
                <div class="video-info">
                    <div class="video-title">${v.title}</div>
                    <div class="video-meta">
                        <span class="platform-badge ${v.platform}">${v.platform === "tiktok" ? "TikTok" : "Instagram"}</span>
                        <span>${v.account}</span>
                        <span>${v.days_ago}日前</span>
                    </div>
                </div>
                <div class="video-stats">
                    <div class="video-views">${formatNumber(v.views)}再生</div>
                    <div class="video-engagement">ER: ${v.engagement_rate}%</div>
                    <div class="video-meta">${formatNumber(v.likes)}♡ ${formatNumber(v.comments)}💬</div>
                </div>
            `;
            card.addEventListener("click", () => showVideoDetail(v));
            grid.appendChild(card);
        });
    } catch (err) {
        grid.innerHTML = `<div style="color:#f85149;padding:24px;">エラー: ${err.message}</div>`;
    }
}

function showVideoDetail(v) {
    const panel = document.getElementById("sidePanel");
    const title = document.getElementById("panelTitle");
    const body = document.getElementById("panelBody");
    panel.classList.remove("hidden");
    title.textContent = "動画詳細";
    body.innerHTML = `
        <div class="panel-section">
            <div class="panel-section-title">基本情報</div>
            <div class="panel-stat"><span class="panel-stat-label">タイトル</span><span class="panel-stat-value" style="font-size:12px;max-width:200px;text-align:right;">${v.title}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">プラットフォーム</span><span class="platform-badge ${v.platform}">${v.platform === "tiktok" ? "TikTok" : "Instagram"}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">アカウント</span><span class="panel-stat-value">${v.account}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">投稿日</span><span class="panel-stat-value">${v.days_ago}日前</span></div>
        </div>
        <div class="panel-section">
            <div class="panel-section-title">パフォーマンス</div>
            <div class="panel-stat"><span class="panel-stat-label">再生数</span><span class="panel-stat-value" style="color:#3fb950;">${formatNumber(v.views)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">いいね</span><span class="panel-stat-value">${formatNumber(v.likes)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">コメント</span><span class="panel-stat-value">${formatNumber(v.comments)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">シェア</span><span class="panel-stat-value">${formatNumber(v.shares)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">ER</span><span class="panel-stat-value" style="color:#d29922;">${v.engagement_rate}%</span></div>
        </div>
        <div class="panel-section">
            <div class="panel-section-title">ハッシュタグ</div>
            <div class="panel-tags">${v.hashtags.map(h => `<span class="panel-tag">${h}</span>`).join("")}</div>
        </div>
        <div class="panel-section">
            <div class="panel-section-title">アカウント情報</div>
            <div class="panel-stat"><span class="panel-stat-label">フォロワー</span><span class="panel-stat-value">${formatNumber(v.account_followers)}</span></div>
        </div>
    `;
}

// --- アカウント一覧 ---
async function loadAccounts() {
    const grid = document.getElementById("accountsGrid");
    const title = document.getElementById("accountsTitle");
    const keyword = state.selectedKeyword || (state.genre === "food" ? "食品" : "美容");
    title.textContent = `「${keyword}」の注目アカウント`;
    grid.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const data = await fetchAccounts(keyword);
        grid.innerHTML = "";
        data.accounts.forEach(a => {
            const card = document.createElement("div");
            card.className = "account-card";
            const growthCls = a.growth_rate >= 0 ? "positive" : "negative";
            const initial = a.display_name.charAt(0);
            card.innerHTML = `
                <div class="account-avatar">${initial}</div>
                <div class="account-info">
                    <div class="account-name">${a.display_name}</div>
                    <div class="account-handle">
                        <span class="platform-badge ${a.platform}">${a.platform === "tiktok" ? "TikTok" : "Insta"}</span>
                        ${a.username}
                    </div>
                    <div class="account-meta">
                        <span>投稿${a.posts}件</span>
                        <span>平均${formatNumber(a.avg_views)}再生</span>
                    </div>
                </div>
                <div class="account-stats">
                    <div class="account-followers">${formatNumber(a.followers)}</div>
                    <div class="account-growth ${growthCls}">${a.growth_rate >= 0 ? "+" : ""}${a.growth_rate}%</div>
                    <div style="font-size:11px;color:#8b949e;">ER: ${a.engagement_rate}%</div>
                </div>
            `;
            card.addEventListener("click", () => showAccountDetail(a));
            grid.appendChild(card);
        });
    } catch (err) {
        grid.innerHTML = `<div style="color:#f85149;padding:24px;">エラー: ${err.message}</div>`;
    }
}

function showAccountDetail(a) {
    const panel = document.getElementById("sidePanel");
    const title = document.getElementById("panelTitle");
    const body = document.getElementById("panelBody");
    panel.classList.remove("hidden");
    title.textContent = a.display_name;
    const growthCls = a.growth_rate >= 0 ? "positive" : "negative";
    body.innerHTML = `
        <div class="panel-section">
            <div class="panel-section-title">アカウント情報</div>
            <div class="panel-stat"><span class="panel-stat-label">ユーザー名</span><span class="panel-stat-value">${a.username}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">プラットフォーム</span><span class="platform-badge ${a.platform}">${a.platform === "tiktok" ? "TikTok" : "Instagram"}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">フォロワー</span><span class="panel-stat-value">${formatNumber(a.followers)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">フォロー中</span><span class="panel-stat-value">${formatNumber(a.following)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">投稿数</span><span class="panel-stat-value">${a.posts}</span></div>
        </div>
        <div class="panel-section">
            <div class="panel-section-title">パフォーマンス</div>
            <div class="panel-stat"><span class="panel-stat-label">成長率</span><span class="account-growth ${growthCls}" style="font-size:16px;">${a.growth_rate >= 0 ? "+" : ""}${a.growth_rate}%</span></div>
            <div class="panel-stat"><span class="panel-stat-label">平均再生数</span><span class="panel-stat-value">${formatNumber(a.avg_views)}</span></div>
            <div class="panel-stat"><span class="panel-stat-label">ER</span><span class="panel-stat-value" style="color:#d29922;">${a.engagement_rate}%</span></div>
        </div>
        <div class="panel-section">
            <div class="panel-section-title">関連キーワード</div>
            <div class="panel-tags">${a.related_keywords.map(k => `<span class="panel-tag">#${k}</span>`).join("")}</div>
        </div>
    `;
}

// --- ソート ---
document.getElementById("videoSort").addEventListener("change", (e) => {
    loadVideos();
});
document.getElementById("accountSort").addEventListener("change", (e) => {
    loadAccounts();
});

// --- 初期化 ---
document.addEventListener("DOMContentLoaded", () => {
    setupToggles();
    updateBreadcrumb();
    loadMindmap();
});
