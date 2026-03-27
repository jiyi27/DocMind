<template>
  <div class="user-profile">
    <section class="profile-toolbar">
      <div class="profile-header">
        <el-avatar :size="72" class="profile-avatar">
          {{ userInitial }}
        </el-avatar>
        <div class="profile-details">
          <div class="profile-title-row">
            <h1 class="profile-name">{{ username }}</h1>
            <el-tag v-if="isSuperAdmin" type="danger" effect="plain" round>Super Admin</el-tag>
            <el-tag v-else type="info" effect="plain" round>User</el-tag>
          </div>
          <div class="profile-meta">
            <span class="meta-pill">
              <span class="meta-label">Username</span>
              <strong>{{ username }}</strong>
            </span>
            <span class="meta-pill">
              <span class="meta-label">Role</span>
              <strong>{{ isSuperAdmin ? 'Super Admin' : 'User' }}</strong>
            </span>
            <span class="meta-pill">
              <span class="meta-label">Knowledge Base</span>
              <strong>{{ kbLabel }}</strong>
            </span>
          </div>
        </div>
      </div>
    </section>

    <section class="documents-panel">
      <div class="section-head">
        <div>
          <h2 class="section-title">API Keys</h2>
          <p class="section-desc">Create personal API keys for external clients. Raw keys are shown only once.</p>
        </div>
        <el-button type="primary" @click="openCreateKeyDialog">Create API Key</el-button>
      </div>

      <div class="api-key-list">
        <div v-if="apiKeysLoading" class="api-key-loading">
          <el-skeleton :rows="3" animated />
        </div>
        <el-empty v-else-if="apiKeys.length === 0" description="No API keys yet" :image-size="88" />
        <div v-else class="api-key-cards">
          <article v-for="item in apiKeys" :key="item.id" class="api-key-card">
            <div class="api-key-card-head">
              <div>
                <h3 class="api-key-name">{{ item.name }}</h3>
                <p class="api-key-prefix">{{ item.key_prefix }}...</p>
              </div>
              <el-tag :type="item.is_active ? 'success' : 'info'" effect="plain">
                {{ item.is_active ? 'Active' : 'Revoked' }}
              </el-tag>
            </div>
            <div class="api-key-meta">
              <span class="meta-pill">
                <span class="meta-label">Daily limit</span>
                <strong>{{ item.daily_limit }}</strong>
              </span>
              <span class="meta-pill">
                <span class="meta-label">Created</span>
                <strong>{{ formatDate(item.created_at) }}</strong>
              </span>
              <span class="meta-pill">
                <span class="meta-label">Last used</span>
                <strong>{{ item.last_used_at ? formatDate(item.last_used_at) : 'Never' }}</strong>
              </span>
            </div>
            <div class="api-key-actions">
              <el-button
                type="danger"
                plain
                :disabled="!item.is_active || deletingKeyId === item.id"
                @click="revokeApiKey(item)"
              >
                Revoke
              </el-button>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="documents-panel">
      <div class="section-head">
        <div>
          <h2 class="section-title">My Uploaded Documents</h2>
          <p class="section-desc">Everything you uploaded across accessible workspaces.</p>
        </div>
      </div>
      <div class="doc-list-wrap">
        <DocumentList mode="profile" />
      </div>
    </section>

    <el-dialog v-model="createKeyDialogVisible" title="Create API Key" width="460px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Name">
          <el-input v-model="createKeyForm.name" maxlength="120" placeholder="e.g. Claude Desktop" />
        </el-form-item>
        <el-form-item label="Daily Limit">
          <el-input-number v-model="createKeyForm.daily_limit" :min="1" :max="1000000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createKeyDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="creatingKey" @click="submitCreateApiKey">
          Create
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createdKeyDialogVisible" title="Copy API Key Now" width="560px">
      <p class="section-desc">This is the only time the full key will be shown.</p>
      <el-input :model-value="newlyCreatedRawKey" readonly>
        <template #append>
          <el-button @click="copyRawKey">Copy</el-button>
        </template>
      </el-input>
      <template #footer>
        <el-button type="primary" @click="createdKeyDialogVisible = false">Done</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { createApiKey, deleteApiKey, listApiKeys } from '@/api/apiKeys'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const authStore = useAuthStore()
const kbStore = useKbStore()

const username = computed(() => authStore.user?.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isSuperAdmin = computed(() => authStore.isSuperAdmin)
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
const scopedKb = computed(() =>
  kbStore.kbList.find((kb) => String(kb.id) === String(authStore.kbId)) || null,
)
const kbLabel = computed(() => {
  if (isSuperAdmin.value) return 'All workspaces'
  return scopedKb.value?.display_name || scopedKb.value?.name || 'Assigned workspace'
})

function formatDate(value) {
  return new Date(value).toLocaleString()
}

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

onMounted(() => {
  if (!isSuperAdmin.value && authStore.kbId && kbStore.kbList.length === 0) {
    kbStore.fetchKbs()
  }
  loadApiKeys()
})
</script>

<style scoped>
.user-profile {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
}

.profile-toolbar {
  margin-bottom: 20px;
  padding: 4px 2px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 18px;
}

.profile-avatar {
  background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%);
  color: #ffffff;
  font-size: 28px;
  font-weight: 700;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
}

.profile-details {
  min-width: 0;
}

.profile-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-name {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dm-text);
}

.profile-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--dm-border);
  background: rgba(255, 255, 255, 0.86);
  color: var(--dm-text);
  font-size: 13px;
}

.meta-label {
  color: var(--dm-text-soft);
}

.documents-panel {
  padding: 22px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.section-head {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 800;
  color: var(--dm-text);
}

.section-desc {
  margin: 0;
  font-size: 13px;
  color: var(--dm-text-soft);
}

.doc-list-wrap {
  max-height: calc(100vh - 320px);
  min-height: 320px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.api-key-list {
  min-height: 120px;
}

.api-key-loading {
  padding: 8px 0;
}

.api-key-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.api-key-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid var(--dm-border);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.9));
}

.api-key-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.api-key-name {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 800;
  color: var(--dm-text);
}

.api-key-prefix {
  margin: 0;
  font-size: 13px;
  color: var(--dm-text-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.api-key-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.api-key-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 960px) {
  .profile-header {
    align-items: flex-start;
  }

  .api-key-cards {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .documents-panel {
    padding: 18px;
  }

  .profile-header {
    flex-direction: column;
  }

  .section-head {
    flex-direction: column;
    align-items: stretch;
  }

  .profile-name {
    font-size: 24px;
  }
}
</style>
