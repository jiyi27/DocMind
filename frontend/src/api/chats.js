import http from './http'

export function getChatSessions(params = {}) {
  return http.get('/chats', { params })
}

export function getChatSessionDetail(sessionId) {
  return http.get(`/chats/${sessionId}`)
}
