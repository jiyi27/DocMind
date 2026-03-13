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
 * Create Knowledge Base (Super-Admin Only)
 * POST /kb
 * @param {{ name: string, display_name: string, description?: string }} data
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
