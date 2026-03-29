import React, { useState } from 'react'
import type { DriveFile, Platform, Task } from '../../types'
import { useStore } from '../../store/useStore'
import { useGoogleAPI } from '../../hooks/useGoogleAPI'
import { initGoogleAPI, listFiles, detectNewDeliveries } from '../../services/googleDrive'
import { readKPISheet, readProgressSheet } from '../../services/googleSheets'
import { generateAndSaveScript } from '../../services/googleDocs'

const GooglePanel: React.FC = () => {
  const { settings, addTask, addLog } = useStore()
  const { isInitialized, isLoading: gapiLoading, error: gapiError, initGoogle } = useGoogleAPI()

  // Drive Explorer
  const [files, setFiles] = useState<DriveFile[]>([])
  const [driveLoading, setDriveLoading] = useState(false)
  const [driveError, setDriveError] = useState<string | null>(null)

  // Sheets Sync
  const [sheetId, setSheetId] = useState(settings.kpiSheetId || '')
  const [sheetsMessage, setSheetsMessage] = useState<string | null>(null)
  const [sheetsLoading, setSheetsLoading] = useState(false)

  // Docs Generator
  const [topic, setTopic] = useState('')
  const [platform, setPlatform] = useState<Platform>('tiktok')
  const [docsStatus, setDocsStatus] = useState<string | null>(null)
  const [docsLoading, setDocsLoading] = useState(false)

  const handleConnect = async () => {
    const result = await initGoogleAPI()
    if (result.ok) {
      await initGoogle(settings.googleClientId, settings.googleApiKey)
      if (settings.driveRootFolderId) {
        await handleLoadFiles()
      }
    } else {
      setDriveError(result.error)
    }
  }

  const handleLoadFiles = async () => {
    if (!settings.driveRootFolderId) {
      setDriveError('Drive ルートフォルダIDが設定されていません。')
      return
    }
    setDriveLoading(true)
    setDriveError(null)
    const result = await listFiles(settings.driveRootFolderId)
    if (result.ok) {
      setFiles(result.files)
    } else {
      setDriveError(result.error)
    }
    setDriveLoading(false)
  }

  const handleDetectDeliveries = async () => {
    if (!settings.driveRootFolderId) {
      setDriveError('Drive ルートフォルダIDが設定されていません。')
      return
    }
    setDriveLoading(true)
    setDriveError(null)
    const result = await detectNewDeliveries(settings.driveRootFolderId)
    if (result.ok) {
      const now = new Date().toISOString()
      result.newFiles.forEach((file) => {
        const task: Task = {
          id: `task_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
          title: `納品確認: ${file.name}`,
          description: `Driveに新規ファイルが検出されました: ${file.name} (${file.mimeType})`,
          status: 'pending',
          urgency: 3,
          importance: 3,
          delegation: 'human_only',
          aiProvider: 'none',
          category: '納品確認',
          createdAt: now,
          updatedAt: now,
        }
        addTask(task)
      })
      addLog({
        id: `log_${Date.now()}`,
        timestamp: now,
        action: '納品ファイル検知',
        decision: `${result.newFiles.length}件の新規ファイルを検出`,
        reason: 'Driveフォルダのスキャン',
        result: result.newFiles.length > 0 ? 'タスクとして追加しました' : '新規ファイルはありません',
      })
      setDriveError(
        result.newFiles.length > 0
          ? `${result.newFiles.length}件の新規納品ファイルをタスクに追加しました。`
          : '新規納品ファイルはありません。'
      )
    } else {
      setDriveError(result.error)
    }
    setDriveLoading(false)
  }

  const handleReadKPI = async () => {
    const id = sheetId || settings.kpiSheetId
    if (!id) {
      setSheetsMessage('KPIシートIDを入力してください。')
      return
    }
    setSheetsLoading(true)
    setSheetsMessage(null)
    const result = await readKPISheet(id)
    if (result.ok) {
      setSheetsMessage(`KPIデータを${result.kpis.length}件読み込みました。`)
    } else {
      setSheetsMessage(result.error)
    }
    setSheetsLoading(false)
  }

  const handleReadProgress = async () => {
    const id = sheetId || settings.progressSheetId
    if (!id) {
      setSheetsMessage('進捗シートIDを入力してください。')
      return
    }
    setSheetsLoading(true)
    setSheetsMessage(null)
    const result = await readProgressSheet(id)
    if (result.ok) {
      setSheetsMessage(`進捗データを${result.tasks.length}件読み込みました。`)
    } else {
      setSheetsMessage(result.error)
    }
    setSheetsLoading(false)
  }

  const handleGenerateDoc = async () => {
    if (!topic.trim()) {
      setDocsStatus('トピックを入力してください。')
      return
    }
    setDocsLoading(true)
    setDocsStatus('企画書を生成中...')
    const result = await generateAndSaveScript(topic, platform, settings.driveRootFolderId || undefined)
    if (result.ok) {
      setDocsStatus(`企画書を作成しました (ID: ${result.documentId})`)
      addLog({
        id: `log_${Date.now()}`,
        timestamp: new Date().toISOString(),
        action: '企画書自動生成',
        decision: `${platform}向け企画書を作成`,
        reason: `トピック: ${topic}`,
        result: `ドキュメントID: ${result.documentId}`,
      })
    } else {
      setDocsStatus(result.error)
    }
    setDocsLoading(false)
  }

  const formatMimeType = (mimeType: string): string => {
    const map: Record<string, string> = {
      'application/vnd.google-apps.folder': 'フォルダ',
      'application/vnd.google-apps.document': 'ドキュメント',
      'application/vnd.google-apps.spreadsheet': 'スプレッドシート',
      'application/vnd.google-apps.presentation': 'スライド',
      'video/mp4': '動画 (MP4)',
      'image/png': '画像 (PNG)',
      'image/jpeg': '画像 (JPEG)',
      'application/pdf': 'PDF',
    }
    return map[mimeType] || mimeType
  }

  if (!isInitialized && !settings.googleApiKey && !settings.googleClientId) {
    return (
      <div className="google-panel">
        <h2>Google連携</h2>
        <div className="setup-instructions">
          <h3>セットアップ手順</h3>
          <ol>
            <li>Google Cloud Consoleでプロジェクトを作成します。</li>
            <li>Drive API、Sheets API、Docs APIを有効化します。</li>
            <li>OAuth 2.0クライアントIDを作成します。</li>
            <li>APIキーを作成します。</li>
            <li>設定画面からGoogle Client IDとAPI Keyを入力します。</li>
            <li>DriveルートフォルダIDを設定します。</li>
          </ol>
          <p>設定が完了したら、このページからGoogle連携機能を利用できます。</p>
        </div>
      </div>
    )
  }

  return (
    <div className="google-panel">
      <h2>Google連携</h2>

      {/* Section 1: Drive Explorer */}
      <section className="panel-section">
        <h3>Drive Explorer</h3>
        <div className="section-actions">
          <button
            className="btn btn-primary"
            onClick={handleConnect}
            disabled={gapiLoading || driveLoading}
          >
            {gapiLoading ? '接続中...' : 'Driveを接続'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleLoadFiles}
            disabled={driveLoading}
          >
            ファイル一覧を更新
          </button>
          <button
            className="btn btn-accent"
            onClick={handleDetectDeliveries}
            disabled={driveLoading}
          >
            納品ファイル検知
          </button>
        </div>

        {gapiError && <p className="message message-error">{gapiError}</p>}
        {driveError && <p className="message message-info">{driveError}</p>}
        {driveLoading && <p className="message message-loading">読み込み中...</p>}

        {files.length > 0 && (
          <table className="file-table">
            <thead>
              <tr>
                <th>ファイル名</th>
                <th>種類</th>
                <th>更新日時</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.id}>
                  <td>
                    {file.webViewLink ? (
                      <a href={file.webViewLink} target="_blank" rel="noopener noreferrer">
                        {file.name}
                      </a>
                    ) : (
                      file.name
                    )}
                  </td>
                  <td>{formatMimeType(file.mimeType)}</td>
                  <td>{new Date(file.modifiedTime).toLocaleString('ja-JP')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Section 2: Sheets Sync */}
      <section className="panel-section">
        <h3>Sheets同期</h3>
        <div className="form-group">
          <label>シートID</label>
          <input
            type="text"
            className="input"
            value={sheetId}
            onChange={(e) => setSheetId(e.target.value)}
            placeholder="スプレッドシートIDを入力"
          />
        </div>
        <div className="section-actions">
          <button
            className="btn btn-primary"
            onClick={handleReadKPI}
            disabled={sheetsLoading}
          >
            KPIシート読み込み
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleReadProgress}
            disabled={sheetsLoading}
          >
            進捗シート読み込み
          </button>
        </div>
        {sheetsMessage && <p className="message message-info">{sheetsMessage}</p>}
      </section>

      {/* Section 3: Docs Generator */}
      <section className="panel-section">
        <h3>Docs自動生成</h3>
        <div className="form-group">
          <label>トピック</label>
          <input
            type="text"
            className="input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例: 朝のルーティン紹介"
          />
        </div>
        <div className="form-group">
          <label>プラットフォーム</label>
          <select
            className="select"
            value={platform}
            onChange={(e) => setPlatform(e.target.value as Platform)}
          >
            <option value="tiktok">TikTok</option>
            <option value="instagram">Instagram</option>
            <option value="youtube">YouTube</option>
          </select>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleGenerateDoc}
          disabled={docsLoading}
        >
          {docsLoading ? '生成中...' : '企画書を自動生成'}
        </button>
        {docsStatus && <p className="message message-info">{docsStatus}</p>}
      </section>
    </div>
  )
}

export default GooglePanel
