import type { KPIEntry, Platform, MetricType } from '../types'

declare const gapi: {
  client: {
    sheets: {
      spreadsheets: {
        values: {
          get: (params: {
            spreadsheetId: string
            range: string
          }) => Promise<{ result: { values?: string[][] } }>
          update: (params: {
            spreadsheetId: string
            range: string
            valueInputOption: string
            resource: { values: (string | number)[][] }
          }) => Promise<{ result: { updatedCells: number } }>
          append: (params: {
            spreadsheetId: string
            range: string
            valueInputOption: string
            insertDataOption: string
            resource: { values: (string | number)[][] }
          }) => Promise<{ result: unknown }>
        }
      }
    }
  }
}

/**
 * スプレッドシートからKPIデータを読み取る
 * シートのカラム想定: id | platform | metric | target | actual | date | note
 */
export async function readKPISheet(
  sheetId: string,
): Promise<{ ok: true; kpis: KPIEntry[] } | { ok: false; error: string }> {
  try {
    const res = await gapi.client.sheets.spreadsheets.values.get({
      spreadsheetId: sheetId,
      range: 'KPI!A2:G',  // Skip header row
    })

    const rows = res.result.values || []
    const kpis: KPIEntry[] = rows
      .filter((row) => row.length >= 6)
      .map((row) => ({
        id: row[0] || `kpi_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        platform: row[1] as Platform,
        metric: row[2] as MetricType,
        target: Number(row[3]) || 0,
        actual: Number(row[4]) || 0,
        date: row[5] || '',
        note: row[6] || undefined,
      }))

    return { ok: true, kpis }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `KPIシートの読み取りに失敗しました: ${message}` }
  }
}

/**
 * KPIデータをスプレッドシートに書き込む
 */
export async function writeKPISheet(
  sheetId: string,
  data: KPIEntry[],
): Promise<{ ok: true; updatedCells: number } | { ok: false; error: string }> {
  try {
    const values: (string | number)[][] = data.map((k) => [
      k.id,
      k.platform,
      k.metric,
      k.target,
      k.actual,
      k.date,
      k.note || '',
    ])

    const res = await gapi.client.sheets.spreadsheets.values.update({
      spreadsheetId: sheetId,
      range: 'KPI!A2:G',
      valueInputOption: 'USER_ENTERED',
      resource: { values },
    })

    return { ok: true, updatedCells: res.result.updatedCells }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `KPIシートへの書き込みに失敗しました: ${message}` }
  }
}

/**
 * 進捗管理シートからタスクデータを読み取る
 * シートのカラム想定: id | title | description | status | urgency | importance | delegation | category | deadline
 */
export async function readProgressSheet(
  sheetId: string,
): Promise<{ ok: true; tasks: Record<string, unknown>[] } | { ok: false; error: string }> {
  try {
    const res = await gapi.client.sheets.spreadsheets.values.get({
      spreadsheetId: sheetId,
      range: '進捗管理!A2:I',  // Skip header row
    })

    const rows = res.result.values || []
    const tasks = rows
      .filter((row) => row.length >= 4)
      .map((row) => ({
        id: row[0] || '',
        title: row[1] || '',
        description: row[2] || '',
        status: row[3] || 'pending',
        urgency: Number(row[4]) || 3,
        importance: Number(row[5]) || 3,
        delegation: row[6] || 'human_only',
        category: row[7] || '',
        deadline: row[8] || undefined,
      }))

    return { ok: true, tasks }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `進捗管理シートの読み取りに失敗しました: ${message}` }
  }
}

/**
 * KPIデータの双方向同期を行う
 * ローカルとシートの両方から最新データをマージする
 */
export async function syncKPIData(
  sheetId: string,
  localKPIs: KPIEntry[],
): Promise<{ ok: true; merged: KPIEntry[]; syncedCount: number } | { ok: false; error: string }> {
  // Read remote data
  const remoteResult = await readKPISheet(sheetId)
  if (!remoteResult.ok) {
    return { ok: false, error: remoteResult.error }
  }

  const remoteKPIs = remoteResult.kpis

  // Build maps keyed by id
  const localMap = new Map<string, KPIEntry>()
  for (const k of localKPIs) {
    localMap.set(k.id, k)
  }

  const remoteMap = new Map<string, KPIEntry>()
  for (const k of remoteKPIs) {
    remoteMap.set(k.id, k)
  }

  // Merge: prefer whichever has the more recent date, or local if same
  const allIds = new Set([...localMap.keys(), ...remoteMap.keys()])
  const merged: KPIEntry[] = []

  for (const id of allIds) {
    const local = localMap.get(id)
    const remote = remoteMap.get(id)

    if (local && remote) {
      // Both exist - keep the one with more recent date, prefer local on tie
      if (remote.date > local.date) {
        merged.push(remote)
      } else {
        merged.push(local)
      }
    } else if (local) {
      merged.push(local)
    } else if (remote) {
      merged.push(remote)
    }
  }

  // Sort by date descending
  merged.sort((a, b) => b.date.localeCompare(a.date))

  // Write merged data back to sheet
  const writeResult = await writeKPISheet(sheetId, merged)
  if (!writeResult.ok) {
    return { ok: false, error: `同期データの書き戻しに失敗しました: ${writeResult.error}` }
  }

  return { ok: true, merged, syncedCount: merged.length }
}
