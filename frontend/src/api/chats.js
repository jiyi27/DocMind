import http from './http'

export function getChatSessions(params = {}) {
  return http.get('/chats', { params })
}

export function createChatSession(body = {}) {
  return http.post('/chats', body)
}

export function getChatSessionDetail(sessionId) {
  return http.get(`/chats/${sessionId}`)
}

/**
 * Send a chat message to the RAG pipeline.
 * History is managed server-side — only the session ID and current input are needed.
 *
 * @param {string} sessionId - UUID of the active chat session
 * @param {string} chatInput - The user's current question
 * @returns {Promise<{answer: string, sources: string[], session_id: string, kb_name: string, is_first_turn: boolean}>}
 */
export function sendChatMessage(sessionId, chatInput) {
  return http.post(
    '/chat',
    { sessionId, chatInput },
    { timeout: 120000 },
  )
}

/**
 * Stream a chat message via SSE (Server-Sent Events).
 *
 * Calls POST /chat/stream and reads the response body as a stream.
 * Invokes callbacks as events arrive:
 *   onSources(sources: string[])         — fired once before text starts
 *   onChunk(text: string)                — fired for each token chunk
 *   onDone(sessionId: string)            — fired when generation is complete
 *   onError(message: string)             — fired on server-side error event
 *
 * Returns a Promise that resolves when the stream closes, or rejects on
 * network/HTTP errors.
 *
 * @param {string} sessionId
 * @param {string} chatInput
 * @param {{ onSources, onChunk, onDone, onError, signal }} callbacks
 */
export async function sendChatMessageStream(sessionId, chatInput, { onSources, onChunk, onDone, onError, signal } = {}) {
  const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const token = localStorage.getItem('token')

  const response = await fetch(`${baseURL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ sessionId, chatInput }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE lines are separated by \n\n; process all complete events in the buffer
    const parts = buffer.split('\n\n')
    buffer = parts.pop() // keep incomplete trailing chunk

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue

      const json = line.slice('data:'.length).trim()
      if (!json) continue

      let event
      try {
        event = JSON.parse(json)
      } catch {
        continue
      }

      if (event.type === 'sources') onSources?.(event.sources)
      else if (event.type === 'chunk') onChunk?.(event.text)
      else if (event.type === 'done') onDone?.(event.session_id)
      else if (event.type === 'error') onError?.(event.message)
    }
  }
}
