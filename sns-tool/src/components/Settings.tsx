import React, { useState } from 'react'
import type { AppSettings } from '../types'
import { useStore } from '../store/useStore'

interface FieldConfig {
  key: keyof AppSettings
  label: string
  type: 'password' | 'text'
  placeholder: string
  testable: boolean
}

const FIELDS: FieldConfig[] = [
  {
    key: 'anthropicApiKey',
    label: 'Anthropic APIキー',
    type: 'password',
    placeholder: 'sk-ant-...',
    testable: true,
  },
  {
    key: 'geminiApiKey',
    label: 'Gemini APIキー',
    type: 'password',
    placeholder: 'AIza...',
    testable: true,
  },
  {
    key: 'googleClientId',
    label: 'GoogleクライアントID',
    type: 'text',
    placeholder: 'xxxx.apps.googleusercontent.com',
    testable: false,
  },
  {
    key: 'googleApiKey',
    label: 'Google APIキー',
    type: 'text',
    placeholder: 'AIza...',
    testable: false,
  },
  {
    key: 'driveRootFolderId',
    label: 'DriveルートフォルダID',
    type: 'text',
    placeholder: 'フォルダIDを入力',
    testable: false,
  },
  {
    key: 'kpiSheetId',
    label: 'KPIシートID',
    type: 'text',
    placeholder: 'スプレッドシートIDを入力',
    testable: false,
  },
  {
    key: 'progressSheetId',
    label: '進捗シートID',
    type: 'text',
    placeholder: 'スプレッドシートIDを入力',
    testable: false,
  },
]

const Settings: React.FC = () => {
  const { settings, updateSettings, addLog } = useStore()
  const [form, setForm] = useState<AppSettings>({ ...settings })
  const [saved, setSaved] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})
  const [testingKey, setTestingKey] = useState<string | null>(null)

  const handleChange = (key: keyof AppSettings, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const handleSave = () => {
    updateSettings(form)
    addLog({
      id: `log_${Date.now()}`,
      timestamp: new Date().toISOString(),
      action: '設定更新',
      decision: 'API設定を保存',
      reason: 'ユーザー操作',
      result: '保存完了',
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleTestAnthropicKey = async () => {
    const apiKey = form.anthropicApiKey
    if (!apiKey) {
      setTestResults((prev) => ({
        ...prev,
        anthropicApiKey: { success: false, message: 'APIキーを入力してください。' },
      }))
      return
    }

    setTestingKey('anthropicApiKey')
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 10,
          messages: [{ role: 'user', content: 'ping' }],
        }),
      })

      if (res.ok) {
        setTestResults((prev) => ({
          ...prev,
          anthropicApiKey: { success: true, message: '接続成功' },
        }))
      } else {
        setTestResults((prev) => ({
          ...prev,
          anthropicApiKey: { success: false, message: `エラー (${res.status})` },
        }))
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setTestResults((prev) => ({
        ...prev,
        anthropicApiKey: { success: false, message: `接続失敗: ${message}` },
      }))
    }
    setTestingKey(null)
  }

  const handleTestGeminiKey = async () => {
    const apiKey = form.geminiApiKey
    if (!apiKey) {
      setTestResults((prev) => ({
        ...prev,
        geminiApiKey: { success: false, message: 'APIキーを入力してください。' },
      }))
      return
    }

    setTestingKey('geminiApiKey')
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: 'ping' }] }],
          }),
        }
      )

      if (res.ok) {
        setTestResults((prev) => ({
          ...prev,
          geminiApiKey: { success: true, message: '接続成功' },
        }))
      } else {
        setTestResults((prev) => ({
          ...prev,
          geminiApiKey: { success: false, message: `エラー (${res.status})` },
        }))
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setTestResults((prev) => ({
        ...prev,
        geminiApiKey: { success: false, message: `接続失敗: ${message}` },
      }))
    }
    setTestingKey(null)
  }

  const handleTest = (key: keyof AppSettings) => {
    if (key === 'anthropicApiKey') {
      handleTestAnthropicKey()
    } else if (key === 'geminiApiKey') {
      handleTestGeminiKey()
    }
  }

  return (
    <div className="settings">
      <div className="page-header">
        <h2 className="page-title">設定</h2>
        <p className="page-subtitle">APIキー・Google連携の設定</p>
      </div>

      <div className="settings-grid" style={{ maxWidth: '640px' }}>
        {FIELDS.map((field) => (
          <div key={field.key} className="form-group" style={{ marginBottom: '20px' }}>
            <label
              className="form-label"
              style={{
                display: 'block',
                marginBottom: '4px',
                fontWeight: 'bold',
                fontSize: '14px',
              }}
            >
              {field.label}
            </label>
            <div className="form-inline" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                type={field.type}
                className="form-input"
                value={form[field.key]}
                onChange={(e) => handleChange(field.key, e.target.value)}
                placeholder={field.placeholder}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                }}
              />
              {field.testable && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => handleTest(field.key)}
                  disabled={testingKey === field.key}
                  style={{
                    padding: '8px 12px',
                    background: '#f3f4f6',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    cursor: testingKey === field.key ? 'not-allowed' : 'pointer',
                    fontSize: '13px',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {testingKey === field.key ? 'テスト中...' : '接続テスト'}
                </button>
              )}
            </div>
            {testResults[field.key] && (
              <div
                style={{
                  marginTop: '4px',
                  fontSize: '13px',
                  color: testResults[field.key].success ? '#10b981' : '#ef4444',
                }}
              >
                {testResults[field.key].success ? '\u2713 ' : '\u2717 '}
                {testResults[field.key].message}
              </div>
            )}
          </div>
        ))}

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '24px' }}>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            style={{
              padding: '10px 24px',
              background: '#3b82f6',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '15px',
              fontWeight: 'bold',
            }}
          >
            保存
          </button>
          {saved && (
            <span style={{ color: '#10b981', fontSize: '14px' }}>
              設定を保存しました。
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default Settings
