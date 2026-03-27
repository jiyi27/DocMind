import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getDocumentById, getDocumentChunks } from '@/api/ingest'
import { parseDocumentDetailPreset } from '@/utils/documents/route'

export function useDocumentDetail() {
  const route = useRoute()
  const docId = computed(() => route.params.id)
  const preset = parseDocumentDetailPreset(route)

  const docMeta = ref({
    title: preset.title || null,
    file_name: preset.fileName || null,
    chunk_count: preset.chunkCount,
    created_at: null,
    kb_id: preset.kbId || null,
    kb_display_name: preset.kbName || null,
  })
  const kbDetail = ref(null)
  const chunks = ref([])
  const chunkTotal = ref(0)
  const loadingMeta = ref(true)
  const loadingChunks = ref(false)
  const loadingMore = ref(false)
  const offset = ref(0)

  const limit = 20

  const docTitle = computed(() => {
    return docMeta.value.title || docMeta.value.file_name || 'Document'
  })

  const kbDisplayName = computed(() => {
    return kbDetail.value?.display_name || docMeta.value.kb_display_name || preset.kbName || 'Unknown KB'
  })

  const kbSlug = computed(() => kbDetail.value?.name || null)

  const displayedChunkCount = computed(() => {
    return docMeta.value.chunk_count ?? chunkTotal.value ?? 0
  })

  const hasMore = computed(() => chunks.value.length < chunkTotal.value)

  async function fetchMeta() {
    loadingMeta.value = true

    try {
      if (!docId.value) return

      const document = await getDocumentById(docId.value)
      if (!document) return

      docMeta.value = { ...docMeta.value, ...document }
      kbDetail.value = document.kb_name
        ? { name: document.kb_name, display_name: document.kb_display_name }
        : null
    } finally {
      loadingMeta.value = false
    }
  }

  async function fetchChunks(reset = false) {
    if (!docId.value) return

    if (reset) {
      offset.value = 0
      chunks.value = []
      loadingChunks.value = true
    } else {
      loadingMore.value = true
    }

    try {
      const response = await getDocumentChunks(docId.value, offset.value, limit)
      const items = response?.items ?? []

      chunkTotal.value = response?.total ?? 0
      chunks.value = reset ? items : [...chunks.value, ...items]
      offset.value = chunks.value.length
    } finally {
      loadingChunks.value = false
      loadingMore.value = false
    }
  }

  function loadMore() {
    if (loadingMore.value || !hasMore.value) return
    fetchChunks(false)
  }

  onMounted(async () => {
    await fetchMeta()
    fetchChunks(true)
  })

  return {
    docId,
    docMeta,
    chunks,
    chunkTotal,
    loadingMeta,
    loadingChunks,
    loadingMore,
    docTitle,
    kbDisplayName,
    kbSlug,
    displayedChunkCount,
    hasMore,
    loadMore,
  }
}
