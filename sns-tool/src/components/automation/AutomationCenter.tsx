import React, { useMemo, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import type { Task, TaskDelegation } from '../../types'
import { DELEGATION_LABELS, DELEGATION_ICONS } from '../../types'
import { useStore } from '../../store/useStore'

const COLORS: Record<TaskDelegation, string> = {
  ai_full: '#10b981',
  ai_draft: '#f59e0b',
  human_only: '#ef4444',
}

const AutomationCenter: React.FC = () => {
  const { tasks, updateTask, logs, addLog } = useStore()
  const [runningIds, setRunningIds] = useState<Set<string>>(new Set())

  const grouped = useMemo(() => {
    const groups: Record<TaskDelegation, Task[]> = {
      ai_full: [],
      ai_draft: [],
      human_only: [],
    }
    tasks.forEach((task) => {
      if (groups[task.delegation]) {
        groups[task.delegation].push(task)
      }
    })
    return groups
  }, [tasks])

  const pieData = useMemo(() => {
    return (['ai_full', 'ai_draft', 'human_only'] as TaskDelegation[]).map((key) => ({
      name: DELEGATION_LABELS[key],
      value: grouped[key].length,
      color: COLORS[key],
    }))
  }, [grouped])

  const handleExecute = async (task: Task) => {
    setRunningIds((prev) => new Set(prev).add(task.id))
    updateTask(task.id, { status: 'in_progress' })

    addLog({
      id: `log_${Date.now()}`,
      timestamp: new Date().toISOString(),
      action: 'AI自動実行開始',
      decision: `タスク「${task.title}」を自動実行`,
      reason: `委任区分: ${DELEGATION_LABELS[task.delegation]}`,
      result: '実行中',
    })

    // Simulate AI processing
    await new Promise((resolve) => setTimeout(resolve, 1000))

    const now = new Date().toISOString()
    updateTask(task.id, {
      status: 'completed',
      completedAt: now,
      updatedAt: now,
      aiOutput: `[自動生成] タスク「${task.title}」の処理が完了しました。AIによる分析結果とアウトプットが生成されました。`,
    })

    addLog({
      id: `log_${Date.now()}`,
      timestamp: now,
      action: 'AI自動実行完了',
      decision: `タスク「${task.title}」が完了`,
      reason: `委任区分: ${DELEGATION_LABELS[task.delegation]}`,
      result: '完了',
    })

    setRunningIds((prev) => {
      const next = new Set(prev)
      next.delete(task.id)
      return next
    })
  }

  const recentLogs = useMemo(() => {
    return [...logs]
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 10)
  }, [logs])

  const columns: TaskDelegation[] = ['ai_full', 'ai_draft', 'human_only']

  return (
    <div className="automation-center">
      <h2>自動化センター</h2>

      {/* Distribution Chart */}
      <section className="panel-section">
        <h3>タスク委任分布</h3>
        <div className="chart-container" style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <div style={{ width: 200, height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-legend">
            {pieData.map((entry) => (
              <div key={entry.name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: entry.color, display: 'inline-block' }} />
                <span>{entry.name}: {entry.value}件</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Automation Matrix */}
      <section className="panel-section">
        <h3>自動化マトリクス</h3>
        <div className="automation-matrix" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
          {columns.map((delegation) => (
            <div
              key={delegation}
              className="matrix-column"
              style={{ borderTop: `3px solid ${COLORS[delegation]}`, padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem' }}
            >
              <h4 style={{ marginBottom: '0.5rem' }}>
                {DELEGATION_ICONS[delegation]} {DELEGATION_LABELS[delegation]}
              </h4>
              <p className="task-count" style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
                {grouped[delegation].length}件のタスク
              </p>
              <div className="task-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {grouped[delegation].map((task) => (
                  <div
                    key={task.id}
                    className="task-card"
                    style={{
                      padding: '0.75rem',
                      backgroundColor: '#ffffff',
                      borderRadius: '0.375rem',
                      border: '1px solid #e5e7eb',
                    }}
                  >
                    <p style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.25rem' }}>{task.title}</p>
                    <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                      状態: {task.status} | 緊急度: {task.urgency} | 重要度: {task.importance}
                    </p>
                    {delegation === 'ai_full' && task.status !== 'completed' && (
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => handleExecute(task)}
                        disabled={runningIds.has(task.id)}
                        style={{
                          backgroundColor: COLORS.ai_full,
                          color: '#fff',
                          border: 'none',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '0.25rem',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                        }}
                      >
                        {runningIds.has(task.id) ? '実行中...' : '自動化を実行'}
                      </button>
                    )}
                    {task.aiOutput && (
                      <p style={{ fontSize: '0.75rem', color: '#059669', marginTop: '0.5rem' }}>
                        {task.aiOutput}
                      </p>
                    )}
                  </div>
                ))}
                {grouped[delegation].length === 0 && (
                  <p style={{ fontSize: '0.875rem', color: '#9ca3af', textAlign: 'center', padding: '1rem' }}>
                    タスクなし
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Execution Log */}
      <section className="panel-section">
        <h3>実行ログ</h3>
        {recentLogs.length === 0 ? (
          <p style={{ color: '#9ca3af' }}>実行ログはまだありません。</p>
        ) : (
          <table className="log-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>日時</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>アクション</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>判断</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid #e5e7eb' }}>結果</th>
              </tr>
            </thead>
            <tbody>
              {recentLogs.map((log) => (
                <tr key={log.id}>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #f3f4f6', fontSize: '0.75rem' }}>
                    {new Date(log.timestamp).toLocaleString('ja-JP')}
                  </td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #f3f4f6', fontSize: '0.875rem' }}>
                    {log.action}
                  </td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #f3f4f6', fontSize: '0.875rem' }}>
                    {log.decision}
                  </td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #f3f4f6', fontSize: '0.875rem' }}>
                    {log.result}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

export default AutomationCenter
