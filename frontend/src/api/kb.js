import http from './http'

/**
 * Get Knowledge Base list
 * GET /kb
 */
export function getKbs() {
    return http.get('/kb')
}

/**
 * Get single Knowledge Base details
 * GET /kb/{kb_id}
 */
export function getKbDetail(kbId) {
    return http.get(`/kb/${kbId}`)
}

/**
 * Update Knowledge Base metadata
 * PATCH /kb/{kb_id}
 */
export function updateKb(kbId, data) {
    return http.patch(`/kb/${kbId}`, data)
}

/**
 * Update Knowledge Base embedding connection settings
 * PATCH /kb/{kb_id}/embedding-connection
 */
export function updateKbEmbeddingConnection(kbId, data) {
    return http.patch(`/kb/${kbId}/embedding-connection`, data)
}

/**
 * Create Knowledge Base (Super-Admin Only)
 * GET /kb/embedding-options
 */
export function getKbEmbeddingOptions() {
    return http.get('/kb/embedding-options')
}

/**
 * Create Knowledge Base (Super-Admin Only)
 * POST /kb
 * @param {{
 *   name: string,
 *   display_name: string,
 *   description?: string,
 *   embedding?: {
 *     provider: string,
 *     model?: string,
 *     base_url?: string,
 *     api_key?: string
 *   }
 * }} data
 */
export function createKb(data) {
    return http.post('/kb', data)
}

/**
 * Delete Knowledge Base (Super-Admin Only)
 * DELETE /kb/{kb_id}
 */
export function deleteKb(kbId) {
    return http.delete(`/kb/${kbId}`)
}
