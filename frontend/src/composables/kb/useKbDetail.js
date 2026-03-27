import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useKbDetail({ kbId, kbDetail, kbStore }) {
  const infoDialogVisible = ref(false)
  const connectionDialogVisible = ref(false)
  const infoSaving = ref(false)
  const connectionSaving = ref(false)
  const infoFormRef = ref(null)
  const connectionFormRef = ref(null)

  const infoForm = ref({
    display_name: '',
    description: '',
  })

  const connectionForm = ref({
    base_url: '',
    api_key: '',
  })

  const infoRules = {
    display_name: [
      { required: true, message: 'Please enter a display name', trigger: 'blur' },
      { min: 1, max: 128, message: 'Length must be between 1 and 128 characters', trigger: 'blur' },
    ],
  }

  function syncFormsFromKb() {
    infoForm.value.display_name = kbDetail.value?.display_name || ''
    infoForm.value.description = kbDetail.value?.description || ''
    connectionForm.value.base_url = kbDetail.value?.embedding_base_url || ''
    connectionForm.value.api_key = ''
  }

  function openInfoDialog() {
    syncFormsFromKb()
    infoDialogVisible.value = true
  }

  function openConnectionDialog() {
    syncFormsFromKb()
    connectionDialogVisible.value = true
  }

  function resetInfoForm() {
    syncFormsFromKb()
    infoFormRef.value?.clearValidate?.()
  }

  function resetConnectionForm() {
    syncFormsFromKb()
    connectionFormRef.value?.clearValidate?.()
  }

  async function submitInfoForm() {
    const valid = await infoFormRef.value?.validate().catch(() => false)
    if (!valid) return

    infoSaving.value = true

    try {
      await kbStore.updateKbInfo(kbId.value, {
        display_name: infoForm.value.display_name.trim(),
        description: infoForm.value.description.trim(),
      })
      infoDialogVisible.value = false
      ElMessage.success('Knowledge base updated')
    } finally {
      infoSaving.value = false
    }
  }

  async function submitConnectionForm() {
    connectionSaving.value = true

    try {
      await kbStore.updateKbConnection(kbId.value, {
        base_url: connectionForm.value.base_url.trim(),
        api_key: connectionForm.value.api_key.trim(),
      })
      connectionDialogVisible.value = false
      ElMessage.success('Embedding connection updated')
    } finally {
      connectionSaving.value = false
    }
  }

  return {
    infoDialogVisible,
    connectionDialogVisible,
    infoSaving,
    connectionSaving,
    infoFormRef,
    connectionFormRef,
    infoForm,
    connectionForm,
    infoRules,
    syncFormsFromKb,
    openInfoDialog,
    openConnectionDialog,
    resetInfoForm,
    resetConnectionForm,
    submitInfoForm,
    submitConnectionForm,
  }
}
