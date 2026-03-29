# SNS AI 生産性最大化ツール

りゅうとの「指示」と「最終承認」以外は全てAIが処理する、SNSアカウント運営の生産性ツール。

## 機能（フェーズ1 MVP）

1. **KPIダッシュボード** - 目標vs実績の可視化、Claude AIによるギャップ分析
2. **優先タスク管理** - 自動スコアリング、TOP3表示、AI委譲度分類
3. **Google Drive連携** - フォルダ監視、納品ファイル検知、Docs自動生成、Sheets同期
4. **AI自動化マトリクス** - タスクの自動化分類（AI全自動/AI草案→承認/手動）
5. **コスト管理** - API使用状況、プラン内収まり確認
6. **週次レポート** - KPI達成率、ギャップ分析、翌週アクション提案

## セットアップ

### 1. 依存関係インストール

```bash
cd sns-tool
npm install
```

### 2. APIキーの設定

アプリ起動後、設定画面（⚙️）で以下を入力:

- **Anthropic API Key**: [Anthropic Console](https://console.anthropic.com/) から取得
- **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/) から取得

### 3. Google API 認証セットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 以下のAPIを有効化:
   - Google Drive API
   - Google Docs API
   - Google Sheets API
3. 認証情報 → OAuth 2.0 クライアント ID を作成（Webアプリケーション）
   - 承認済みの JavaScript 生成元: `http://localhost:3000`
   - 承認済みのリダイレクト URI: `http://localhost:3000`
4. クライアント ID を設定画面に入力
5. 認証情報 → API キー を作成し、設定画面に入力

### 4. 起動

```bash
npm run dev
```

ブラウザで `http://localhost:3000` を開く。

## 技術スタック

- **フロントエンド**: React 19 + TypeScript + Vite
- **状態管理**: Zustand（localStorage永続化）
- **グラフ**: Recharts
- **AI**: Anthropic Claude API / Google Gemini API
- **Google連携**: Drive API / Docs API / Sheets API（gapi client）

## フォルダ構成

```
sns-tool/
├── src/
│   ├── components/
│   │   ├── dashboard/    # ダッシュボード（TOP3、KPIサマリー、AI分析）
│   │   ├── kpi/          # KPI管理・グラフ
│   │   ├── tasks/        # タスクボード・カード
│   │   ├── google/       # Google連携パネル
│   │   ├── automation/   # AI自動化センター
│   │   ├── cost/         # コスト管理
│   │   ├── report/       # 週次レポート
│   │   ├── Layout.tsx    # レイアウト
│   │   ├── Sidebar.tsx   # サイドバー
│   │   └── Settings.tsx  # 設定
│   ├── services/         # API連携サービス
│   │   ├── claude.ts     # Anthropic Claude API
│   │   ├── gemini.ts     # Google Gemini API
│   │   ├── googleDrive.ts
│   │   ├── googleDocs.ts
│   │   ├── googleSheets.ts
│   │   └── costManager.ts
│   ├── store/            # Zustand ストア
│   ├── hooks/            # カスタムフック
│   ├── types/            # TypeScript型定義
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
└── tsconfig.json
```

## フェーズ2 設計メモ

以下はフェーズ2で追加予定。コンポーネント設計は拡張を考慮済み:

- **Discord連携**: `src/services/discord.ts` を追加、Webhook受け口は準備可能
- **Chrome自動化**: `src/services/browser.ts` を追加、数値取得を自動化
- **AIマルチエージェント**: `src/services/multiAgent.ts` で複数視点の壁打ち機能
- **Supabase移行**: ストアのpersist部分をSupabaseクライアントに差し替えるだけで移行可能

## コスト試算サマリー

| サービス | プラン | 月額 | MVP利用で収まるか |
|---|---|---|---|
| Anthropic Claude | API従量課金 | ~$5-10/月（利用頻度による） | ✅ |
| Google Gemini | 無料枠 | $0 | ✅（15RPM/1500RPD内） |
| Google Drive API | 無料 | $0 | ✅ |
| Google Sheets API | 無料 | $0 | ✅ |
| Google Docs API | 無料 | $0 | ✅ |

**見積もり**: 1日10-20回のAI分析利用で月額 $5-10 程度。Google APIは全て無料枠内。
