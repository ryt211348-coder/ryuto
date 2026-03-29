const { Client, GatewayIntentBits, Partials } = require('discord.js');
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

// ===== 設定 =====
const CONFIG = {
  token: process.env.DISCORD_BOT_TOKEN || '',
  guildId: process.env.DISCORD_GUILD_ID || '',
  userName: process.env.DISCORD_USER_NAME || 'りゅうと',
  anthropicKey: process.env.ANTHROPIC_API_KEY || '',
  port: Number(process.env.PORT) || 3001,
};

// ===== データ保存 =====
const DATA_FILE = path.join(__dirname, 'tasks.json');

function loadTasks() {
  try {
    if (fs.existsSync(DATA_FILE)) return JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
  } catch (e) { console.error('Failed to load tasks:', e.message); }
  return [];
}

function saveTasks(tasks) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(tasks, null, 2), 'utf-8');
}

let tasks = loadTasks();

// ===== カテゴリ定義 =====
const CATEGORIES = [
  '企画', '台本・スクリプト', '撮影手配', '編集確認', '納品確認',
  '投稿', '数値分析', 'クリエイター管理', 'CW確認・返信',
  'Discord連絡', 'リサーチ', 'ミーティング', 'その他'
];

// ===== Claude APIでタスク分析 =====
async function analyzeMessageAsTask(content, author, channelName) {
  if (!CONFIG.anthropicKey) {
    return {
      isTask: true,
      title: content.slice(0, 60),
      description: content,
      category: 'その他',
      urgency: 3,
      importance: 3,
      delegation: 'ai_draft',
      aiProvider: 'claude',
    };
  }

  const prompt = `あなたはSNSアカウント運営（美容系 TikTok/Instagram/YouTube）のタスク管理AIです。
以下のDiscordメッセージを分析してください。

チャンネル: #${channelName}
送信者: ${author}
メッセージ: ${content}

以下のJSON形式で回答してください:
{
  "isTask": true/false (タスクや作業依頼・確認事項を含むか),
  "title": "タスクタイトル（30文字以内）",
  "description": "タスクの詳細説明",
  "category": "${CATEGORIES.join(' / ')} のいずれか",
  "urgency": 1-5 (緊急度),
  "importance": 1-5 (重要度),
  "delegation": "ai_full / ai_draft / human_only",
  "aiProvider": "claude / gemini / none",
  "status": "pending / in_progress / completed (メッセージから推測)"
}

タスクでない雑談やあいさつの場合は {"isTask": false} だけ返してください。`;

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': CONFIG.anthropicKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 500,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    const data = await res.json();
    const text = data.content?.[0]?.text || '';
    const match = text.match(/\{[\s\S]*\}/);
    if (match) return JSON.parse(match[0]);
  } catch (e) {
    console.error('Claude API error:', e.message);
  }

  return { isTask: false };
}

// ===== Discord Bot =====
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Message, Partials.Channel],
});

client.once('ready', () => {
  console.log(`✅ Bot起動: ${client.user.tag}`);
  console.log(`📡 サーバー数: ${client.guilds.cache.size}`);
});

// 新しいメッセージを監視
client.on('messageCreate', async (message) => {
  // Botのメッセージは無視
  if (message.author.bot) return;

  // 指定サーバーのみ
  if (CONFIG.guildId && message.guild?.id !== CONFIG.guildId) return;

  const content = message.content.trim();
  if (!content) return;

  console.log(`📨 [#${message.channel.name}] ${message.author.displayName}: ${content.slice(0, 50)}...`);

  // メッセージをタスクとして分析
  const result = await analyzeMessageAsTask(
    content,
    message.author.displayName,
    message.channel.name
  );

  if (result.isTask) {
    const task = {
      id: `discord_${message.id}`,
      title: result.title || content.slice(0, 60),
      description: result.description || content,
      category: result.category || 'その他',
      urgency: result.urgency || 3,
      importance: result.importance || 3,
      delegation: result.delegation || 'ai_draft',
      aiProvider: result.aiProvider || 'claude',
      status: result.status || 'pending',
      priority_score: (result.urgency || 3) * 2 + (result.importance || 3) * 2,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      source: 'discord',
      sourceChannel: message.channel.name,
      sourceAuthor: message.author.displayName,
      sourceMessageId: message.id,
      sourceUrl: message.url,
    };

    // 重複チェック
    const exists = tasks.some(t => t.sourceMessageId === message.id);
    if (!exists) {
      tasks.push(task);
      saveTasks(tasks);
      console.log(`✅ タスク追加: ${task.title} [${task.category}] 緊急${task.urgency} 重要${task.importance}`);
    }
  }
});

// ===== 過去メッセージ取得 =====
async function fetchHistoryFromChannel(channel, limit = 50) {
  try {
    const messages = await channel.messages.fetch({ limit });
    const sorted = [...messages.values()].sort((a, b) => a.createdTimestamp - b.createdTimestamp);
    let added = 0;

    for (const msg of sorted) {
      if (msg.author.bot || !msg.content.trim()) continue;

      const exists = tasks.some(t => t.sourceMessageId === msg.id);
      if (exists) continue;

      const result = await analyzeMessageAsTask(
        msg.content,
        msg.author.displayName,
        channel.name
      );

      if (result.isTask) {
        tasks.push({
          id: `discord_${msg.id}`,
          title: result.title || msg.content.slice(0, 60),
          description: result.description || msg.content,
          category: result.category || 'その他',
          urgency: result.urgency || 3,
          importance: result.importance || 3,
          delegation: result.delegation || 'ai_draft',
          aiProvider: result.aiProvider || 'claude',
          status: result.status || 'pending',
          priority_score: (result.urgency || 3) * 2 + (result.importance || 3) * 2,
          createdAt: msg.createdAt.toISOString(),
          updatedAt: new Date().toISOString(),
          source: 'discord',
          sourceChannel: channel.name,
          sourceAuthor: msg.author.displayName,
          sourceMessageId: msg.id,
          sourceUrl: msg.url,
        });
        added++;
      }

      // レート制限対策
      await new Promise(r => setTimeout(r, 500));
    }

    saveTasks(tasks);
    return added;
  } catch (e) {
    console.error(`Error fetching from #${channel.name}:`, e.message);
    return 0;
  }
}

// ===== Express API =====
const app = express();
app.use(cors());
app.use(express.json());

// タスク一覧取得
app.get('/api/tasks', (req, res) => {
  res.json(tasks);
});

// タスクステータス更新
app.patch('/api/tasks/:id', (req, res) => {
  const idx = tasks.findIndex(t => t.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'Task not found' });
  tasks[idx] = { ...tasks[idx], ...req.body, updatedAt: new Date().toISOString() };
  saveTasks(tasks);
  res.json(tasks[idx]);
});

// タスク削除
app.delete('/api/tasks/:id', (req, res) => {
  tasks = tasks.filter(t => t.id !== req.params.id);
  saveTasks(tasks);
  res.json({ ok: true });
});

// 過去メッセージ取得（手動トリガー）
app.post('/api/fetch-history', async (req, res) => {
  const { channelName, limit } = req.body;
  const guild = client.guilds.cache.get(CONFIG.guildId);
  if (!guild) return res.status(400).json({ error: 'サーバーが見つかりません' });

  let totalAdded = 0;

  if (channelName) {
    const channel = guild.channels.cache.find(c => c.name === channelName);
    if (channel) totalAdded = await fetchHistoryFromChannel(channel, limit || 50);
  } else {
    // 全テキストチャンネルから取得
    const textChannels = guild.channels.cache.filter(c => c.isTextBased() && !c.isVoiceBased());
    for (const [, channel] of textChannels) {
      const added = await fetchHistoryFromChannel(channel, limit || 20);
      totalAdded += added;
    }
  }

  res.json({ added: totalAdded, total: tasks.length });
});

// Bot情報
app.get('/api/status', (req, res) => {
  res.json({
    botReady: client.isReady(),
    botUser: client.user?.tag || null,
    guildName: client.guilds.cache.get(CONFIG.guildId)?.name || null,
    taskCount: tasks.length,
    channels: client.guilds.cache.get(CONFIG.guildId)?.channels.cache
      .filter(c => c.isTextBased() && !c.isVoiceBased())
      .map(c => ({ id: c.id, name: c.name })) || [],
  });
});

// ===== 起動 =====
app.listen(CONFIG.port, () => {
  console.log(`🌐 API server: http://localhost:${CONFIG.port}`);
});

if (CONFIG.token) {
  client.login(CONFIG.token).catch(e => {
    console.error('❌ Botログイン失敗:', e.message);
    console.log('DISCORD_BOT_TOKEN を確認してください');
  });
} else {
  console.warn('⚠️ DISCORD_BOT_TOKEN が未設定です');
  console.log('.env ファイルを作成してトークンを設定してください');
  console.log('cp .env.example .env');
}
