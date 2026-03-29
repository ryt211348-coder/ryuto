import type { Task, TaskStatus } from '../../types'
import { DELEGATION_LABELS, DELEGATION_ICONS } from '../../types'
import { useStore } from '../../store/useStore'

interface TaskCardProps {
  task: Task
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  pending: '未着手',
  in_progress: '進行中',
  waiting_approval: '承認待ち',
  completed: '完了',
}

const URGENCY_COLORS: Record<number, string> = {
  1: 'badge-low',
  2: 'badge-low',
  3: 'badge-medium',
  4: 'badge-high',
  5: 'badge-critical',
}

const IMPORTANCE_COLORS: Record<number, string> = {
  1: 'badge-low',
  2: 'badge-low',
  3: 'badge-medium',
  4: 'badge-high',
  5: 'badge-critical',
}

export default function TaskCard({ task }: TaskCardProps) {
  const { updateTask, removeTask } = useStore()

  const handleStatusChange = (status: TaskStatus) => {
    const updates: Partial<Task> = {
      status,
      updatedAt: new Date().toISOString(),
    }
    if (status === 'completed') {
      updates.completedAt = new Date().toISOString()
    }
    updateTask(task.id, updates)
  }

  const handleAIExecute = () => {
    // Placeholder: just move to in_progress or waiting_approval
    if (task.delegation === 'ai_full') {
      updateTask(task.id, {
        status: 'completed',
        updatedAt: new Date().toISOString(),
        completedAt: new Date().toISOString(),
        aiOutput: '(AI自動実行完了 - プレースホルダー)',
      })
    } else if (task.delegation === 'ai_draft') {
      updateTask(task.id, {
        status: 'waiting_approval',
        updatedAt: new Date().toISOString(),
        aiOutput: '(AI草案生成完了 - プレースホルダー)',
      })
    }
  }

  const deadlineDisplay = task.deadline
    ? new Date(task.deadline).toLocaleDateString('ja-JP')
    : null

  const isOverdue = task.deadline
    ? new Date(task.deadline) < new Date() && task.status !== 'completed'
    : false

  const canAIExecute = task.delegation === 'ai_full' || task.delegation === 'ai_draft'

  return (
    <div className={`task-card ${isOverdue ? 'task-card-overdue' : ''}`}>
      <div className="task-card-header">
        <h4 className="task-card-title">{task.title}</h4>
        <button
          className="task-card-delete"
          onClick={() => removeTask(task.id)}
          title="削除"
        >
          ×
        </button>
      </div>

      {task.description && (
        <p className="task-card-description">
          {task.description.length > 100
            ? `${task.description.slice(0, 100)}...`
            : task.description}
        </p>
      )}

      <div className="task-card-meta">
        {task.category && (
          <span className="task-card-category">{task.category}</span>
        )}
        {deadlineDisplay && (
          <span className={`task-card-deadline ${isOverdue ? 'task-card-deadline-overdue' : ''}`}>
            {isOverdue ? '期限切れ: ' : '期限: '}{deadlineDisplay}
          </span>
        )}
      </div>

      <div className="task-card-badges">
        <span className={`task-card-badge ${URGENCY_COLORS[task.urgency] || 'badge-medium'}`}>
          緊急度 {task.urgency}
        </span>
        <span className={`task-card-badge ${IMPORTANCE_COLORS[task.importance] || 'badge-medium'}`}>
          重要度 {task.importance}
        </span>
        {task.priority_score != null && (
          <span className="task-card-badge badge-score">
            スコア {task.priority_score}
          </span>
        )}
      </div>

      <div className="task-card-delegation">
        <span className="task-card-delegation-icon">{DELEGATION_ICONS[task.delegation]}</span>
        <span className="task-card-delegation-label">{DELEGATION_LABELS[task.delegation]}</span>
      </div>

      <div className="task-card-actions">
        <select
          className="task-card-status-select"
          value={task.status}
          onChange={(e) => handleStatusChange(e.target.value as TaskStatus)}
        >
          {(Object.keys(STATUS_LABELS) as TaskStatus[]).map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>
          ))}
        </select>

        {canAIExecute && task.status !== 'completed' && (
          <button className="task-card-ai-button" onClick={handleAIExecute}>
            AI実行
          </button>
        )}
      </div>

      {task.aiOutput && (
        <div className="task-card-ai-output">
          <span className="task-card-ai-output-label">AI出力:</span>
          <p className="task-card-ai-output-text">{task.aiOutput}</p>
        </div>
      )}
    </div>
  )
}
