import React from 'react'
import { useStore } from '../../store/useStore'
import TopTasks from './TopTasks'
import KPISummary from './KPISummary'
import AIAnalysis from './AIAnalysis'

const Dashboard: React.FC = () => {
  const logs = useStore((s) => s.logs)

  // Use action logs as a proxy for recent activity
  const recentActivity = [...logs]
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .slice(0, 5)

  return (
    <div className="dashboard">
      <h2 className="dashboard-title">ダッシュボード</h2>

      <section className="dashboard-section">
        <h3 className="dashboard-section-title">今日の最優先タスク TOP3</h3>
        <TopTasks />
      </section>

      <section className="dashboard-section">
        <h3 className="dashboard-section-title">KPIサマリー</h3>
        <KPISummary />
      </section>

      <section className="dashboard-section">
        <h3 className="dashboard-section-title">AI分析</h3>
        <AIAnalysis />
      </section>

      <section className="dashboard-section">
        <h3 className="dashboard-section-title">最近のDrive更新</h3>
        <div className="drive-updates">
          {recentActivity.length === 0 ? (
            <div className="drive-updates-empty">
              <p>最近の更新はありません。Google Drive連携を設定すると、ここにファイルの更新情報が表示されます。</p>
            </div>
          ) : (
            <div className="drive-updates-list">
              {recentActivity.map((log) => (
                <div key={log.id} className="drive-update-card">
                  <div className="drive-update-action">{log.action}</div>
                  <div className="drive-update-detail">{log.result}</div>
                  <div className="drive-update-time">
                    {new Date(log.timestamp).toLocaleString('ja-JP')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

export default Dashboard
