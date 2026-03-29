import React from 'react'
import type { KPIEntry, Platform, MetricType } from '../../types'
import { PLATFORM_LABELS, METRIC_LABELS } from '../../types'
import { useStore } from '../../store/useStore'

interface GroupedMetric {
  platform: Platform
  metric: MetricType
  target: number
  actual: number
  achievementRate: number
}

const KPISummary: React.FC = () => {
  const kpis = useStore((s) => s.kpis)

  if (kpis.length === 0) {
    return (
      <div className="kpi-summary-empty">
        <p>KPIデータがまだ登録されていません。KPI管理ページからデータを追加してください。</p>
      </div>
    )
  }

  // Group by platform+metric, take latest entry for each
  const latestByKey = new Map<string, KPIEntry>()
  for (const kpi of kpis) {
    const key = `${kpi.platform}_${kpi.metric}`
    const existing = latestByKey.get(key)
    if (!existing || kpi.date > existing.date) {
      latestByKey.set(key, kpi)
    }
  }

  // Group by platform
  const byPlatform = new Map<Platform, GroupedMetric[]>()
  for (const kpi of latestByKey.values()) {
    const rate = kpi.target > 0 ? Math.round((kpi.actual / kpi.target) * 100) : 0
    const entry: GroupedMetric = {
      platform: kpi.platform,
      metric: kpi.metric,
      target: kpi.target,
      actual: kpi.actual,
      achievementRate: rate,
    }
    const list = byPlatform.get(kpi.platform) || []
    list.push(entry)
    byPlatform.set(kpi.platform, list)
  }

  const getAchievementColor = (rate: number): string => {
    if (rate >= 80) return 'achievement-green'
    if (rate >= 50) return 'achievement-yellow'
    return 'achievement-red'
  }

  return (
    <div className="kpi-summary">
      {Array.from(byPlatform.entries()).map(([platform, metrics]) => (
        <div key={platform} className="kpi-platform-group">
          <h4 className="kpi-platform-title">{PLATFORM_LABELS[platform]}</h4>
          <div className="kpi-metrics">
            {metrics.map((m) => (
              <div key={`${m.platform}_${m.metric}`} className="kpi-metric-row">
                <span className="kpi-metric-label">{METRIC_LABELS[m.metric]}</span>
                <div className="kpi-metric-bar-container">
                  <div className="kpi-metric-values">
                    <span>{m.actual.toLocaleString()} / {m.target.toLocaleString()}</span>
                    <span className={`kpi-achievement ${getAchievementColor(m.achievementRate)}`}>
                      {m.achievementRate}%
                    </span>
                  </div>
                  <div className="kpi-progress-track">
                    <div
                      className={`kpi-progress-fill ${getAchievementColor(m.achievementRate)}`}
                      style={{ width: `${Math.min(m.achievementRate, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export default KPISummary
