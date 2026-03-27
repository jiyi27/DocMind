import http from './http'

export function getRuntimeSettings() {
  return http.get('/admin/settings')
}

export function updateLlmSettings(data) {
  return http.put('/admin/settings/llm', data)
}

export function updateChatSettings(data) {
  return http.put('/admin/settings/chat', data)
}

export function updateRetrievalSettings(data) {
  return http.put('/admin/settings/retrieval', data)
}
