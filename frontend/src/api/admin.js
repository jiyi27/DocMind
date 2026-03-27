import http from './http'

export function getRuntimeSettings() {
  return http.get('/admin/settings')
}

export function updateRuntimeSettings(data) {
  return http.put('/admin/settings', data)
}
