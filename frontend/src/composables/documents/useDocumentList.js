import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteDocument, getDocuments, getDocumentsByKb } from '@/api/ingest'
import { buildDocumentDetailRoute } from '@/utils/documents/route'

export function useDocumentList(props, emit) {
  const router = useRouter()
  const documents = ref([])
  const loading = ref(false)
  const deletingId = ref(null)

  let pollingTimer = null
  let fetchGeneration = 0

  function clearPollingTimer() {
    if (!pollingTimer) return
    clearTimeout(pollingTimer)
    pollingTimer = null
  }

  async function fetchDocuments(showLoading = true) {
    const generation = ++fetchGeneration
    clearPollingTimer()

    if (showLoading) {
      loading.value = true
    }

    try {
      const response = props.kbId
        ? await getDocumentsByKb(props.kbId)
        : await getDocuments()

      documents.value = response?.documents ?? response ?? []

      const needsPolling = documents.value.some((document) => {
        return document.status === 'pending' || document.status === 'processing'
      })

      if (generation !== fetchGeneration) {
        return
      }

      if (needsPolling) {
        pollingTimer = setTimeout(() => {
          fetchDocuments(false)
        }, 3000)
      }
    } finally {
      if (showLoading) {
        loading.value = false
      }
    }
  }

  function goToDetail(document) {
    if (!document?.id || document.status === 'pending' || document.status === 'processing') {
      return
    }

    router.push(
      buildDocumentDetailRoute(document, {
        kbId: props.kbId,
        kbName: props.kbName,
      }),
    )
  }

  async function handleDelete(document) {
    try {
      await ElMessageBox.confirm(
        `Are you sure you want to delete "${document.title || document.file_name}" and all its vector data? This cannot be undone.`,
        'Confirm Deletion',
        {
          confirmButtonText: 'Delete',
          cancelButtonText: 'Cancel',
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
        },
      )
    } catch {
      return
    }

    deletingId.value = document.id

    try {
      await deleteDocument(document.id)
      documents.value = documents.value.filter((item) => item.id !== document.id)
      ElMessage.success('Document deleted')
      emit('deleted', document.id)
    } finally {
      deletingId.value = null
    }
  }

  function refresh() {
    fetchDocuments(false)
  }

  onMounted(() => {
    fetchDocuments()
  })

  onUnmounted(() => {
    clearPollingTimer()
  })

  return {
    documents,
    loading,
    deletingId,
    fetchDocuments,
    goToDetail,
    handleDelete,
    refresh,
  }
}
