import http from './http'

export function listApiKeys() {
  return http.get('/api-keys')
}

export function createApiKey(data) {
  return http.post('/api-keys', data)
}

export function deleteApiKey(keyId) {
  return http.delete(`/api-keys/${keyId}`)
}
