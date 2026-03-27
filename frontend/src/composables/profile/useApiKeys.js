import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createApiKey, deleteApiKey, listApiKeys } from '@/api/apiKeys'

export function useApiKeys() {
  const apiKeys = ref([])
  const apiKeysLoading = ref(false)
  const createKeyDialogVisible = ref(false)
  const createdKeyDialogVisible = ref(false)
  const creatingKey = ref(false)
  const deletingKeyId = ref('')
  const newlyCreatedRawKey = ref('')
  const createKeyForm = reactive({
    name: '',
    daily_limit: 1000,
  })

  async function loadApiKeys() {
    apiKeysLoading.value = true

    try {
      apiKeys.value = await listApiKeys()
    } finally {
      apiKeysLoading.value = false
    }
  }

  function openCreateKeyDialog() {
    createKeyForm.name = ''
    createKeyForm.daily_limit = 1000
    createKeyDialogVisible.value = true
  }

  async function submitCreateApiKey() {
    if (!createKeyForm.name.trim()) {
      ElMessage.error('API key name is required')
      return
    }

    creatingKey.value = true

    try {
      const created = await createApiKey({
        name: createKeyForm.name.trim(),
        daily_limit: createKeyForm.daily_limit,
      })
      createKeyDialogVisible.value = false
      newlyCreatedRawKey.value = created.raw_key || ''
      createdKeyDialogVisible.value = true
      await loadApiKeys()
      ElMessage.success('API key created')
    } finally {
      creatingKey.value = false
    }
  }

  async function revokeApiKey(item) {
    try {
      await ElMessageBox.confirm(
        `Revoke API key "${item.name}"? This cannot be undone.`,
        'Revoke API Key',
        { type: 'warning' },
      )
    } catch {
      return
    }

    deletingKeyId.value = item.id

    try {
      await deleteApiKey(item.id)
      await loadApiKeys()
      ElMessage.success('API key revoked')
    } finally {
      deletingKeyId.value = ''
    }
  }

  async function copyRawKey() {
    await navigator.clipboard.writeText(newlyCreatedRawKey.value)
    ElMessage.success('API key copied')
  }

  return {
    apiKeys,
    apiKeysLoading,
    createKeyDialogVisible,
    createdKeyDialogVisible,
    creatingKey,
    deletingKeyId,
    newlyCreatedRawKey,
    createKeyForm,
    loadApiKeys,
    openCreateKeyDialog,
    submitCreateApiKey,
    revokeApiKey,
    copyRawKey,
  }
}
