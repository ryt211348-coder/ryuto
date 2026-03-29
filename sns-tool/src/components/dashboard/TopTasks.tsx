import React from 'react'
import type { Task } from '../../types'
import { DELEGATION_ICONS, DELEGATION_LABELS } from '../../types'
import { useStore } from '../../store/useStore'

const TopTasks: React.FC = () => {
  const tasks = useStore((s) => s.tasks)

  const topTasks = [...tasks]
    .filter((t) => t.status !== 'completed')
    .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0))
    .slice(0, 3)

  if (topTasks.length === 0) {
    return (
      <div className="top-tasks-empty">
        <p>タスクがまだ登録されていません。タスク管理ページからタスクを追加してください。</p>
      </div>
    )
  }

  const formatDeadline = (deadline?: string): string => {
    if (!deadline) return '期限なし'
    const d = new Date(deadline)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }

  const getUrgencyLabel = (level: number): string => {
    if (level >= 4) return '高'
    if (level >= 2) return '中'
    return '低'
  }

  const getUrgencyClass = (level: number): string => {
    if (level >= 4) return 'indicator-high'
    if (level >= 2) return 'indicator-medium'
    return 'indicator-low'
  }

  return (
    <div className="top-tasks">
      {topTasks.map((task, index) => (
        <div key={task.id} className="top-task-card">
          <div className="top-task-rank">#{index + 1}</div>
          <div className="top-task-content">
            <h4 className="top-task-title">{task.title}</h4>
            <div className="top-task-meta">
              <span className="top-task-deadline">
                {formatDeadline(task.deadline)}
              </span>
              <span className="top-task-delegation">
                {DELEGATION_ICONS[task.delegation]} {DELEGATION_LABELS[task.delegation]}
              </span>
            </div>
            <div className="top-task-indicators">
              <span className={`indicator ${getUrgencyClass(task.urgency)}`}>
                緊急度: {getUrgencyLabel(task.urgency)}
              </span>
              <span className={`indicator ${getUrgencyClass(task.importance)}`}>
                重要度: {getUrgencyLabel(task.importance)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default TopTasks
