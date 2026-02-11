/**
 * HTTP helpers for frontend API calls.
 */

type ErrorPayload = {
  detail?: unknown
  message?: unknown
}

/**
 * Normalize API base URL (adds https:// if protocol is missing).
 */
export function normalizeApiBaseUrl(value?: string | null): string | null {
  if (!value) {
    return null
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }

  const withProtocol = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed.replace(/^\/+/, '')}`

  try {
    const parsed = new URL(withProtocol)
    const cleanPath = parsed.pathname.replace(/\/+$/, '')
    return `${parsed.protocol}//${parsed.host}${cleanPath}`
  } catch {
    return null
  }
}

/**
 * Resolve runtime API base URL from env, then window location fallbacks.
 */
export function getApiBaseUrl(): string {
  const normalizedEnv = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_URL)
  if (normalizedEnv) {
    return normalizedEnv
  }

  if (typeof window !== 'undefined') {
    const { hostname, host, protocol } = window.location

    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `http://${hostname}:8000`
    }

    return `${protocol}//${host}`
  }

  return 'http://localhost:8000'
}

/**
 * Parse response body as JSON safely. Returns null for empty or invalid payloads.
 */
export async function parseJsonResponse<T>(response: Response): Promise<T | null> {
  const rawBody = await response.text()
  if (!rawBody) {
    return null
  }

  try {
    return JSON.parse(rawBody) as T
  } catch {
    return null
  }
}

/**
 * Extract a user-friendly error message from a JSON payload.
 */
export function getErrorMessageFromPayload(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') {
    return fallback
  }

  const maybeError = payload as ErrorPayload

  if (typeof maybeError.detail === 'string' && maybeError.detail.trim()) {
    return maybeError.detail
  }

  if (typeof maybeError.message === 'string' && maybeError.message.trim()) {
    return maybeError.message
  }

  return fallback
}
