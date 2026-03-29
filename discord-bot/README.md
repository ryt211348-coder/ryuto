# Discord Bot - SNS AI ツール連携

ストーク株式会社サーバーのメッセージを自動読み取り → タスクに変換する Bot。

## できること

- **リアルタイム監視**: 新しいメッセージを自動でタスクに変換
- **過去メッセージ取得**: チャンネルの過去メッセージを一括取得
- **AI分析**: Claude APIでメッセージ内容からカテゴリ・緊急度・重要度を自動判定
- **雑談スキップ**: タスクでない雑談・あいさつは自動で除外
- **API提供**: フロントエンド（SNS AI ツール）と連携するREST API

## セットアップ手順

### 1. Discord Bot を作成

1. https://discord.com/developers/applications にアクセス
2. 「New Application」→ 名前を入力（例: SNS AI Bot）
3. 左メニュー「Bot」→「Reset Token」→ **トークンをコピー**
4. **MESSAGE CONTENT INTENT** を **ON** にする（重要！）
5. 左メニュー「OAuth2」→「URL Generator」
   - SCOPES: `bot`
   - BOT PERMISSIONS: `Read Messages/View Channels`, `Read Message History`
6. 生成されたURLをブラウザで開いて、ストーク株式会社サーバーに Bot を追加

### 2. サーバーIDを取得

1. Discordアプリで「設定」→「詳細設定」→「開発者モード」を ON
2. サーバー名を右クリック →「IDをコピー」

### 3. 環境変数を設定

```bash
cd discord-bot
cp .env.example .env
```

`.env` を編集:
```
DISCORD_BOT_TOKEN=コピーしたBotトークン
DISCORD_GUILD_ID=コピーしたサーバーID
DISCORD_USER_NAME=りゅうと
ANTHROPIC_API_KEY=sk-ant-api03-...
PORT=3001
```

### 4. 起動

```bash
npm start
```

## API エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/tasks` | タスク一覧取得 |
| PATCH | `/api/tasks/:id` | タスク更新 |
| DELETE | `/api/tasks/:id` | タスク削除 |
| POST | `/api/fetch-history` | 過去メッセージからタスク取得 |
| GET | `/api/status` | Bot状態確認 |

### 過去メッセージ取得の例
```bash
# 特定チャンネルから50件取得
curl -X POST http://localhost:3001/api/fetch-history \
  -H "Content-Type: application/json" \
  -d '{"channelName": "一般", "limit": 50}'

# 全チャンネルから取得
curl -X POST http://localhost:3001/api/fetch-history \
  -H "Content-Type: application/json" \
  -d '{}'
```
