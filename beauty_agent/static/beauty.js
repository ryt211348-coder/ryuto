// 美容AI制作エージェント - Web UI JavaScript

// ========================================
// タブ切り替え
// ========================================
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(tabId).classList.add('active');
}

// ========================================
// 設定チェック
// ========================================
async function checkConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    updateConfigUI(data);
  } catch (e) {
    console.error('設定チェック失敗:', e);
  }
}

function updateConfigUI(config) {
  const items = [
    { key: 'gemini_key', label: 'Gemini API Key' },
    { key: 'anthropic_key', label: 'Anthropic API Key' },
    { key: 'google_creds', label: 'Google認証' },
    { key: 'drive_folder', label: 'Drive Folder ID' },
  ];

  const grid = document.getElementById('config-grid');
  grid.innerHTML = items.map(item => `
    <div class="config-item">
      <span class="dot ${config[item.key] ? 'on' : 'off'}"></span>
      <span>${item.label}</span>
    </div>
  `).join('');
}

async function saveConfig() {
  const data = {};
  const gemini = document.getElementById('cfg-gemini').value.trim();
  const anthropic = document.getElementById('cfg-anthropic').value.trim();
  const drive = document.getElementById('cfg-drive').value.trim();

  if (gemini) data.gemini_key = gemini;
  if (anthropic) data.anthropic_key = anthropic;
  if (drive) data.drive_folder_id = drive;

  if (Object.keys(data).length === 0) return;

  try {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    checkConfig();
    // 入力欄クリア
    document.getElementById('cfg-gemini').value = '';
    document.getElementById('cfg-anthropic').value = '';
    document.getElementById('cfg-drive').value = '';
    alert('設定を保存しました');
  } catch (e) {
    alert('設定保存に失敗しました');
  }
}

// ========================================
// 台本プレビュー
// ========================================
async function previewScript() {
  const url = document.getElementById('doc-url').value.trim();
  const text = document.getElementById('script-text').value.trim();

  if (!url && !text) {
    alert('ドキュメントURLまたは台本テキストを入力してください');
    return;
  }

  const previewArea = document.getElementById('preview-area');
  previewArea.innerHTML = '<p style="color:var(--text-secondary)">パース中...</p>';

  try {
    let res;
    if (text) {
      res = await fetch('/api/parse-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
    } else {
      res = await fetch('/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_url: url }),
      });
    }

    const data = await res.json();
    if (data.error) {
      previewArea.innerHTML = `<p style="color:var(--accent-red)">${data.error}</p>`;
      return;
    }

    renderScenePreview(data.scenes, previewArea);
  } catch (e) {
    previewArea.innerHTML = `<p style="color:var(--accent-red)">エラー: ${e.message}</p>`;
  }
}

function renderScenePreview(scenes, container) {
  const caveChars = ['毛穴', '白ニキビ', '赤ニキビ', 'アクネ菌'];
  container.innerHTML = `
    <p style="color:var(--accent-green);margin-bottom:12px">${scenes.length}シーン検出</p>
    <div class="scene-list">
      ${scenes.map(s => {
        const cave = caveChars.includes(s.character) ? '<span class="badge badge-warn">洞窟防止</span>' : '';
        return `
          <div class="scene-item">
            <span class="scene-num">${s.scene_id}</span>
            <span class="scene-char">${s.character}</span>
            <span class="scene-emotion">${s.inferred_emotion}</span>
            <span class="scene-lines">${s.lines.slice(0, 2).join(' / ')}</span>
            ${cave}
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// ========================================
// パイプライン実行
// ========================================
let currentJobId = null;
let pollTimer = null;

async function startPipeline() {
  const url = document.getElementById('doc-url').value.trim();
  if (!url) {
    alert('ドキュメントURLを入力してください');
    return;
  }

  document.getElementById('btn-run').disabled = true;
  const progressArea = document.getElementById('progress-area');
  progressArea.classList.add('active');

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_url: url }),
    });
    const data = await res.json();

    if (data.error) {
      document.getElementById('progress-message').textContent = data.error;
      document.getElementById('btn-run').disabled = false;
      return;
    }

    currentJobId = data.job_id;
    pollStatus();
  } catch (e) {
    document.getElementById('progress-message').textContent = `エラー: ${e.message}`;
    document.getElementById('btn-run').disabled = false;
  }
}

function pollStatus() {
  if (!currentJobId) return;

  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${currentJobId}`);
      const job = await res.json();
      updateProgressUI(job);

      if (job.status === 'completed' || job.status === 'error') {
        clearInterval(pollTimer);
        document.getElementById('btn-run').disabled = false;
      }
    } catch (e) {
      console.error('ステータス取得失敗:', e);
    }
  }, 2000);
}

function updateProgressUI(job) {
  document.getElementById('progress-message').textContent = job.message || '';

  // プログレスバー
  const total = job.total_scenes || 1;
  const progress = job.progress || 0;
  const pct = Math.min((progress / total) * 100, 100);
  document.getElementById('progress-bar').style.width = `${pct}%`;

  // シーン結果
  const resultsArea = document.getElementById('scene-results');
  if (job.scene_results && job.scene_results.length > 0) {
    resultsArea.innerHTML = `
      <div class="scene-list">
        ${job.scene_results.map(sr => {
          let scoreClass = '';
          let scoreText = '';
          let icon = '';
          if (sr.result === 'OK') {
            scoreClass = 'ok';
            scoreText = `${sr.score}点`;
            icon = '<span class="status-icon ok"></span>';
          } else if (sr.result === 'FAILED') {
            scoreClass = 'ng';
            scoreText = sr.score ? `${sr.score}点` : 'FAILED';
            icon = '<span class="status-icon ng"></span>';
          } else {
            icon = '<span class="status-icon generating"></span>';
            scoreText = '...';
          }
          const retries = sr.retries > 0 ? `(リトライ${sr.retries}回)` : '';
          return `
            <div class="scene-item">
              ${icon}
              <span class="scene-num">${sr.scene_id}</span>
              <span class="scene-char">${sr.character}</span>
              <span class="scene-lines">${retries}</span>
              <span class="scene-score ${scoreClass}">${scoreText}</span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // 完了時の結果表示
  if (job.status === 'completed') {
    const resultArea = document.getElementById('final-result');
    resultArea.innerHTML = `
      <div class="card result-card">
        <h2>完了</h2>
        <p>OK画像: ${job.ok_count || 0}/${job.total_scenes || 0}枚</p>
        <div class="result-links">
          ${job.spreadsheet_url ? `<a href="${job.spreadsheet_url}" target="_blank">📊 編集者指示書を開く</a>` : ''}
          ${job.drive_folder_url ? `<a href="${job.drive_folder_url}" target="_blank">📁 Driveフォルダを開く</a>` : ''}
        </div>
        ${job.sheet_error ? `<p style="color:var(--accent-red);font-size:0.8rem;margin-top:8px">スプレッドシートエラー: ${job.sheet_error}</p>` : ''}
        ${job.drive_error ? `<p style="color:var(--accent-red);font-size:0.8rem;margin-top:4px">ドライブエラー: ${job.drive_error}</p>` : ''}
      </div>
    `;
  } else if (job.status === 'error') {
    const resultArea = document.getElementById('final-result');
    resultArea.innerHTML = `
      <div class="card result-card error">
        <h2>エラー</h2>
        <p>${job.message}</p>
      </div>
    `;
  }
}

// ========================================
// ログ表示
// ========================================
async function loadLog() {
  try {
    const res = await fetch('/api/log');
    const log = await res.json();
    renderLog(log);
    renderProfiles(log);
  } catch (e) {
    console.error('ログ取得失敗:', e);
  }
}

function renderLog(log) {
  const container = document.getElementById('log-entries');
  const logs = (log.logs || []).slice().reverse().slice(0, 50);

  if (logs.length === 0) {
    container.innerHTML = '<p style="color:var(--text-secondary)">ログがまだありません</p>';
    return;
  }

  container.innerHTML = `
    <table class="log-table">
      <thead>
        <tr>
          <th>日時</th>
          <th>プロジェクト</th>
          <th>Scene</th>
          <th>キャラ</th>
          <th>結果</th>
          <th>スコア</th>
          <th>メモ</th>
        </tr>
      </thead>
      <tbody>
        ${logs.map(entry => {
          const cls = entry.result === 'OK' ? 'ok' : entry.result === 'FAILED' ? 'failed' : 'ng';
          const override = entry.manual_override ? ` [手動]` : '';
          return `
            <tr>
              <td>${entry.date}</td>
              <td>${entry.project}</td>
              <td>${entry.scene_id}</td>
              <td>${entry.character}</td>
              <td class="${cls}">${entry.result}${override}</td>
              <td>${entry.total_score || '-'}</td>
              <td>${entry.memo || ''}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;

  // グローバルルール
  const rulesContainer = document.getElementById('learned-rules');
  const rules = log.global_rules_learned || [];
  rulesContainer.innerHTML = rules.map(r => `<li>${r}</li>`).join('');
}

function renderProfiles(log) {
  const container = document.getElementById('profile-cards');
  const profiles = log.character_profiles || {};

  const charIcons = {
    '皮脂': '🧴',
    '毛穴': '🕳',
    'アクネ菌': '🦠',
    '白ニキビ': '⚪',
    '赤ニキビ': '🔴',
    '洗顔料': '🧼',
  };

  container.innerHTML = Object.entries(profiles).map(([name, p]) => {
    const icon = charIcons[name] || '🎭';
    const total = p.total_attempts || 0;
    const ok = p.total_ok || 0;
    const rate = total > 0 ? Math.round((ok / total) * 100) : 0;
    const caveBadge = p.cave_prevention_needed ? '<span class="badge badge-warn">洞窟防止必要</span>' : '';

    return `
      <div class="profile-card">
        <h4>${icon} ${name} ${caveBadge}</h4>
        <div class="profile-stat">
          <span>成功率</span>
          <span class="value">${rate}% (${ok}/${total})</span>
        </div>
        <div class="profile-stat">
          <span>外見設定</span>
          <span class="value" style="font-size:0.75rem">${p.established_appearance || '未設定'}</span>
        </div>
        ${p.notes ? `<div class="profile-stat"><span>注意</span><span class="value" style="color:var(--accent-gold);font-size:0.75rem">${p.notes}</span></div>` : ''}
        ${(p.failed_prompt_patterns || []).length > 0 ? `
          <div style="margin-top:8px;font-size:0.75rem;color:var(--accent-red)">
            失敗パターン: ${p.failed_prompt_patterns.slice(0, 3).join(' / ')}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

// ========================================
// フィードバック送信
// ========================================
async function sendFeedback() {
  const project = document.getElementById('fb-project').value.trim();
  const sceneId = document.getElementById('fb-scene').value.trim();
  const result = document.getElementById('fb-result').value;
  const memo = document.getElementById('fb-memo').value.trim();

  if (!project || !sceneId) {
    alert('プロジェクト名とシーン番号は必須です');
    return;
  }

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project, scene_id: parseInt(sceneId), result, memo }),
    });
    const data = await res.json();
    if (data.success) {
      alert('フィードバックを記録しました');
      document.getElementById('fb-memo').value = '';
      loadLog();
    } else {
      alert(data.error || 'エラーが発生しました');
    }
  } catch (e) {
    alert('送信に失敗しました');
  }
}

// ========================================
// 初期化
// ========================================
document.addEventListener('DOMContentLoaded', () => {
  checkConfig();
  loadLog();
});
