import type { DriveFile, AppSettings } from '../types'

declare const gapi: {
  load: (api: string, callback: () => void) => void
  client: {
    init: (config: { apiKey: string; clientId: string; discoveryDocs: string[]; scope: string }) => Promise<void>
    drive: {
      files: {
        list: (params: Record<string, unknown>) => Promise<{ result: { files: DriveFile[]; nextPageToken?: string } }>
        get: (params: Record<string, unknown>) => Promise<{ result: DriveFile }>
      }
    }
  }
}

function getSettings(): AppSettings | null {
  try {
    const raw = localStorage.getItem('app_settings')
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

/**
 * Google API (gapi) クライアントを初期化する
 */
export async function initGoogleAPI(): Promise<{ ok: true } | { ok: false; error: string }> {
  const settings = getSettings()
  if (!settings) {
    return { ok: false, error: 'アプリ設定が見つかりません。設定画面からGoogle API情報を入力してください。' }
  }

  if (!settings.googleApiKey || !settings.googleClientId) {
    return { ok: false, error: 'Google APIキーまたはクライアントIDが設定されていません。' }
  }

  try {
    await new Promise<void>((resolve, reject) => {
      if (typeof gapi === 'undefined') {
        reject(new Error('Google APIスクリプト(gapi)が読み込まれていません。index.htmlにscriptタグを追加してください。'))
        return
      }
      gapi.load('client', () => resolve())
    })

    await gapi.client.init({
      apiKey: settings.googleApiKey,
      clientId: settings.googleClientId,
      discoveryDocs: [
        'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest',
        'https://docs.googleapis.com/$discovery/rest?version=v1',
        'https://sheets.googleapis.com/$discovery/rest?version=v4',
      ],
      scope: 'https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/spreadsheets',
    })

    return { ok: true }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `Google API初期化に失敗しました: ${message}` }
  }
}

/**
 * 指定フォルダ内のファイル一覧を取得する
 */
export async function listFiles(folderId: string): Promise<{ ok: true; files: DriveFile[] } | { ok: false; error: string }> {
  try {
    const res = await gapi.client.drive.files.list({
      q: `'${folderId}' in parents and trashed = false`,
      fields: 'files(id, name, mimeType, modifiedTime, parents, webViewLink, size), nextPageToken',
      orderBy: 'modifiedTime desc',
      pageSize: 100,
    })

    return { ok: true, files: res.result.files || [] }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `ファイル一覧の取得に失敗しました: ${message}` }
  }
}

/**
 * ファイルのメタデータを取得する
 */
export async function getFileMetadata(fileId: string): Promise<{ ok: true; file: DriveFile } | { ok: false; error: string }> {
  try {
    const res = await gapi.client.drive.files.get({
      fileId,
      fields: 'id, name, mimeType, modifiedTime, parents, webViewLink, size',
    })

    return { ok: true, file: res.result }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `ファイル情報の取得に失敗しました: ${message}` }
  }
}

/**
 * フォルダの変更をポーリングで監視する
 */
export function watchFolder(
  folderId: string,
  callback: (newFiles: DriveFile[]) => void,
  intervalMs: number = 60000,
): { stop: () => void } {
  let knownFileIds: Set<string> = new Set()
  let initialized = false
  let timerId: ReturnType<typeof setInterval> | null = null

  const poll = async () => {
    const result = await listFiles(folderId)
    if (!result.ok) return

    const currentFiles = result.files
    const currentIds = new Set(currentFiles.map((f) => f.id))

    if (initialized) {
      const newFiles = currentFiles.filter((f) => !knownFileIds.has(f.id))
      if (newFiles.length > 0) {
        callback(newFiles)
      }
    }

    knownFileIds = currentIds
    initialized = true
  }

  // Initial poll
  poll()
  timerId = setInterval(poll, intervalMs)

  return {
    stop: () => {
      if (timerId !== null) {
        clearInterval(timerId)
        timerId = null
      }
    },
  }
}

/**
 * 編集者からの新規納品ファイルを検出する
 */
export async function detectNewDeliveries(folderId: string): Promise<{ ok: true; newFiles: DriveFile[] } | { ok: false; error: string }> {
  const CHECKED_KEY = `drive_checked_files_${folderId}`

  try {
    const result = await listFiles(folderId)
    if (!result.ok) {
      return { ok: false, error: result.error }
    }

    // Load previously checked file IDs
    let checkedIds: string[] = []
    try {
      checkedIds = JSON.parse(localStorage.getItem(CHECKED_KEY) || '[]')
    } catch { /* ignore parse errors */ }

    const checkedSet = new Set(checkedIds)
    const newFiles = result.files.filter((f) => !checkedSet.has(f.id))

    // Update checked list
    const allIds = result.files.map((f) => f.id)
    localStorage.setItem(CHECKED_KEY, JSON.stringify(allIds))

    return { ok: true, newFiles }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `納品ファイルの検出に失敗しました: ${message}` }
  }
}
