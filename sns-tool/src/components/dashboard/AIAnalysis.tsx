import React, { useState } from 'react'
import type { AIAnalysisResult } from '../../types'
import { useStore } from '../../store/useStore'
import { analyzeKPIGap } from '../../services/claude'

const AIAnalysis: React.FC = () => {
  const kpis = useStore((s) => s.kpis)
  const settings = useStore((s) => s.settings)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AIAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const hasApiKey = !!settings.anthropicApiKey

  const handleAnalyze = async () => {
    if (!hasApiKey) return

    setLoading(true)
    setError(null)
    try {
      const analysisResult = await analyzeKPIGap(kpis)
      setResult(analysisResult)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(`分析中にエラーが発生しました: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  if (!hasApiKey) {
    return (
      <div className="ai-analysis-no-key">
        <p>AI分析を利用するには、設定画面でAnthropic APIキーを設定してください。</p>
      </div>
    )
  }

  return (
    <div className="ai-analysis">
      <div className="ai-analysis-actions">
        <button
          className="ai-analysis-button"
          onClick={handleAnalyze}
          disabled={loading || kpis.length === 0}
        >
          {loading ? '分析中...' : 'AI分析を実行'}
        </button>
        {kpis.length === 0 && (
          <p className="ai-analysis-hint">KPIデータを登録すると分析が実行できます。</p>
        )}
      </div>

      {loading && (
        <div className="ai-analysis-loading">
          <div className="spinner" />
          <p>AIがKPIデータを分析しています...</p>
        </div>
      )}

      {error && (
        <div className="ai-analysis-error">
          <p>{error}</p>
        </div>
      )}

      {result && !loading && (
        <div className="ai-analysis-result">
          <div className="ai-analysis-summary">
            <h4>分析サマリー</h4>
            <p>{result.summary}</p>
          </div>
          {result.recommendations.length > 0 && (
            <div className="ai-analysis-recommendations">
              <h4>改善提案</h4>
              <ul>
                {result.recommendations.map((rec, index) => (
                  <li key={index}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="ai-analysis-timestamp">
            分析日時: {new Date(result.timestamp).toLocaleString('ja-JP')}
          </p>
        </div>
      )}
    </div>
  )
}

export default AIAnalysis
