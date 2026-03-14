import http from './http'

export function getChatSessions(params = {}) {
  return http.get('/chats', { params })
}

export function getChatSessionDetail(sessionId) {
  return http.get(`/chats/${sessionId}`)
}

/**
 * Send a chat message to the RAG pipeline.
 *
 * @param {string} sessionId  - UUID of the active chat session
 * @param {string} chatInput  - The user's current question
 * @param {Array<{role: 'user'|'assistant', content: string}>} messages
 *   Full conversation history prior to this turn (oldest first).
 *   The server uses this to inject context into the LLM without maintaining
 *   its own session state.
 *
 * @returns {Promise<{answer: string, sources: string[], session_id: string, kb_name: string}>}
 */
export function sendChatMessage(sessionId, chatInput, messages = []) {
  return http.post(
    '/chat',
    { sessionId, chatInput, messages },
    { timeout: 120000 }, // LLM calls can take longer than the default 30s
  )
}
