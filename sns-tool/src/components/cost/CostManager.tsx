import React, { useState } from 'react'
import type { ServicePlan } from '../../types'
import { useStore } from '../../store/useStore'
import { getServicePlans } from '../../services/costManager'

const STATUS_COLORS: Record<ServicePlan['status'], string> = {
  ok: '#10b981',
  warning: '#f59e0b',
  exceeded: '#ef4444',
}

const STATUS_LABELS: Record<ServicePlan['status'], string> = {
  ok: '正常',
  warning: '注意',
  exceeded: '超過',
}

const INITIAL_PLANS: ServicePlan[] = [
  {
    service: 'Anthropic Claude',
    plan: 'Proプラン',
    monthlyLimit: '$20/月',
    currentUsage: '$0.00',
    usagePercent: 0,
    status: 'ok',
    details: 'Claude Pro サブスクリプション: $20/月',
  },
  {
    service: 'Google Gemini',
    plan: '無料枠',
    monthlyLimit: '15 RPM / 1500 RPD',
    currentUsage: '0リクエスト',
    usagePercent: 0,
    status: 'ok',
    details: 'Gemini 2.0 Flash 無料枠: 15リクエスト/分、1500リクエスト/日',
  },
  {
    service: 'Google Drive API',
    plan: '無料',
    monthlyLimit: '10億クォータ/日',
    currentUsage: '0クォータ',
    usagePercent: 0,
    status: 'ok',
    details: 'Google Drive API 無料枠: 10億クォータ/日',
  },
  {
    service: 'Google Sheets API',
    plan: '無料',
    monthlyLimit: '300リクエスト/分',
    currentUsage: '0リクエスト',
    usagePercent: 0,
    status: 'ok',
    details: 'Google Sheets API: 300リクエスト/分（ユーザーあたり）',
  },
  {
    service: 'Google Docs API',
    plan: '無料',
    monthlyLimit: '300リクエスト/分',
    currentUsage: '0リクエスト',
    usagePercent: 0,
    status: 'ok',
    details: 'Google Docs API: 300リクエスト/分（ユーザーあたり）',
  },
]

const COST_ESTIMATES: { action: string; estimate: string }[] = [
  { action: 'KPIギャップ分析 (Claude)', estimate: '約$0.01/回' },
  { action: '台本生成 (Claude)', estimate: '約$0.02/回' },
  { action: 'タスク分類 (Claude)', estimate: '約$0.005/回' },
  { action: '週次レポート生成 (Claude)', estimate: '約$0.03/回' },
  { action: 'トレンドリサーチ (Gemini)', estimate: '無料枠内' },
  { action: 'Google Drive操作', estimate: '無料枠内' },
  { action: 'Google Sheets読み書き', estimate: '無料枠内' },
  { action: 'Google Docs作成', estimate: '無料枠内' },
]

const CostManager: React.FC = () => {
  const { servicePlans, setServicePlans, addLog } = useStore()
  const [loading, setLoading] = useState(false)

  const handleRefresh = () => {
    setLoading(true)
    const plans = getServicePlans()
    setServicePlans(plans)
    setLoading(false)
  }

  const handleInitialDiagnosis = () => {
    setLoading(true)
    setTimeout(() => {
      setServicePlans(INITIAL_PLANS)
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        action: '初回診断実行',
        decision: '全サービスのプラン情報を取得',
        reason: 'コスト管理の初期設定',
        result: '5サービスの情報を登録完了',
      })
      setLoading(false)
    }, 500)
  }

  const plans = servicePlans.length > 0 ? servicePlans : []

  return (
    <div className="cost-manager">
      <div className="page-header">
        <h2 className="page-title">コスト管理</h2>
        <p className="page-subtitle">契約プラン・API使用状況の管理</p>
      </div>

      <div className="flex gap-1 mb-2" style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button
          className="btn btn-primary"
          onClick={handleRefresh}
          disabled={loading}
          style={{
            padding: '8px 16px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          {loading ? '更新中...' : '使用状況を更新'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleInitialDiagnosis}
          disabled={loading}
          style={{
            padding: '8px 16px',
            background: '#8b5cf6',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          初回診断を実行
        </button>
      </div>

      {plans.length === 0 ? (
        <div className="empty-state" style={{ padding: '24px', background: '#f9fafb', borderRadius: '8px', textAlign: 'center', color: '#6b7280', marginBottom: '32px' }}>
          <p>サービスプランが登録されていません。</p>
          <p>「初回診断を実行」ボタンで初期データを設定するか、「使用状況を更新」で現在の使用状況を取得してください。</p>
        </div>
      ) : (
        <div className="card-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px', marginBottom: '32px' }}>
          {plans.map((plan, index) => (
            <div
              key={index}
              className="cost-card"
              style={{
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '16px',
                background: '#fff',
              }}
            >
              <div className="cost-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div>
                  <div className="cost-card-service" style={{ fontWeight: 'bold' }}>{plan.service}</div>
                  <div className="cost-card-plan" style={{ fontSize: '14px', color: '#6b7280' }}>
                    プラン: {plan.plan}
                  </div>
                </div>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    color: '#fff',
                    background: STATUS_COLORS[plan.status],
                  }}
                >
                  {STATUS_LABELS[plan.status]}
                </span>
              </div>

              <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                上限: {plan.monthlyLimit}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '12px' }}>
                使用量: {plan.currentUsage}
              </div>

              {/* Progress Bar */}
              <div className="progress-bar" style={{ background: '#e5e7eb', borderRadius: '4px', height: '8px', marginBottom: '4px', overflow: 'hidden' }}>
                <div
                  className="progress-fill"
                  style={{
                    width: `${Math.min(plan.usagePercent, 100)}%`,
                    height: '100%',
                    background: STATUS_COLORS[plan.status],
                    borderRadius: '4px',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
              <div style={{ fontSize: '12px', color: '#9ca3af', textAlign: 'right' }}>
                {plan.usagePercent}%
              </div>

              <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '8px' }}>
                {plan.details}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Cost Estimates */}
      <section style={{ marginTop: '16px' }}>
        <h3>アクション別推定コスト</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
              <th style={{ padding: '8px' }}>アクション</th>
              <th style={{ padding: '8px' }}>推定コスト</th>
            </tr>
          </thead>
          <tbody>
            {COST_ESTIMATES.map((item, index) => (
              <tr key={index} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '8px' }}>{item.action}</td>
                <td style={{ padding: '8px', color: '#6b7280' }}>{item.estimate}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}

export default CostManager
