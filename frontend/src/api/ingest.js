import http from './http'

/**
 * 上传并注入文档
 * POST /ingest/{kb_id}
 * @param {string} kbId - 目标知识库 UUID
 * @param {FormData} formData - 包含 file, title, url, doc_type, service, department
 */
export function uploadDocument(kbId, formData) {
    return http.post(`/ingest/${kbId}`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    })
}

/**
 * 获取当前用户的文档列表
 * GET /ingest/documents
 */
export function getDocuments() {
    return http.get('/ingest/documents')
}

/**
 * 获取当前用户在指定知识库的文档列表
 * GET /ingest/documents/kb/{kb_id}
 * @param {string} kbId
 */
export function getDocumentsByKb(kbId) {
    return http.get(`/ingest/documents/kb/${kbId}`)
}

/**
 * 删除文档及向量数据
 * DELETE /ingest/{doc_id}
 * @param {string} docId
 */
export function deleteDocument(docId) {
    return http.delete(`/ingest/${docId}`)
}

/**
 * 检查文档 Chunk 列表
 * GET /ingest/{doc_id}/chunks
 * @param {string} docId
 * @param {number} offset
 * @param {number} limit
 */
export function getDocumentChunks(docId, offset = 0, limit = 20) {
    return http.get(`/ingest/${docId}/chunks`, { params: { offset, limit } })
}
