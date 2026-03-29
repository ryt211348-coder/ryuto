import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { KPIEntry, Platform } from '../../types'
import { PLATFORM_LABELS, METRIC_LABELS } from '../../types'

interface KPIChartProps {
  kpis?: KPIEntry[]
}

export default function KPIChart({ kpis = [] }: KPIChartProps) {
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | 'all'>('all')

  const platforms: Platform[] = ['tiktok', 'instagram', 'youtube']

  const filtered = selectedPlatform === 'all'
    ? kpis
    : kpis.filter((k) => k.platform === selectedPlatform)

  // Group by platform + metric for the chart
  const grouped = new Map<string, { label: string; target: number; actual: number }>()
  for (const entry of filtered) {
    const key = `${entry.platform}_${entry.metric}`
    const existing = grouped.get(key)
    if (existing) {
      existing.target += entry.target
      existing.actual += entry.actual
    } else {
      grouped.set(key, {
        label: `${PLATFORM_LABELS[entry.platform]} - ${METRIC_LABELS[entry.metric]}`,
        target: entry.target,
        actual: entry.actual,
      })
    }
  }

  const chartData = Array.from(grouped.values())

  return (
    <div className="kpi-chart">
      <div className="kpi-chart-header">
        <h3 className="kpi-chart-title">KPI チャート</h3>
        <div className="kpi-chart-filter">
          <label className="kpi-chart-filter-label">プラットフォーム:</label>
          <select
            className="kpi-chart-select"
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value as Platform | 'all')}
          >
            <option value="all">すべて</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                {PLATFORM_LABELS[p]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {chartData.length === 0 ? (
        <p className="kpi-chart-empty">表示するデータがありません。</p>
      ) : (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" angle={-25} textAnchor="end" interval={0} height={80} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="target" name="目標" fill="#8884d8" />
            <Bar dataKey="actual" name="実績" fill="#82ca9d" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
