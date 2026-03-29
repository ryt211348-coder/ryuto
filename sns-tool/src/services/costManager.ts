import type { ServicePlan } from '../types'

interface APILogEntry {
  timestamp: string
  action: string
}

interface CostCheckResult {
  allowed: boolean
  message: string
}

function getLogCount(key: string, withinDays: number = 30): number {
  try {
    const logs: APILogEntry[] = JSON.parse(localStorage.getItem(key) || '[]')
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - withinDays)
    const cutoffStr = cutoff.toISOString()
    return logs.filter((l) => l.timestamp >= cutoffStr).length
  } catch {
    return 0
  }
}

function incrementLogCount(key: string): void {
  try {
    const logs: APILogEntry[] = JSON.parse(localStorage.getItem(key) || '[]')
    logs.push({ timestamp: new Date().toISOString(), action: 'api_call' })
    // Keep only last 90 days of logs to avoid localStorage bloat
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - 90)
    const cutoffStr = cutoff.toISOString()
    const trimmed = logs.filter((l) => l.timestamp >= cutoffStr)
    localStorage.setItem(key, JSON.stringify(trimmed))
  } catch { /* ignore storage errors */ }
}

// Claude Sonnet pricing: ~$3/MTok input, ~$15/MTok output
// Rough estimate: ~$0.01 per typical API call (avg ~1K input + 1K output tokens)
const ESTIMATED_COST_PER_CLAUDE_CALL = 0.01
const CLAUDE_MONTHLY_BUDGET_DEFAULT = 10.0 // $10 default budget

// Gemini 2.0 Flash: free tier allows 15 RPM, 1M TPM, 1500 RPD
const GEMINI_FREE_TIER_DAILY_LIMIT = 1500
const GEMINI_FREE_TIER_RPM = 15

// Google APIs: Drive/Docs/Sheets have generous quotas
const GOOGLE_API_DAILY_QUOTA = 10000 // queries per day (typical default)

/**
 * ローカルログからClaude APIの使用量を推定する
 */
export function checkAnthropicUsage(apiKey: string): {
  callCount: number
  estimatedCostUSD: number
  budgetUSD: number
  usagePercent: number
  status: 'ok' | 'warning' | 'exceeded'
} {
  if (!apiKey) {
    return { callCount: 0, estimatedCostUSD: 0, budgetUSD: CLAUDE_MONTHLY_BUDGET_DEFAULT, usagePercent: 0, status: 'ok' }
  }

  const callCount = getLogCount('claude_api_logs', 30)
  const estimatedCostUSD = callCount * ESTIMATED_COST_PER_CLAUDE_CALL
  const budgetUSD = CLAUDE_MONTHLY_BUDGET_DEFAULT
  const usagePercent = Math.round((estimatedCostUSD / budgetUSD) * 100)

  let status: 'ok' | 'warning' | 'exceeded' = 'ok'
  if (usagePercent >= 100) {
    status = 'exceeded'
  } else if (usagePercent >= 80) {
    status = 'warning'
  }

  return { callCount, estimatedCostUSD, budgetUSD, usagePercent, status }
}

/**
 * Gemini無料枠の使用状況を確認する
 */
export function checkGeminiUsage(apiKey: string): {
  dailyCalls: number
  dailyLimit: number
  usagePercent: number
  status: 'ok' | 'warning' | 'exceeded'
} {
  if (!apiKey) {
    return { dailyCalls: 0, dailyLimit: GEMINI_FREE_TIER_DAILY_LIMIT, usagePercent: 0, status: 'ok' }
  }

  const dailyCalls = getLogCount('gemini_api_logs', 1)
  const usagePercent = Math.round((dailyCalls / GEMINI_FREE_TIER_DAILY_LIMIT) * 100)

  let status: 'ok' | 'warning' | 'exceeded' = 'ok'
  if (dailyCalls >= GEMINI_FREE_TIER_DAILY_LIMIT) {
    status = 'exceeded'
  } else if (usagePercent >= 80) {
    status = 'warning'
  }

  return { dailyCalls, dailyLimit: GEMINI_FREE_TIER_DAILY_LIMIT, usagePercent, status }
}

/**
 * Google API (Drive/Docs/Sheets) のクォータ状況を確認する
 */
export function checkGoogleAPIQuota(): {
  dailyCalls: number
  dailyLimit: number
  usagePercent: number
  status: 'ok' | 'warning' | 'exceeded'
} {
  const dailyCalls = getLogCount('google_api_logs', 1)
  const usagePercent = Math.round((dailyCalls / GOOGLE_API_DAILY_QUOTA) * 100)

  let status: 'ok' | 'warning' | 'exceeded' = 'ok'
  if (dailyCalls >= GOOGLE_API_DAILY_QUOTA) {
    status = 'exceeded'
  } else if (usagePercent >= 80) {
    status = 'warning'
  }

  return { dailyCalls, dailyLimit: GOOGLE_API_DAILY_QUOTA, usagePercent, status }
}

/**
 * 全サービスのプラン状況を返す
 */
export function getServicePlans(): ServicePlan[] {
  let anthropicKey = ''
  let geminiKey = ''
  try {
    const raw = localStorage.getItem('app_settings')
    if (raw) {
      const settings = JSON.parse(raw)
      anthropicKey = settings.anthropicApiKey || ''
      geminiKey = settings.geminiApiKey || ''
    }
  } catch { /* ignore */ }

  const claude = checkAnthropicUsage(anthropicKey)
  const gemini = checkGeminiUsage(geminiKey)
  const google = checkGoogleAPIQuota()

  const plans: ServicePlan[] = [
    {
      service: 'Claude API (Anthropic)',
      plan: ' 従量課金',
      monthlyLimit: `$${claude.budgetUSD.toFixed(2)}/月（推定予算）`,
      currentUsage: `$${claude.estimatedCostUSD.toFixed(2)}（${claude.callCount}回呼び出し）`,
      usagePercent: claude.usagePercent,
      status: claude.status,
      details: anthropicKey
        ? `今月のAPI呼び出し: ${claude.callCount}回、推定コスト: $${claude.estimatedCostUSD.toFixed(2)}`
        : 'APIキー未設定',
    },
    {
      service: 'Gemini API (Google)',
      plan: '無料枠',
      monthlyLimit: `${GEMINI_FREE_TIER_DAILY_LIMIT}リクエスト/日、${GEMINI_FREE_TIER_RPM}RPM`,
      currentUsage: `${gemini.dailyCalls}/${gemini.dailyLimit}リクエスト（本日）`,
      usagePercent: gemini.usagePercent,
      status: gemini.status,
      details: geminiKey
        ? `本日のAPI呼び出し: ${gemini.dailyCalls}回（上限: ${gemini.dailyLimit}回/日）`
        : 'APIキー未設定',
    },
    {
      service: 'Google APIs (Drive/Docs/Sheets)',
      plan: '無料枠',
      monthlyLimit: `${GOOGLE_API_DAILY_QUOTA.toLocaleString()}リクエスト/日`,
      currentUsage: `${google.dailyCalls}/${google.dailyLimit.toLocaleString()}リクエスト（本日）`,
      usagePercent: google.usagePercent,
      status: google.status,
      details: `本日のAPI呼び出し: ${google.dailyCalls}回（上限: ${google.dailyLimit.toLocaleString()}回/日）`,
    },
  ]

  return plans
}

/**
 * アクション実行前のコストチェック（プリフライト）
 */
export function canExecuteAction(
  action: string,
  estimatedCost: number = 0,
): CostCheckResult {
  let anthropicKey = ''
  let geminiKey = ''
  try {
    const raw = localStorage.getItem('app_settings')
    if (raw) {
      const settings = JSON.parse(raw)
      anthropicKey = settings.anthropicApiKey || ''
      geminiKey = settings.geminiApiKey || ''
    }
  } catch { /* ignore */ }

  // Determine which service the action will use
  const isClaudeAction = action.includes('claude') || action.includes('analyze') || action.includes('generate') || action.includes('classify')
  const isGeminiAction = action.includes('gemini') || action.includes('research') || action.includes('trend') || action.includes('competitor') || action.includes('news')
  const isGoogleAction = action.includes('drive') || action.includes('docs') || action.includes('sheets') || action.includes('google')

  if (isClaudeAction) {
    if (!anthropicKey) {
      return { allowed: false, message: 'Anthropic APIキーが設定されていません。設定画面から入力してください。' }
    }
    const usage = checkAnthropicUsage(anthropicKey)
    const projectedCost = usage.estimatedCostUSD + (estimatedCost || ESTIMATED_COST_PER_CLAUDE_CALL)
    if (projectedCost > usage.budgetUSD) {
      return {
        allowed: false,
        message: `Claude APIの推定予算を超過します（現在: $${usage.estimatedCostUSD.toFixed(2)} / 予算: $${usage.budgetUSD.toFixed(2)}）。`,
      }
    }
    if (usage.status === 'warning') {
      return {
        allowed: true,
        message: `注意: Claude APIの使用量が予算の${usage.usagePercent}%に達しています。`,
      }
    }
    return { allowed: true, message: '' }
  }

  if (isGeminiAction) {
    if (!geminiKey) {
      return { allowed: false, message: 'Gemini APIキーが設定されていません。設定画面から入力してください。' }
    }
    const usage = checkGeminiUsage(geminiKey)
    if (usage.status === 'exceeded') {
      return {
        allowed: false,
        message: `Gemini APIの日次無料枠を超過しました（${usage.dailyCalls}/${usage.dailyLimit}リクエスト）。明日まで待つか、有料プランへのアップグレードをご検討ください。`,
      }
    }
    if (usage.status === 'warning') {
      return {
        allowed: true,
        message: `注意: Gemini APIの本日の使用量が無料枠の${usage.usagePercent}%に達しています。`,
      }
    }
    return { allowed: true, message: '' }
  }

  if (isGoogleAction) {
    const usage = checkGoogleAPIQuota()
    if (usage.status === 'exceeded') {
      return {
        allowed: false,
        message: `Google APIの日次クォータを超過しました（${usage.dailyCalls}/${usage.dailyLimit.toLocaleString()}リクエスト）。`,
      }
    }
    if (usage.status === 'warning') {
      return {
        allowed: true,
        message: `注意: Google APIの本日の使用量がクォータの${usage.usagePercent}%に達しています。`,
      }
    }
    return { allowed: true, message: '' }
  }

  // Unknown action type - allow by default
  return { allowed: true, message: '' }
}
