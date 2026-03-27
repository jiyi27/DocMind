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

    <div class="profile-grid">
      <section class="profile-panel profile-panel-overview">
        <div class="section-head">
          <div>
            <h2 class="section-title">Account Overview</h2>
            <p class="section-desc">Use profile for account context, then move document management to its own page.</p>
          </div>
          <el-button plain @click="goToMyDocuments">Open My Documents</el-button>
        </div>

        <div class="overview-grid">
          <article class="overview-card">
            <span class="overview-label">Workspace Scope</span>
            <strong class="overview-value">{{ kbLabel }}</strong>
            <p class="overview-copy">Documents you upload follow your current workspace permissions.</p>
          </article>
          <article class="overview-card">
            <span class="overview-label">Role</span>
            <strong class="overview-value">{{ isSuperAdmin ? 'Super Admin' : 'User' }}</strong>
            <p class="overview-copy">Super admins can access global settings and all workspaces.</p>
          </article>
          <article class="overview-card overview-card-action">
            <div>
              <span class="overview-label">Documents</span>
              <strong class="overview-value">My Documents</strong>
              <p class="overview-copy">Manage uploaded files on a dedicated page instead of mixing them into profile.</p>
            </div>
            <el-button type="primary" plain @click="goToMyDocuments">View Documents</el-button>
          </article>
        </div>
      </section>

      <section class="profile-panel">
        <div class="section-head">
          <div>
            <h2 class="section-title">API Keys</h2>
            <p class="section-desc">Create personal API keys for external clients. Raw keys are shown only once.</p>
          </div>
          <el-button type="primary" @click="openCreateKeyDialog">Create API Key</el-button>
        </div>

        <div v-if="apiKeysLoading" class="api-key-loading">
          <el-skeleton :rows="4" animated />
        </div>
        <el-empty v-else-if="apiKeys.length === 0" description="No API keys yet" :image-size="88" />
        <el-table v-else :data="apiKeys" class="api-key-table" empty-text="No API keys yet">
          <el-table-column label="Name" min-width="220">
            <template #default="{ row }">
              <div class="table-primary-cell">
                <strong>{{ row.name }}</strong>
                <span class="table-secondary">{{ row.key_prefix }}...</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Status" width="120">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" effect="plain">
                {{ row.is_active ? 'Active' : 'Revoked' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Daily Limit" width="140">
            <template #default="{ row }">
              {{ row.daily_limit }}
            </template>
          </el-table-column>
          <el-table-column label="Created" min-width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="Last Used" min-width="180">
            <template #default="{ row }">
              {{ row.last_used_at ? formatDate(row.last_used_at) : 'Never' }}
            </template>
          </el-table-column>
          <el-table-column label="Actions" width="120" align="right">
            <template #default="{ row }">
              <el-button
                type="danger"
                text
                :disabled="!row.is_active || deletingKeyId === row.id"
                @click="revokeApiKey(row)"
              >
                Revoke
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { createApiKey, deleteApiKey, listApiKeys } from '@/api/apiKeys'

const router = useRouter()
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

function goToMyDocuments() {
  router.push({ name: 'MyDocuments' })
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
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-toolbar {
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

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
}

.profile-panel {
  padding: 22px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.profile-panel-overview {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(239, 246, 255, 0.9)),
    rgba(255, 255, 255, 0.82);
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

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.overview-card {
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.78);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.overview-card-action {
  justify-content: space-between;
}

.overview-label {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dm-text-soft);
}

.overview-value {
  font-size: 22px;
  line-height: 1.2;
  color: var(--dm-text);
}

.overview-copy {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--dm-text-soft);
}

.api-key-table {
  width: 100%;
}

.table-primary-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.table-secondary {
  font-size: 12px;
  color: var(--dm-text-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.api-key-loading {
  padding: 8px 0;
}

@media (max-width: 960px) {
  .profile-header {
    align-items: flex-start;
  }

  .overview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .profile-panel {
    padding: 18px;
    border-radius: 22px;
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
