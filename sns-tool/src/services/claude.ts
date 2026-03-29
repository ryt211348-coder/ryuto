import type { KPIEntry, Platform, Task, AIAnalysisResult, WeeklyReport, AppSettings, PLATFORM_LABELS, METRIC_LABELS } from '../types'

function getApiKey(): string {
  try {
    const raw = localStorage.getItem('app_settings')
    if (!raw) return ''
    const settings: AppSettings = JSON.parse(raw)
    return settings.anthropicApiKey || ''
  } catch {
    return ''
  }
}

interface ClaudeMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ClaudeResponse {
  content: { type: string; text: string }[]
  usage?: { input_tokens: number; output_tokens: number }
}

async function callClaude(messages: ClaudeMessage[], systemPrompt?: string): Promise<{ ok: true; text: string; usage?: { input_tokens: number; output_tokens: number } } | { ok: false; error: string }> {
  const apiKey = getApiKey()
  if (!apiKey) {
    return { ok: false, error: 'Anthropic APIキーが設定されていません。設定画面からAPIキーを入力してください。' }
  }

  // Log API call for cost tracking
  try {
    const logs = JSON.parse(localStorage.getItem('claude_api_logs') || '[]')
    logs.push({ timestamp: new Date().toISOString(), action: 'api_call' })
    localStorage.setItem('claude_api_logs', JSON.stringify(logs))
  } catch { /* ignore logging errors */ }

  try {
    const body: Record<string, unknown> = {
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4096,
      messages,
    }
    if (systemPrompt) {
      body.system = systemPrompt
    }

    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errBody = await res.text()
      return { ok: false, error: `Claude APIエラー (${res.status}): ${errBody}` }
    }

    const data: ClaudeResponse = await res.json()
    const text = data.content
      .filter((c) => c.type === 'text')
      .map((c) => c.text)
      .join('')

    return { ok: true, text, usage: data.usage }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `Claude API呼び出しに失敗しました: ${message}` }
  }
}

/**
 * KPIギャップを分析し、改善提案を返す
 */
export async function analyzeKPIGap(kpis: KPIEntry[]): Promise<AIAnalysisResult> {
  const kpiSummary = kpis.map((k) => {
    const gap = k.target - k.actual
    const rate = k.target > 0 ? ((k.actual / k.target) * 100).toFixed(1) : 'N/A'
    return `- ${k.platform} / ${k.metric}: 目標=${k.target}, 実績=${k.actual}, 達成率=${rate}%, ギャップ=${gap} (${k.date})`
  }).join('\n')

  const systemPrompt = `あなたはSNSマーケティングの専門アナリストです。KPIデータを分析し、具体的で実行可能な改善提案を日本語で提供してください。`

  const result = await callClaude(
    [{ role: 'user', content: `以下のKPIデータを分析して、ギャップの原因と改善アクションを提案してください。\n\n${kpiSummary}` }],
    systemPrompt,
  )

  if (!result.ok) {
    return {
      summary: result.error,
      recommendations: [],
      timestamp: new Date().toISOString(),
    }
  }

  // Parse recommendations from Claude's response
  const lines = result.text.split('\n').filter((l) => l.trim())
  const recommendations = lines.filter((l) => /^[-•\d]/.test(l.trim())).map((l) => l.replace(/^[-•\d.)\s]+/, '').trim())

  return {
    summary: result.text,
    recommendations: recommendations.length > 0 ? recommendations : [result.text],
    timestamp: new Date().toISOString(),
  }
}

/**
 * プラットフォーム向けのコンテンツ台本を生成する
 */
export async function generateScript(topic: string, platform: Platform): Promise<{ ok: true; script: string } | { ok: false; error: string }> {
  const platformNames: Record<Platform, string> = {
    tiktok: 'TikTok',
    instagram: 'Instagram',
    youtube: 'YouTube',
  }

  const systemPrompt = `あなたはSNSコンテンツクリエイターのアシスタントです。指定されたプラットフォームに最適化された台本を日本語で作成してください。`

  const prompt = `以下の条件で${platformNames[platform]}向けのコンテンツ台本を作成してください。

トピック: ${topic}
プラットフォーム: ${platformNames[platform]}

以下を含めてください:
- フック（冒頭の掴み）
- 本文の構成
- CTA（行動喚起）
- ハッシュタグ提案`

  const result = await callClaude([{ role: 'user', content: prompt }], systemPrompt)

  if (!result.ok) {
    return { ok: false, error: result.error }
  }

  return { ok: true, script: result.text }
}

/**
 * タスクの委任分類（AI全自動 / AI草案 / 手動）を判定する
 */
export async function classifyTask(task: Task): Promise<{ delegation: Task['delegation']; aiProvider: Task['aiProvider']; reason: string } | { error: string }> {
  const systemPrompt = `あなたはタスク管理AIです。タスクの内容を分析し、最適な実行方法を判定してください。
結果は以下のJSON形式で返してください:
{"delegation": "ai_full" | "ai_draft" | "human_only", "aiProvider": "claude" | "gemini" | "none", "reason": "判定理由"}`

  const prompt = `以下のタスクの最適な実行方法を判定してください。

タイトル: ${task.title}
説明: ${task.description}
カテゴリ: ${task.category}
緊急度: ${task.urgency}/5
重要度: ${task.importance}/5`

  const result = await callClaude([{ role: 'user', content: prompt }], systemPrompt)

  if (!result.ok) {
    return { error: result.error }
  }

  try {
    // Extract JSON from response
    const jsonMatch = result.text.match(/\{[\s\S]*?\}/)
    if (!jsonMatch) {
      return { error: 'AIの応答からJSON形式の結果を抽出できませんでした。' }
    }
    const parsed = JSON.parse(jsonMatch[0])
    return {
      delegation: parsed.delegation || 'human_only',
      aiProvider: parsed.aiProvider || 'none',
      reason: parsed.reason || '',
    }
  } catch {
    return { error: 'AIの応答を解析できませんでした。' }
  }
}

/**
 * 週次レポートを生成する
 */
export async function generateWeeklyReport(
  kpis: KPIEntry[],
  tasks: Task[],
): Promise<{ ok: true; report: WeeklyReport } | { ok: false; error: string }> {
  const now = new Date()
  const weekStart = new Date(now)
  weekStart.setDate(now.getDate() - now.getDay())
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekStart.getDate() + 6)

  const formatDate = (d: Date) => d.toISOString().split('T')[0]

  const kpiSummary = kpis.map((k) => {
    const rate = k.target > 0 ? ((k.actual / k.target) * 100).toFixed(1) : 'N/A'
    return `${k.platform}/${k.metric}: 目標${k.target} → 実績${k.actual} (達成率${rate}%)`
  }).join('\n')

  const taskSummary = tasks.map((t) =>
    `[${t.status}] ${t.title} (緊急度${t.urgency}/重要度${t.importance})`
  ).join('\n')

  const systemPrompt = `あなたはSNS運用マネージャーのアシスタントです。週次の振り返りレポートを作成してください。
ギャップ分析と来週のアクションプランを含めてください。アクションプランは改行区切りのリスト形式で出力してください。`

  const prompt = `以下のデータから今週の振り返りレポートを作成してください。

■ KPIデータ:
${kpiSummary}

■ タスク進捗:
${taskSummary}

以下の形式で出力してください:
【ギャップ分析】
（分析内容）

【来週のアクション】
- アクション1
- アクション2
...`

  const result = await callClaude([{ role: 'user', content: prompt }], systemPrompt)

  if (!result.ok) {
    return { ok: false, error: result.error }
  }

  // Parse actions from response
  const actionLines = result.text
    .split('\n')
    .filter((l) => l.trim().startsWith('-') || l.trim().startsWith('・'))
    .map((l) => l.replace(/^[\s-・]+/, '').trim())
    .filter(Boolean)

  // Extract gap analysis section
  const gapMatch = result.text.match(/【ギャップ分析】([\s\S]*?)(?=【|$)/)
  const gapAnalysis = gapMatch ? gapMatch[1].trim() : result.text

  const report: WeeklyReport = {
    id: `report_${Date.now()}`,
    weekStart: formatDate(weekStart),
    weekEnd: formatDate(weekEnd),
    kpiSummary: kpis.map((k) => ({
      platform: k.platform,
      metric: k.metric,
      target: k.target,
      actual: k.actual,
      achievementRate: k.target > 0 ? Math.round((k.actual / k.target) * 100) : 0,
    })),
    gapAnalysis,
    nextWeekActions: actionLines.length > 0 ? actionLines : ['レポート本文を確認してください'],
    generatedAt: new Date().toISOString(),
  }

  return { ok: true, report }
}
