// ===== KPI =====
export type Platform = 'tiktok' | 'instagram' | 'youtube'
export type MetricType = 'views' | 'followers' | 'likes' | 'comments' | 'shares' | 'engagement_rate'

export interface KPIEntry {
  id: string
  platform: Platform
  metric: MetricType
  target: number
  actual: number
  date: string // YYYY-MM-DD
  note?: string
}

export interface KPIGoal {
  id: string
  platform: Platform
  metric: MetricType
  targetValue: number
  deadline: string
  createdAt: string
}

// ===== Tasks =====
export type TaskDelegation = 'ai_full' | 'ai_draft' | 'human_only'
export type TaskStatus = 'pending' | 'in_progress' | 'waiting_approval' | 'completed'
export type AIProvider = 'claude' | 'gemini' | 'none'

export interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
  urgency: number // 1-5
  importance: number // 1-5, KPI contribution
  delegation: TaskDelegation
  aiProvider: AIProvider
  deadline?: string
  priority_score?: number
  category: string
  createdAt: string
  updatedAt: string
  completedAt?: string
  aiOutput?: string
}

// ===== Google Drive =====
export interface DriveFile {
  id: string
  name: string
  mimeType: string
  modifiedTime: string
  parents?: string[]
  webViewLink?: string
  size?: string
}

export interface DriveFolder {
  id: string
  name: string
  files: DriveFile[]
  subfolders: DriveFolder[]
}

// ===== Automation =====
export interface AutomationItem {
  id: string
  taskTitle: string
  delegation: TaskDelegation
  aiProvider: AIProvider
  description: string
  status: 'ready' | 'running' | 'completed' | 'error'
  lastRun?: string
  output?: string
}

// ===== Cost =====
export interface ServicePlan {
  service: string
  plan: string
  monthlyLimit: string
  currentUsage: string
  usagePercent: number
  status: 'ok' | 'warning' | 'exceeded'
  details: string
}

// ===== Report =====
export interface WeeklyReport {
  id: string
  weekStart: string
  weekEnd: string
  kpiSummary: {
    platform: Platform
    metric: MetricType
    target: number
    actual: number
    achievementRate: number
  }[]
  gapAnalysis: string
  nextWeekActions: string[]
  generatedAt: string
}

// ===== AI Analysis =====
export interface AIAnalysisResult {
  summary: string
  recommendations: string[]
  timestamp: string
}

// ===== Settings =====
export interface AppSettings {
  anthropicApiKey: string
  geminiApiKey: string
  googleClientId: string
  googleApiKey: string
  driveRootFolderId: string
  kpiSheetId: string
  progressSheetId: string
}

// ===== Logs =====
export interface ActionLog {
  id: string
  timestamp: string
  action: string
  decision: string
  reason: string
  result: string
}

// ===== Platform labels =====
export const PLATFORM_LABELS: Record<Platform, string> = {
  tiktok: 'TikTok',
  instagram: 'Instagram',
  youtube: 'YouTube',
}

export const METRIC_LABELS: Record<MetricType, string> = {
  views: '再生数',
  followers: 'フォロワー',
  likes: 'いいね',
  comments: 'コメント',
  shares: 'シェア',
  engagement_rate: 'エンゲージメント率',
}

export const DELEGATION_LABELS: Record<TaskDelegation, string> = {
  ai_full: 'AI全自動',
  ai_draft: 'AI草案→承認',
  human_only: '手動対応',
}

export const DELEGATION_ICONS: Record<TaskDelegation, string> = {
  ai_full: '\u{1F916}',
  ai_draft: '\u2705',
  human_only: '\u{1F464}',
}
