import { h, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getKbSyncJobs, getKbSyncRecords, previewKbSync, resolveConfluencePage, triggerKbSync } from '@/api/kb'

export function useKbConfluenceSync({ kbId, kbDetail, kbStore }) {
  const confluenceDialogVisible = ref(false)
  const syncPreviewDialogVisible = ref(false)
  const historyDrawerVisible = ref(false)
  const confluenceSaving = ref(false)
  const syncTriggering = ref(false)
  const historyLoading = ref(false)
  const recordsLoading = ref(false)
  const syncJobs = ref([])
  const jobRecords = ref([])
  const expandedJobId = ref('')
  const confluenceFormRef = ref(null)
  const syncPreview = ref(null)

  let historyPollingTimer = null

  const confluenceForm = ref({
    root_page_url: '',
    sync_enabled: false,
    sync_interval_minutes: 5,
    retrieval_mode: 'chunk',
  })

  const confluenceRules = {
    root_page_url: [
      {
        validator: (_, value, callback) => {
          if (!value || !value.trim()) {
            callback()
            return
          }

          const normalizedValue = value.trim()
          if (!normalizedValue.includes('/display/') && !normalizedValue.includes('pageId=')) {
            callback(new Error('Must be a Confluence page URL containing /display/ or pageId='))
            return
          }

          callback()
        },
        trigger: 'blur',
      },
    ],
    sync_interval_minutes: [
      {
        validator: (_, value, callback) => {
          if (!Number.isInteger(value) || value < 5) {
            callback(new Error('Sync interval must be at least 5 minutes'))
            return
          }

          callback()
        },
        trigger: 'change',
      },
    ],
  }

  function syncFormFromKb() {
    confluenceForm.value.root_page_url = ''
    confluenceForm.value.sync_enabled = Boolean(kbDetail.value?.confluence_sync_enabled)
    confluenceForm.value.sync_interval_minutes = Number(kbDetail.value?.confluence_sync_interval_minutes || 5)
    confluenceForm.value.retrieval_mode = kbDetail.value?.confluence_retrieval_mode || 'chunk'
  }

  function clearHistoryPolling() {
    if (historyPollingTimer) {
      clearTimeout(historyPollingTimer)
      historyPollingTimer = null
    }
  }

  function hasActiveSyncJobs() {
    return syncJobs.value.some((job) => job.status === 'pending' || job.status === 'running')
  }

  function scheduleHistoryPolling() {
    clearHistoryPolling()

    if (!historyDrawerVisible.value || !hasActiveSyncJobs()) {
      return
    }

    historyPollingTimer = setTimeout(async () => {
      await loadSyncJobs({ silent: true })
      if (expandedJobId.value) {
        await loadJobRecords(expandedJobId.value, { silent: true })
      }
      scheduleHistoryPolling()
    }, 3000)
  }

  function formatRetrievalMode(mode) {
    return mode === 'full_doc' ? 'Full Article' : 'Fragment'
  }

  function formatSyncInterval(minutes) {
    const value = Number(minutes || 0)
    return `${value} minute${value === 1 ? '' : 's'}`
  }

  function formatSyncStatus(status) {
    if (!status) return 'Never synced'
    if (status === 'completed') return 'Completed'
    if (status === 'failed') return 'Failed'
    if (status === 'running') return 'Running'
    if (status === 'pending') return 'Pending'
    return status
  }

  function syncStatusTagType(status) {
    if (status === 'completed' || status === 'success') return 'success'
    if (status === 'failed') return 'danger'
    if (status === 'running' || status === 'processing') return 'warning'
    return 'info'
  }

  function operationTagType(operation) {
    if (operation === 'create') return 'success'
    if (operation === 'update') return 'warning'
    if (operation === 'delete') return 'danger'
    return 'info'
  }

  function openConfluenceDialog() {
    syncFormFromKb()
    confluenceDialogVisible.value = true
  }

  async function openHistoryDrawer() {
    historyDrawerVisible.value = true
    await loadSyncJobs()
  }

  function handleHistoryDrawerClosed() {
    clearHistoryPolling()
    expandedJobId.value = ''
    jobRecords.value = []
  }

  function resetConfluenceForm() {
    syncFormFromKb()
    confluenceFormRef.value?.clearValidate?.()
  }

  async function submitConfluenceForm() {
    const valid = await confluenceFormRef.value?.validate().catch(() => false)
    if (!valid) return

    const url = confluenceForm.value.root_page_url.trim()

    if (confluenceForm.value.sync_enabled && !kbDetail.value?.confluence_capability_enabled) {
      ElMessage.error('Configure Confluence Base URL and PAT in System Settings before enabling auto sync')
      return
    }

    confluenceSaving.value = true

    try {
      let rootPageId = kbDetail.value?.confluence_root_page_id || ''
      let rootPageTitle = kbDetail.value?.confluence_root_page_title || ''

      if (url) {
        let resolved

        try {
          resolved = await resolveConfluencePage(kbId.value, url)
        } catch {
          return
        }

        try {
          await ElMessageBox.confirm(
            h('div', { style: 'line-height: 1.8' }, [
              h('p', null, [h('b', null, 'Page: '), resolved.title]),
              h('p', null, [h('b', null, 'Page ID: '), resolved.page_id]),
              h('p', null, [
                h('b', null, 'URL: '),
                h('a', { href: resolved.source_url, target: '_blank', rel: 'noreferrer' }, resolved.source_url),
              ]),
            ]),
            'Confirm Root Page Binding',
            {
              type: 'info',
              confirmButtonText: 'Confirm & Save',
              cancelButtonText: 'Cancel',
            },
          )
        } catch {
          return
        }

        rootPageId = resolved.page_id
        rootPageTitle = resolved.title
      }

      await kbStore.updateKbInfo(kbId.value, {
        display_name: kbDetail.value.display_name,
        description: kbDetail.value.description || '',
        confluence: {
          root_page_id: rootPageId,
          root_page_title: rootPageTitle,
          sync_enabled: confluenceForm.value.sync_enabled,
          sync_interval_minutes: confluenceForm.value.sync_interval_minutes,
          retrieval_mode: confluenceForm.value.retrieval_mode,
        },
      })

      confluenceDialogVisible.value = false
      syncFormFromKb()
      ElMessage.success('Confluence settings updated')
    } finally {
      confluenceSaving.value = false
    }
  }

  async function triggerSyncNow() {
    syncTriggering.value = true

    try {
      const preview = await previewKbSync(kbId.value)
      if (preview?.job_in_progress) {
        if (historyDrawerVisible.value) {
          await loadSyncJobs()
        }
        ElMessage.success('Existing sync job is still running')
        return
      }

      if ((preview?.total_operations || 0) === 0) {
        ElMessage.success(`Scanned ${preview?.scanned || 0} page(s) — all up to date`)
        return
      }

      syncPreview.value = preview
      syncPreviewDialogVisible.value = true
    } catch (error) {
      if (error === 'cancel' || error === 'close' || error?.message === 'cancel') {
        return
      }
      throw error
    } finally {
      syncTriggering.value = false
    }
  }

  async function confirmTriggerSync() {
    if (!syncPreview.value) return

    syncTriggering.value = true

    try {
      const data = await triggerKbSync(kbId.value)
      syncPreviewDialogVisible.value = false
      syncPreview.value = null
      await kbStore.fetchKbDetail(kbId.value)
      if (historyDrawerVisible.value) {
        await loadSyncJobs()
      }
      ElMessage.success(data?.status === 'pending' ? 'Confluence sync started' : 'Existing sync job is still running')
    } finally {
      syncTriggering.value = false
    }
  }

  async function loadSyncJobs({ silent = false } = {}) {
    if (!silent) {
      historyLoading.value = true
    }

    try {
      const data = await getKbSyncJobs(kbId.value, 20)
      syncJobs.value = data?.jobs || []
      scheduleHistoryPolling()
    } finally {
      if (!silent) {
        historyLoading.value = false
      }
    }
  }

  async function toggleJobDetails(job) {
    if (expandedJobId.value === job.id) {
      expandedJobId.value = ''
      jobRecords.value = []
      return
    }

    expandedJobId.value = job.id
    await loadJobRecords(job.id)
  }

  async function loadJobRecords(jobId, { silent = false } = {}) {
    if (!silent) {
      recordsLoading.value = true
    }

    try {
      const data = await getKbSyncRecords(kbId.value, jobId)
      if (expandedJobId.value === jobId) {
        jobRecords.value = data?.records || []
      }
    } finally {
      if (!silent) {
        recordsLoading.value = false
      }
    }
  }

  onUnmounted(() => {
    clearHistoryPolling()
  })

  return {
    confluenceDialogVisible,
    syncPreviewDialogVisible,
    historyDrawerVisible,
    confluenceSaving,
    syncTriggering,
    historyLoading,
    recordsLoading,
    syncJobs,
    jobRecords,
    expandedJobId,
    confluenceFormRef,
    syncPreview,
    confluenceForm,
    confluenceRules,
    syncFormFromKb,
    formatRetrievalMode,
    formatSyncInterval,
    formatSyncStatus,
    syncStatusTagType,
    operationTagType,
    openConfluenceDialog,
    openHistoryDrawer,
    handleHistoryDrawerClosed,
    resetConfluenceForm,
    submitConfluenceForm,
    triggerSyncNow,
    confirmTriggerSync,
    loadSyncJobs,
    toggleJobDetails,
    loadJobRecords,
  }
}
