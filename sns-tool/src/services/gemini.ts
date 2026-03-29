import type { Platform, AIAnalysisResult, AppSettings } from '../types'

function getApiKey(): string {
  try {
    const raw = localStorage.getItem('app_settings')
    if (!raw) return ''
    const settings: AppSettings = JSON.parse(raw)
    return settings.geminiApiKey || ''
  } catch {
    return ''
  }
}

interface GeminiResponse {
  candidates?: {
    content: {
      parts: { text: string }[]
    }
  }[]
  error?: { message: string; code: number }
}

async function callGemini(prompt: string): Promise<{ ok: true; text: string } | { ok: false; error: string }> {
  const apiKey = getApiKey()
  if (!apiKey) {
    return { ok: false, error: 'Gemini APIキーが設定されていません。設定画面からAPIキーを入力してください。' }
  }

  // Log API call for cost tracking
  try {
    const logs = JSON.parse(localStorage.getItem('gemini_api_logs') || '[]')
    logs.push({ timestamp: new Date().toISOString(), action: 'api_call' })
    localStorage.setItem('gemini_api_logs', JSON.stringify(logs))
  } catch { /* ignore logging errors */ }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [
          {
            parts: [{ text: prompt }],
          },
        ],
      }),
    })

    if (!res.ok) {
      const errBody = await res.text()
      return { ok: false, error: `Gemini APIエラー (${res.status}): ${errBody}` }
    }

    const data: GeminiResponse = await res.json()

    if (data.error) {
      return { ok: false, error: `Gemini APIエラー: ${data.error.message}` }
    }

    const text = data.candidates?.[0]?.content?.parts?.map((p) => p.text).join('') || ''
    if (!text) {
      return { ok: false, error: 'Gemini APIから空のレスポンスが返されました。' }
    }

    return { ok: true, text }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `Gemini API呼び出しに失敗しました: ${message}` }
  }
}

/**
 * 指定トピック・プラットフォームのトレンドをリサーチする
 */
export async function researchTrend(topic: string, platform: Platform): Promise<AIAnalysisResult> {
  const platformNames: Record<Platform, string> = {
    tiktok: 'TikTok',
    instagram: 'Instagram',
    youtube: 'YouTube',
  }

  const prompt = `あなたはSNSトレンドアナリストです。以下の条件でトレンドリサーチを行い、日本語で結果をまとめてください。

トピック: ${topic}
プラットフォーム: ${platformNames[platform]}

以下を含めてください:
- 現在のトレンド概要
- 関連するハッシュタグや話題
- コンテンツ制作に活かせるポイント
- 推奨するコンテンツの方向性`

  const result = await callGemini(prompt)

  if (!result.ok) {
    return {
      summary: result.error,
      recommendations: [],
      timestamp: new Date().toISOString(),
    }
  }

  const recommendations = result.text
    .split('\n')
    .filter((l) => /^[-•・\d]/.test(l.trim()))
    .map((l) => l.replace(/^[-•・\d.)\s]+/, '').trim())
    .filter(Boolean)

  return {
    summary: result.text,
    recommendations: recommendations.length > 0 ? recommendations : [result.text],
    timestamp: new Date().toISOString(),
  }
}

/**
 * 競合アカウントを分析する
 */
export async function analyzeCompetitor(accountUrl: string): Promise<AIAnalysisResult> {
  const prompt = `あなたはSNS競合分析の専門家です。以下のアカウントURLから読み取れる情報をもとに、競合分析を日本語で行ってください。

アカウントURL: ${accountUrl}

以下の観点で分析してください:
- アカウントの特徴と強み
- コンテンツ戦略の推測
- エンゲージメント施策
- 自アカウントに取り入れられるポイント
- 差別化のための提案

※URLから直接データを取得できない場合は、一般的な競合分析フレームワークに基づいた分析観点を提示してください。`

  const result = await callGemini(prompt)

  if (!result.ok) {
    return {
      summary: result.error,
      recommendations: [],
      timestamp: new Date().toISOString(),
    }
  }

  const recommendations = result.text
    .split('\n')
    .filter((l) => /^[-•・\d]/.test(l.trim()))
    .map((l) => l.replace(/^[-•・\d.)\s]+/, '').trim())
    .filter(Boolean)

  return {
    summary: result.text,
    recommendations: recommendations.length > 0 ? recommendations : [result.text],
    timestamp: new Date().toISOString(),
  }
}

/**
 * 業界ニュースを収集する
 */
export async function collectIndustryNews(keywords: string[]): Promise<AIAnalysisResult> {
  const prompt = `あなたはSNSマーケティング業界のニュースアナリストです。以下のキーワードに関連する最新の業界動向やニュースについて、日本語でまとめてください。

キーワード: ${keywords.join(', ')}

以下を含めてください:
- 関連する最新の動向やトレンド
- SNS運用に影響を与えうるアルゴリズム変更や新機能
- コンテンツ戦略への示唆
- 注目すべきポイント

※リアルタイムのニュースではなく、あなたの知識に基づいた業界動向の分析を提供してください。`

  const result = await callGemini(prompt)

  if (!result.ok) {
    return {
      summary: result.error,
      recommendations: [],
      timestamp: new Date().toISOString(),
    }
  }

  const recommendations = result.text
    .split('\n')
    .filter((l) => /^[-•・\d]/.test(l.trim()))
    .map((l) => l.replace(/^[-•・\d.)\s]+/, '').trim())
    .filter(Boolean)

  return {
    summary: result.text,
    recommendations: recommendations.length > 0 ? recommendations : [result.text],
    timestamp: new Date().toISOString(),
  }
}
