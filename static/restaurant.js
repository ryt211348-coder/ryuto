/* レストラン比較ツール - フロントエンドJS（前半：初期化・検索） */

// グローバル変数
let allRestaurants = [];

// 初期化
document.addEventListener("DOMContentLoaded", function () {
    loadOptions();
    searchRestaurants();
});

// 選択肢をAPIから取得してセレクトボックスに反映
async function loadOptions() {
    try {
        const res = await fetch("/api/restaurant/options");
        const data = await res.json();

        populateSelect("area", data.areas);
        populateSelect("genre", data.genres);
        populateSelect("atmosphere", data.atmospheres);
    } catch (e) {
        console.error("選択肢の取得に失敗:", e);
    }
}

function populateSelect(id, items) {
    const el = document.getElementById(id);
    if (!el) return;
    items.forEach(function (item) {
        const opt = document.createElement("option");
        opt.value = item;
        opt.textContent = item;
        el.appendChild(opt);
    });
}

// 検索実行
async function searchRestaurants() {
    const resultsEl = document.getElementById("results");
    const countEl = document.getElementById("result-count");

    resultsEl.innerHTML = '<div class="loading">検索中...</div>';
    countEl.style.display = "none";

    const params = {
        area: document.getElementById("area").value,
        genre: document.getElementById("genre").value,
        atmosphere: document.getElementById("atmosphere").value,
        party_size: parseInt(document.getElementById("party_size").value) || 0,
        budget_min: parseInt(document.getElementById("budget_min").value) || 0,
        budget_max: parseInt(document.getElementById("budget_max").value) || 0,
        reservation_status: document.getElementById("reservation").value,
        has_private_room: document.getElementById("private_room").checked,
        sort_by: document.getElementById("sort_by").value,
    };

    try {
        const res = await fetch("/api/restaurant/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(params),
        });
        const data = await res.json();

        allRestaurants = data.restaurants;
        renderResults(data.restaurants, data.count);
    } catch (e) {
        resultsEl.innerHTML =
            '<div class="no-results"><h3>エラーが発生しました</h3><p>再度お試しください</p></div>';
        console.error("検索エラー:", e);
    }
}

// スコアに応じたCSSクラスを返す
function scoreClass(score) {
    if (score >= 4.0) return "score-high";
    if (score >= 3.5) return "score-mid";
    return "score-low";
}

// 予約状況のCSSクラスを返す
function reserveClass(status) {
    if (status === "available") return "reserve-available";
    if (status === "few") return "reserve-few";
    return "reserve-full";
}

// レビューバーのCSSクラスを返す
function barClass(source) {
    if (source === "tabelog") return "bar-tabelog";
    if (source === "hotpepper") return "bar-hotpepper";
    return "bar-google";
}

/* ===== 後半：レンダリング・モーダル ===== */

// 検索結果をレンダリング
function renderResults(restaurants, count) {
    var resultsEl = document.getElementById("results");
    var countEl = document.getElementById("result-count");

    if (!restaurants || restaurants.length === 0) {
        resultsEl.innerHTML =
            '<div class="no-results">' +
            "<h3>条件に合うレストランが見つかりません</h3>" +
            "<p>条件を変更して再検索してみてください</p>" +
            "</div>";
        countEl.style.display = "none";
        return;
    }

    countEl.innerHTML = "<strong>" + count + "</strong> 件のレストランが見つかりました";
    countEl.style.display = "block";

    var html = "";
    for (var i = 0; i < restaurants.length; i++) {
        html += buildCard(restaurants[i], i);
    }
    resultsEl.innerHTML = html;
}

// カードHTMLを構築
function buildCard(r, index) {
    var sc = r.overall_score ? r.overall_score.toFixed(2) : "-.--";
    var scCls = scoreClass(r.overall_score || 0);

    // レビュー行を構築
    var reviewsHtml = "";
    var reviews = r.reviews || [];
    for (var j = 0; j < reviews.length; j++) {
        var rv = reviews[j];
        var barWidth = (rv.rating / 5.0) * 100;
        reviewsHtml +=
            '<div class="review-row">' +
            '<span class="review-source">' + escHtml(rv.source_label) + "</span>" +
            '<div class="review-bar-bg">' +
            '<div class="review-bar ' + barClass(rv.source) + '" style="width:' + barWidth + '%"></div>' +
            "</div>" +
            '<span class="review-rating">' + rv.rating.toFixed(1) + "</span>" +
            '<span class="review-count">' + rv.review_count.toLocaleString() + "件</span>" +
            "</div>";
    }

    // 雰囲気タグ
    var tagsHtml = "";
    var tags = r.atmosphere_tags || [];
    for (var k = 0; k < tags.length && k < 3; k++) {
        tagsHtml += '<span class="tag tag-atmosphere">' + escHtml(tags[k]) + "</span>";
    }

    // 予約バッジ
    var rvCls = reserveClass(r.reservation_status);
    var rvLabel = r.reservation_label || "";

    return (
        '<div class="restaurant-card" onclick="openModal(' + index + ')">' +
        '<div class="card-header">' +
        '<div class="card-info">' +
        '<div class="card-name">' + escHtml(r.name) + "</div>" +
        '<div class="card-meta">' +
        "<span>" + escHtml(r.genre) + "</span>" +
        "<span>|</span>" +
        "<span>" + escHtml(r.area) + "</span>" +
        "</div>" +
        "</div>" +
        '<div class="score-badge ' + scCls + '">' +
        '<span class="score-num">' + sc + "</span>" +
        '<span class="score-label">SCORE</span>' +
        "</div>" +
        "</div>" +
        '<div class="card-reviews">' +
        reviewsHtml +
        "</div>" +
        '<div class="card-footer">' +
        '<span class="card-price">' + escHtml(r.price_label) + "</span>" +
        '<div class="card-tags">' +
        '<span class="reservation-badge ' + rvCls + '">' + escHtml(rvLabel) + "</span>" +
        tagsHtml +
        "</div>" +
        "</div>" +
        "</div>"
    );
}

// モーダルを開く
function openModal(index) {
    var r = allRestaurants[index];
    if (!r) return;

    var sc = r.overall_score ? r.overall_score.toFixed(2) : "-.--";
    var scCls = scoreClass(r.overall_score || 0);

    // レビュー詳細
    var reviewsHtml = "";
    var reviews = r.reviews || [];
    for (var j = 0; j < reviews.length; j++) {
        var rv = reviews[j];
        var barW = (rv.rating / 5.0) * 100;
        reviewsHtml +=
            '<div class="detail-review-row">' +
            '<span class="detail-review-source">' + escHtml(rv.source_label) + "</span>" +
            '<span class="detail-review-rating">' + rv.rating.toFixed(1) + "</span>" +
            '<div class="detail-review-bar-bg">' +
            '<div class="detail-review-bar ' + barClass(rv.source) + '" style="width:' + barW + '%"></div>' +
            "</div>" +
            '<span class="detail-review-count">' + rv.review_count.toLocaleString() + "件</span>" +
            "</div>";
    }

    // 雰囲気タグ
    var tagsHtml = "";
    var tags = (r.atmosphere_tags || []).concat(r.features || []);
    for (var k = 0; k < tags.length; k++) {
        tagsHtml += '<span class="detail-tag">' + escHtml(tags[k]) + "</span>";
    }

    var rvCls = reserveClass(r.reservation_status);

    var html =
        '<div class="detail-header">' +
        "<div>" +
        '<div class="detail-name">' + escHtml(r.name) + "</div>" +
        '<div class="detail-sub">' + escHtml(r.genre) + " / " + escHtml(r.sub_genre || "") + " - " + escHtml(r.area) + "</div>" +
        "</div>" +
        '<div class="score-badge ' + scCls + '" style="width:64px;height:64px;">' +
        '<span class="score-num" style="font-size:22px;">' + sc + "</span>" +
        '<span class="score-label">SCORE</span>' +
        "</div>" +
        "</div>" +
        '<div class="detail-section">' +
        "<h3>説明</h3>" +
        '<p class="detail-description">' + escHtml(r.description || "") + "</p>" +
        "</div>" +
        '<div class="detail-section">' +
        "<h3>各サイトの評価</h3>" +
        '<div class="detail-reviews">' + reviewsHtml + "</div>" +
        "</div>" +
        '<div class="detail-section">' +
        "<h3>店舗情報</h3>" +
        '<div class="detail-info-grid">' +
        infoItem("住所", r.address) +
        infoItem("価格帯", r.price_label) +
        infoItem("営業時間", r.open_hours) +
        infoItem("定休日", r.closed_days) +
        infoItem("席数", r.capacity + "席") +
        infoItem("個室", r.has_private_room ? "あり" : "なし") +
        infoItem("喫煙", r.smoking) +
        '<div class="detail-info-item">' +
        '<span class="info-label">予約状況</span>' +
        '<span class="info-value"><span class="reservation-badge ' + rvCls + '">' + escHtml(r.reservation_label || "") + "</span></span>" +
        "</div>" +
        "</div>" +
        "</div>" +
        '<div class="detail-section">' +
        "<h3>雰囲気・特徴</h3>" +
        '<div class="detail-tags">' + tagsHtml + "</div>" +
        "</div>";

    document.getElementById("modal-body").innerHTML = html;
    document.getElementById("modal").style.display = "flex";
    document.body.style.overflow = "hidden";
}

// モーダルを閉じる
function closeModal() {
    document.getElementById("modal").style.display = "none";
    document.body.style.overflow = "";
}

// ESCキーでモーダルを閉じる
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeModal();
});

// ヘルパー：情報アイテム
function infoItem(label, value) {
    return (
        '<div class="detail-info-item">' +
        '<span class="info-label">' + escHtml(label) + "</span>" +
        '<span class="info-value">' + escHtml(value || "-") + "</span>" +
        "</div>"
    );
}

// HTMLエスケープ
function escHtml(str) {
    if (!str) return "";
    var s = String(str);
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
