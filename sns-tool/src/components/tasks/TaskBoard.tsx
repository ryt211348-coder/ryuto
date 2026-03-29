import { useState } from 'react'
import type { Task, TaskDelegation, AIProvider, TaskStatus } from '../../types'
import { DELEGATION_LABELS } from '../../types'
import { useStore } from '../../store/useStore'
import { classifyTask } from '../../services/claude'
import TaskCard from './TaskCard'

type StatusFilter = 'all' | TaskStatus

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'すべて' },
  { key: 'pending', label: '未着手' },
  { key: 'in_progress', label: '進行中' },
  { key: 'completed', label: '完了' },
]

const delegationOptions: TaskDelegation[] = ['ai_full', 'ai_draft', 'human_only']
const aiProviderOptions: AIProvider[] = ['claude', 'gemini', 'none']

const AI_PROVIDER_LABELS: Record<AIProvider, string> = {
  claude: 'Claude',
  gemini: 'Gemini',
  none: 'なし',
}

function calculatePriorityScore(
  urgency: number,
  importance: number,
  delegation: TaskDelegation,
  deadline?: string,
): number {
  const delegationFactor = delegation === 'ai_full' ? 1 : delegation === 'ai_draft' ? 2 : 3

  let deadlineFactor = 0
  if (deadline) {
    const now = Date.now()
    const dl = new Date(deadline).getTime()
    deadlineFactor = Math.max(0, 5 - Math.floor((dl - now) / 86400000))
  }

  return urgency * 2 + importance * 2 + delegationFactor + deadlineFactor
}

export default function TaskBoard() {
  const { tasks, addTask, updateTask } = useStore()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [deadline, setDeadline] = useState('')
  const [urgency, setUrgency] = useState(3)
  const [importance, setImportance] = useState(3)
  const [delegation, setDelegation] = useState<TaskDelegation>('human_only')
  const [aiProvider, setAIProvider] = useState<AIProvider>('none')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [classifying, setClassifying] = useState(false)

  const handleAdd = () => {
    if (!title.trim()) return

    const now = new Date().toISOString()
    const priorityScore = calculatePriorityScore(
      urgency,
      importance,
      delegation,
      deadline || undefined,
    )

    const task: Task = {
      id: crypto.randomUUID(),
      title: title.trim(),
      description: description.trim(),
      status: 'pending',
      urgency,
      importance,
      delegation,
      aiProvider,
      deadline: deadline || undefined,
      priority_score: priorityScore,
      category: category.trim(),
      createdAt: now,
      updatedAt: now,
    }

    addTask(task)
    setTitle('')
    setDescription('')
    setCategory('')
    setDeadline('')
    setUrgency(3)
    setImportance(3)
    setDelegation('human_only')
    setAIProvider('none')
  }

  const handleBulkClassify = async () => {
    const unclassified = tasks.filter(
      (t) => t.delegation === 'human_only' && t.aiProvider === 'none' && t.status !== 'completed',
    )

    if (unclassified.length === 0) {
      alert('分類対象のタスクがありません。')
      return
    }

    setClassifying(true)
    let successCount = 0
    let errorCount = 0

    for (const task of unclassified) {
      const result = await classifyTask(task)
      if ('error' in result) {
        errorCount++
      } else {
        const priorityScore = calculatePriorityScore(
          task.urgency,
          task.importance,
          result.delegation,
          task.deadline,
        )
        updateTask(task.id, {
          delegation: result.delegation,
          aiProvider: result.aiProvider,
          priority_score: priorityScore,
          updatedAt: new Date().toISOString(),
        })
        successCount++
      }
    }

    setClassifying(false)
    alert(`分類完了: ${successCount}件成功、${errorCount}件失敗`)
  }

  // Recalculate priority scores and sort
  const filteredTasks = tasks
    .filter((t) => statusFilter === 'all' || t.status === statusFilter)
    .map((t) => ({
      ...t,
      priority_score: t.priority_score ?? calculatePriorityScore(
        t.urgency,
        t.importance,
        t.delegation,
        t.deadline,
      ),
    }))
    .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0))

  return (
    <div className="task-board">
      <h2 className="task-board-title">タスク管理</h2>

      {/* Add Task Form */}
      <div className="task-form">
        <h3 className="task-form-title">タスクを追加</h3>
        <div className="task-form-grid">
          <div className="task-form-field task-form-field-wide">
            <label className="task-form-label">タイトル</label>
            <input
              className="task-form-input"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="タスク名を入力..."
            />
          </div>

          <div className="task-form-field task-form-field-wide">
            <label className="task-form-label">説明</label>
            <textarea
              className="task-form-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="タスクの詳細..."
              rows={2}
            />
          </div>

          <div className="task-form-field">
            <label className="task-form-label">カテゴリ</label>
            <input
              className="task-form-input"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="例: コンテンツ制作"
            />
          </div>

          <div className="task-form-field">
            <label className="task-form-label">期限</label>
            <input
              className="task-form-input"
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
            />
          </div>

          <div className="task-form-field">
            <label className="task-form-label">緊急度 (1-5)</label>
            <select
              className="task-form-select"
              value={urgency}
              onChange={(e) => setUrgency(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <div className="task-form-field">
            <label className="task-form-label">重要度 (1-5)</label>
            <select
              className="task-form-select"
              value={importance}
              onChange={(e) => setImportance(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <div className="task-form-field">
            <label className="task-form-label">委任方法</label>
            <select
              className="task-form-select"
              value={delegation}
              onChange={(e) => setDelegation(e.target.value as TaskDelegation)}
            >
              {delegationOptions.map((d) => (
                <option key={d} value={d}>{DELEGATION_LABELS[d]}</option>
              ))}
            </select>
          </div>

          <div className="task-form-field">
            <label className="task-form-label">AIプロバイダー</label>
            <select
              className="task-form-select"
              value={aiProvider}
              onChange={(e) => setAIProvider(e.target.value as AIProvider)}
            >
              {aiProviderOptions.map((p) => (
                <option key={p} value={p}>{AI_PROVIDER_LABELS[p]}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="task-form-actions">
          <button className="task-form-submit" onClick={handleAdd}>
            追加
          </button>
          <button
            className="task-form-classify"
            onClick={handleBulkClassify}
            disabled={classifying}
          >
            {classifying ? '分類中...' : 'AIでタスク分類'}
          </button>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="task-board-tabs">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            className={`task-board-tab ${statusFilter === tab.key ? 'task-board-tab-active' : ''}`}
            onClick={() => setStatusFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Task List */}
      <div className="task-board-list">
        {filteredTasks.length === 0 ? (
          <p className="task-board-empty">タスクがありません。</p>
        ) : (
          filteredTasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))
        )}
      </div>
    </div>
  )
}
