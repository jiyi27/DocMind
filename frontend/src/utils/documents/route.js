export function buildDocumentDetailRoute(document, options = {}) {
  const kbId = options.kbId ?? document?.kb_id ?? null
  const kbName = options.kbName ?? document?.kb_display_name ?? null

  return {
    name: 'DocumentDetail',
    params: { id: document.id },
    query: {
      kbId: kbId || undefined,
      kbName: kbName || undefined,
      title: document?.title || undefined,
      fileName: document?.file_name || undefined,
      chunkCount: document?.chunk_count ?? undefined,
    },
  }
}

export function parseDocumentDetailPreset(route) {
  const query = route?.query || {}

  const chunkCount = typeof query.chunkCount === 'string' ? Number(query.chunkCount) : null

  return {
    title: typeof query.title === 'string' ? query.title : '',
    fileName: typeof query.fileName === 'string' ? query.fileName : '',
    kbName: typeof query.kbName === 'string' ? query.kbName : '',
    kbId: typeof query.kbId === 'string' ? query.kbId : null,
    chunkCount: Number.isFinite(chunkCount) ? chunkCount : null,
  }
}
