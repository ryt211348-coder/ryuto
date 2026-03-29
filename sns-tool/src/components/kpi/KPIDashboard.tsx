import { useState } from 'react'
import type { Platform, MetricType, KPIEntry } from '../../types'
import { PLATFORM_LABELS, METRIC_LABELS } from '../../types'
import { useStore } from '../../store/useStore'
import { syncKPIData } from '../../services/googleSheets'
import KPIChart from './KPIChart'

const platforms: Platform[] = ['tiktok', 'instagram', 'youtube']
const metrics: MetricType[] = ['views', 'followers', 'likes', 'comments', 'shares', 'engagement_rate']

export default function KPIDashboard() {
  const { kpis, addKPI, removeKPI, settings } = useStore()

  const [platform, setPlatform] = useState<Platform>('tiktok')
  const [metric, setMetric] = useState<MetricType>('views')
  const [target, setTarget] = useState('')
  const [actual, setActual] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0])
  const [note, setNote] = useState('')
  const [syncing, setSyncing] = useState(false)

  const handleAdd = () => {
    if (!target || !actual || !date) return

    const entry: KPIEntry = {
      id: crypto.randomUUID(),
      platform,
      metric,
      target: Number(target),
      actual: Number(actual),
      date,
      note: note || undefined,
    }

    addKPI(entry)
    setTarget('')
    setActual('')
    setNote('')
  }

  const handleSync = async () => {
    if (!settings.kpiSheetId) {
      alert('Google SheetsのシートIDが設定されていません。設定画面からKPIシートIDを入力してください。')
      return
    }

    setSyncing(true)
    try {
      const result = await syncKPIData(settings.kpiSheetId, kpis)
      if (result.ok) {
        // Update store with merged data
        const store = useStore.getState()
        // Clear and re-add all merged KPIs
        for (const kpi of store.kpis) {
          store.removeKPI(kpi.id)
        }
        for (const kpi of result.merged) {
          store.addKPI(kpi)
        }
        alert(`同期完了: ${result.syncedCount}件のデータを同期しました。`)
      } else {
        alert(`同期エラー: ${result.error}`)
      }
    } catch (err) {
      alert(`同期に失敗しました: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSyncing(false)
    }
  }

  const sortedKpis = [...kpis].sort((a, b) => b.date.localeCompare(a.date))

  return (
    <div className="kpi-dashboard">
      <h2 className="kpi-dashboard-title">KPI管理</h2>

      {/* Add KPI Form */}
      <div className="kpi-form">
        <h3 className="kpi-form-title">KPIを追加</h3>
        <div className="kpi-form-grid">
          <div className="kpi-form-field">
            <label className="kpi-form-label">プラットフォーム</label>
            <select
              className="kpi-form-select"
              value={platform}
              onChange={(e) => setPlatform(e.target.value as Platform)}
            >
              {platforms.map((p) => (
                <option key={p} value={p}>{PLATFORM_LABELS[p]}</option>
              ))}
            </select>
          </div>

          <div className="kpi-form-field">
            <label className="kpi-form-label">指標</label>
            <select
              className="kpi-form-select"
              value={metric}
              onChange={(e) => setMetric(e.target.value as MetricType)}
            >
              {metrics.map((m) => (
                <option key={m} value={m}>{METRIC_LABELS[m]}</option>
              ))}
            </select>
          </div>

          <div className="kpi-form-field">
            <label className="kpi-form-label">目標値</label>
            <input
              className="kpi-form-input"
              type="number"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="0"
            />
          </div>

          <div className="kpi-form-field">
            <label className="kpi-form-label">実績値</label>
            <input
              className="kpi-form-input"
              type="number"
              value={actual}
              onChange={(e) => setActual(e.target.value)}
              placeholder="0"
            />
          </div>

          <div className="kpi-form-field">
            <label className="kpi-form-label">日付</label>
            <input
              className="kpi-form-input"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          <div className="kpi-form-field">
            <label className="kpi-form-label">メモ（任意）</label>
            <input
              className="kpi-form-input"
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="メモを入力..."
            />
          </div>
        </div>

        <div className="kpi-form-actions">
          <button className="kpi-form-submit" onClick={handleAdd}>
            追加
          </button>
          <button
            className="kpi-form-sync"
            onClick={handleSync}
            disabled={syncing}
          >
            {syncing ? '同期中...' : 'Google Sheetsと同期'}
          </button>
        </div>
      </div>

      {/* Chart */}
      <KPIChart kpis={kpis} />

      {/* KPI Table */}
      <div className="kpi-table-wrapper">
        <h3 className="kpi-table-title">KPI一覧</h3>
        {sortedKpis.length === 0 ? (
          <p className="kpi-table-empty">KPIデータがありません。</p>
        ) : (
          <table className="kpi-table">
            <thead>
              <tr>
                <th>日付</th>
                <th>プラットフォーム</th>
                <th>指標</th>
                <th>目標</th>
                <th>実績</th>
                <th>達成率</th>
                <th>メモ</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sortedKpis.map((kpi) => {
                const rate = kpi.target > 0
                  ? ((kpi.actual / kpi.target) * 100).toFixed(1)
                  : '-'
                return (
                  <tr key={kpi.id}>
                    <td>{kpi.date}</td>
                    <td>{PLATFORM_LABELS[kpi.platform]}</td>
                    <td>{METRIC_LABELS[kpi.metric]}</td>
                    <td>{kpi.target.toLocaleString()}</td>
                    <td>{kpi.actual.toLocaleString()}</td>
                    <td>{rate}%</td>
                    <td>{kpi.note || '-'}</td>
                    <td>
                      <button
                        className="kpi-table-delete"
                        onClick={() => removeKPI(kpi.id)}
                      >
                        削除
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
