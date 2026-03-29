import { useState } from 'react'
import { useStore } from '../store/useStore'
import type { AppSettings } from '../types'

export default function Settings() {
  const { settings, updateSettings, addLog } = useStore()
  const [form, setForm] = useState<AppSettings>({ ...settings })
  const [saved, setSaved] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, string>>({})

  const handleChange = (key: keyof AppSettings, value: string) => {
    setForm(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const handleSave = () => {
    updateSettings(form)
    setSaved(true)
    addLog({
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      action: '設定更新',
      decision: 'API設定を保存',
      reason: 'ユーザー操作',
      result: '保存完了',
    })
    setTimeout(() => setSaved(false), 3000)
  }

  const testClaude = async () => {
    if (!form.anthropicApiKey) {
      setTestResults(prev => ({ ...prev, claude: 'APIキーを入力してください' }))
      return
    }
    setTestResults(prev => ({ ...prev, claude: 'テスト中...' }))
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': form.anthropicApiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 10,
          messages: [{ role: 'user', content: 'ping' }],
        }),
      })
      setTestResults(prev => ({
        ...prev,
        claude: res.ok ? '接続成功' : `エラー: ${res.status}`,
      }))
    } catch (err) {
      setTestResults(prev => ({ ...prev, claude: `接続失敗: ${(err as Error).message}` }))
    }
  }

  const testGemini = async () => {
    if (!form.geminiApiKey) {
      setTestResults(prev => ({ ...prev, gemini: 'APIキーを入力してください' }))
      return
    }
    setTestResults(prev => ({ ...prev, gemini: 'テスト中...' }))
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${form.geminiApiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: 'ping' }] }],
          }),
        }
      )
      setTestResults(prev => ({
        ...prev,
        gemini: res.ok ? '接続成功' : `エラー: ${res.status}`,
      }))
    } catch (err) {
      setTestResults(prev => ({ ...prev, gemini: `接続失敗: ${(err as Error).message}` }))
    }
  }

  const FIELDS: { key: keyof AppSettings; label: string; section: string; type?: string; testFn?: () => void }[] = [
    { key: 'anthropicApiKey', label: 'Anthropic API Key', section: 'AI API', type: 'password', testFn: testClaude },
    { key: 'geminiApiKey', label: 'Gemini API Key', section: 'AI API', type: 'password', testFn: testGemini },
    { key: 'googleClientId', label: 'Google Client ID', section: 'Google API' },
    { key: 'googleApiKey', label: 'Google API Key', section: 'Google API', type: 'password' },
    { key: 'driveRootFolderId', label: 'Drive ルートフォルダ ID', section: 'Google連携' },
    { key: 'kpiSheetId', label: 'KPI管理シート ID', section: 'Google連携' },
    { key: 'progressSheetId', label: '進捗管理シート ID', section: 'Google連携' },
  ]

  const sections = [...new Set(FIELDS.map(f => f.section))]

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">設定</h2>
        <p className="page-subtitle">API キー・Google 連携の設定</p>
      </div>

      <div className="settings-grid">
        {sections.map(section => (
          <div key={section} className="settings-section">
            <h3 className="settings-section-title">{section}</h3>
            {FIELDS.filter(f => f.section === section).map(field => (
              <div key={field.key} className="form-group">
                <label className="form-label">{field.label}</label>
                <div className="form-inline">
                  <input
                    type={field.type || 'text'}
                    className="form-input"
                    value={form[field.key]}
                    onChange={e => handleChange(field.key, e.target.value)}
                    placeholder={`${field.label}を入力`}
                  />
                  {field.testFn && (
                    <button className="btn btn-ghost btn-sm" onClick={field.testFn}>
                      テスト
                    </button>
                  )}
                </div>
                {testResults[field.key === 'anthropicApiKey' ? 'claude' : field.key === 'geminiApiKey' ? 'gemini' : ''] && (
                  <p className={`text-sm mt-1 ${
                    testResults[field.key === 'anthropicApiKey' ? 'claude' : 'gemini']?.includes('成功')
                      ? 'text-success' : 'text-danger'
                  }`}>
                    {testResults[field.key === 'anthropicApiKey' ? 'claude' : field.key === 'geminiApiKey' ? 'gemini' : '']}
                  </p>
                )}
              </div>
            ))}
          </div>
        ))}

        <div className="flex gap-1">
          <button className="btn btn-primary" onClick={handleSave}>設定を保存</button>
          {saved && <span className="text-success text-sm" style={{ alignSelf: 'center' }}>保存しました</span>}
        </div>
      </div>
    </div>
  )
}
