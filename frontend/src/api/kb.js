import http from './http'

/**
 * 获取知识库列表
 * GET /kb
 */
export function getKbs() {
    return http.get('/kb')
}

/**
 * 获取单个知识库详情
 * GET /kb/{kb_id}
 */
export function getKbDetail(kbId) {
    return http.get(`/kb/${kbId}`)
}

/**
 * 创建知识库 (Super-Admin Only)
 * POST /kb
 * @param {{ name: string, display_name: string, description?: string }} data
 */
export function createKb(data) {
    return http.post('/kb', data)
}

/**
 * 删除知识库 (Super-Admin Only)
 * DELETE /kb/{kb_id}
 */
export function deleteKb(kbId) {
    return http.delete(`/kb/${kbId}`)
}
