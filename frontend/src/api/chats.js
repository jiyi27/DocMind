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
