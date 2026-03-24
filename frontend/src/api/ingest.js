import http from './http'

/**
 * Upload and ingest document
 * POST /ingest/{kb_id}
 * @param {string} kbId - Target Knowledge Base UUID
 * @param {FormData} formData - Contains file, metadata fields, and ingestion options
 */
export function uploadDocument(kbId, formData) {
    return http.post(`/ingest/${kbId}`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    })
}

/**
 * Get current user's document list
 * GET /ingest/documents
 */
export function getDocuments() {
    return http.get('/ingest/documents')
}

/**
 * Get a single document's metadata
 * GET /ingest/documents/{doc_id}
 * @param {string} docId
 */
export function getDocumentById(docId) {
    return http.get(`/ingest/documents/${docId}`)
}

/**
 * Get current user's document list in specified KB
 * GET /ingest/documents/kb/{kb_id}
 * @param {string} kbId
 */
export function getDocumentsByKb(kbId) {
    return http.get(`/ingest/documents/kb/${kbId}`)
}

/**
 * Delete document and vector data
 * DELETE /ingest/{doc_id}
 * @param {string} docId
 */
export function deleteDocument(docId) {
    return http.delete(`/ingest/${docId}`)
}

/**
 * Check document chunk list
 * GET /ingest/{doc_id}/chunks
 * @param {string} docId
 * @param {number} offset
 * @param {number} limit
 */
export function getDocumentChunks(docId, offset = 0, limit = 20) {
    return http.get(`/ingest/${docId}/chunks`, { params: { offset, limit } })
}
