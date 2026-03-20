import http from './http'

/**
 * @param {object} params
 * @param {string} params.query
 * @param {string} params.kbName
 * @param {number} params.topK
 */
export function searchDocuments({ query, kbName, topK }) {
  return http.post('/search', { query, kbName, topK })
}
