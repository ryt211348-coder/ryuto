import React, { useState } from 'react'
import type { WeeklyReport as WeeklyReportType } from '../../types'
import { PLATFORM_LABELS, METRIC_LABELS } from '../../types'
import { useStore } from '../../store/useStore'
import { generateWeeklyReport } from '../../services/claude'

const WeeklyReportPage: React.FC = () => {
  const { kpis, tasks, weeklyReports, addWeeklyReport, addLog } = useStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)

    const result = await generateWeeklyReport(kpis, tasks)

    if (result.ok) {
      addWeeklyReport(result.report)
      setExpandedIds((prev) => new Set(prev).add(result.report.id))
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        action: '週次レポート生成',
        decision: `${result.report.weekStart} 〜 ${result.report.weekEnd} のレポートを生成`,
        reason: 'ユーザーリクエスト',
        result: '生成完了',
      })
    } else {
      setError(result.error)
    }

    setLoading(false)
  }

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const sortedReports = [...weeklyReports].sort(
    (a, b) => new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime()
  )

  const getAchievementColor = (rate: number): string => {
    if (rate >= 100) return '#10b981'
    if (rate >= 80) return '#f59e0b'
    return '#ef4444'
  }

  const renderReport = (report: WeeklyReportType) => {
    const isExpanded = expandedIds.has(report.id)

    return (
      <div
        key={report.id}
        className="report-card"
        style={{
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          marginBottom: '12px',
          overflow: 'hidden',
        }}
      >
        <button
          className="report-header"
          onClick={() => toggleExpand(report.id)}
          style={{
            width: '100%',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 16px',
            background: isExpanded ? '#f3f4f6' : '#fff',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <div>
            <strong>{report.weekStart} 〜 {report.weekEnd}</strong>
            <span style={{ marginLeft: '12px', fontSize: '12px', color: '#9ca3af' }}>
              生成日時: {new Date(report.generatedAt).toLocaleString('ja-JP')}
            </span>
          </div>
          <span style={{ fontSize: '18px', color: '#6b7280' }}>
            {isExpanded ? '\u25BC' : '\u25B6'}
          </span>
        </button>

        {isExpanded && (
          <div className="report-body" style={{ padding: '16px', borderTop: '1px solid #e5e7eb' }}>
            {/* KPI Achievement Table */}
            <div className="report-section" style={{ marginBottom: '24px' }}>
              <h4 style={{ marginBottom: '8px' }}>KPI達成状況</h4>
              {report.kpiSummary.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>プラットフォーム</th>
                      <th style={{ padding: '8px' }}>指標</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>目標</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>実績</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>達成率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.kpiSummary.map((kpi, index) => (
                      <tr key={index} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '8px' }}>{PLATFORM_LABELS[kpi.platform]}</td>
                        <td style={{ padding: '8px' }}>{METRIC_LABELS[kpi.metric]}</td>
                        <td style={{ padding: '8px', textAlign: 'right' }}>{kpi.target.toLocaleString()}</td>
                        <td style={{ padding: '8px', textAlign: 'right' }}>{kpi.actual.toLocaleString()}</td>
                        <td style={{
                          padding: '8px',
                          textAlign: 'right',
                          fontWeight: 'bold',
                          color: getAchievementColor(kpi.achievementRate),
                        }}>
                          {kpi.achievementRate}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ color: '#9ca3af' }}>KPIデータなし</p>
              )}
            </div>

            {/* Gap Analysis */}
            <div className="report-section" style={{ marginBottom: '24px' }}>
              <h4 style={{ marginBottom: '8px' }}>ギャップ分析</h4>
              <div style={{
                padding: '12px',
                background: '#fefce8',
                borderRadius: '6px',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.6',
                fontSize: '14px',
              }}>
                {report.gapAnalysis}
              </div>
            </div>

            {/* Next Week Actions */}
            <div className="report-section">
              <h4 style={{ marginBottom: '8px' }}>来週のアクションアイテム</h4>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
                {report.nextWeekActions.map((action, index) => (
                  <li key={index} style={{ fontSize: '14px' }}>{action}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="weekly-report">
      <div className="page-header">
        <h2 className="page-title">週次レポート</h2>
        <p className="page-subtitle">KPI達成率・ギャップ分析・翌週アクション提案</p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <button
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={loading}
          style={{
            padding: '10px 20px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '15px',
          }}
        >
          {loading ? '生成中...' : '週次レポートを生成'}
        </button>
        {error && (
          <div style={{ marginTop: '12px', color: '#ef4444' }}>
            {error}
          </div>
        )}
      </div>

      {/* Reports List */}
      <section>
        <h3>レポート一覧 ({sortedReports.length}件)</h3>
        {sortedReports.length === 0 ? (
          <div className="empty-state" style={{ padding: '24px', color: '#9ca3af', textAlign: 'center' }}>
            <p>レポートはまだ生成されていません。</p>
            <p>KPIデータを登録してから「週次レポートを生成」ボタンでレポートを作成してください。</p>
          </div>
        ) : (
          sortedReports.map(renderReport)
        )}
      </section>
    </div>
  )
}

export default WeeklyReportPage
