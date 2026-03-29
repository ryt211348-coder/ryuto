/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useCallback, useRef } from 'react'

declare const gapi: any

const SCOPES = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/spreadsheets',
].join(' ')

const DISCOVERY_DOCS = [
  'https://www.googleapis.com/discovery/v1/apis/drive/v3/rest',
  'https://sheets.googleapis.com/$discovery/rest?version=v4',
  'https://docs.googleapis.com/$discovery/rest?version=v1',
]

function loadGapiScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.getElementById('gapi-script')) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.id = 'gapi-script'
    script.src = 'https://apis.google.com/js/api.js'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Google API script'))
    document.head.appendChild(script)
  })
}

export function useGoogleAPI() {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const initPromiseRef = useRef<Promise<void> | null>(null)

  const initGoogle = useCallback(
    async (clientId: string, apiKey: string): Promise<void> => {
      if (initPromiseRef.current) {
        return initPromiseRef.current
      }

      const promise = (async () => {
        setIsLoading(true)
        setError(null)

        try {
          await loadGapiScript()

          await new Promise<void>((resolve, reject) => {
            gapi.load('client:auth2', {
              callback: () => resolve(),
              onerror: () => reject(new Error('Failed to load gapi client')),
            })
          })

          await gapi.client.init({
            apiKey,
            clientId,
            discoveryDocs: DISCOVERY_DOCS,
            scope: SCOPES,
          })

          setIsInitialized(true)
        } catch (err) {
          const message =
            err instanceof Error ? err.message : 'Google API initialization failed'
          setError(message)
          initPromiseRef.current = null
          throw err
        } finally {
          setIsLoading(false)
        }
      })()

      initPromiseRef.current = promise
      return promise
    },
    []
  )

  return { isInitialized, isLoading, error, initGoogle }
}
