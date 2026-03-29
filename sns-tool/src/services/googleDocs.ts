import type { Platform } from '../types'
import { generateScript } from './claude'

declare const gapi: {
  client: {
    docs: {
      documents: {
        create: (params: { resource: { title: string } }) => Promise<{ result: { documentId: string; title: string } }>
        batchUpdate: (params: {
          documentId: string
          resource: { requests: Record<string, unknown>[] }
        }) => Promise<{ result: unknown }>
      }
    }
    drive: {
      files: {
        update: (params: { fileId: string; addParents?: string; removeParents?: string }) => Promise<{ result: unknown }>
      }
    }
  }
}

/**
 * Google Docsにドキュメントを作成する
 */
export async function createDocument(
  title: string,
  content: string,
): Promise<{ ok: true; documentId: string; title: string } | { ok: false; error: string }> {
  try {
    // Create blank document
    const createRes = await gapi.client.docs.documents.create({
      resource: { title },
    })

    const documentId = createRes.result.documentId

    // Insert content
    if (content) {
      await gapi.client.docs.documents.batchUpdate({
        documentId,
        resource: {
          requests: [
            {
              insertText: {
                location: { index: 1 },
                text: content,
              },
            },
          ],
        },
      })
    }

    return { ok: true, documentId, title: createRes.result.title }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { ok: false, error: `ドキュメントの作成に失敗しました: ${message}` }
  }
}

/**
 * Claudeで台本を生成し、Google Docsに保存する
 */
export async function generateAndSaveScript(
  topic: string,
  platform: Platform,
  folderId?: string,
): Promise<{ ok: true; documentId: string; script: string } | { ok: false; error: string }> {
  // Generate script via Claude
  const scriptResult = await generateScript(topic, platform)

  if (!scriptResult.ok) {
    return { ok: false, error: scriptResult.error }
  }

  const platformNames: Record<Platform, string> = {
    tiktok: 'TikTok',
    instagram: 'Instagram',
    youtube: 'YouTube',
  }

  const now = new Date()
  const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const title = `【${platformNames[platform]}台本】${topic}_${dateStr}`

  // Create document
  const docResult = await createDocument(title, scriptResult.script)

  if (!docResult.ok) {
    return { ok: false, error: docResult.error }
  }

  // Move to specified folder if provided
  if (folderId) {
    try {
      await gapi.client.drive.files.update({
        fileId: docResult.documentId,
        addParents: folderId,
      })
    } catch (err) {
      // Document was created but couldn't be moved - still return success
      console.warn('ドキュメントを指定フォルダに移動できませんでしたが、ドキュメント自体は作成されました。', err)
    }
  }

  return { ok: true, documentId: docResult.documentId, script: scriptResult.script }
}
