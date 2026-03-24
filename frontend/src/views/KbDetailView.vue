<template>
  <div class="kb-detail-page">
    <div class="page-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" text @click="router.push('/')" />
        <div class="kb-title-info">
          <h1 class="kb-display-name">{{ kbDetail?.display_name || 'Knowledge Base' }}</h1>
          <span class="kb-slug">{{ kbDetail?.name }}</span>
          <p v-if="kbDetail?.description" class="kb-description">{{ kbDetail.description }}</p>
        </div>
      </div>
      <div v-if="canEdit" class="header-actions">
        <el-button type="primary" plain @click="openInfoDialog">
          Edit Info
        </el-button>
        <el-button plain @click="openConnectionDialog">
          Connection
        </el-button>
      </div>
    </div>

    <div v-if="kbDetail" class="kb-overview">
      <div class="overview-card">
        <div class="overview-title">Overview</div>
        <div class="overview-tags">
          <el-tag type="info">{{ kbDetail.document_count ?? 0 }} Documents</el-tag>
          <el-tag type="success">{{ kbDetail.total_points ?? 0 }} Chunks</el-tag>
        </div>
      </div>

      <div class="overview-card">
        <div class="overview-title">Embedding</div>
        <div class="overview-tags">
          <el-tag v-if="kbDetail.embedding_provider" effect="plain">
            {{ kbDetail.embedding_provider }}
          </el-tag>
          <el-tag v-if="kbDetail.embedding_model" effect="plain" type="warning">
            {{ kbDetail.embedding_model }}
          </el-tag>
          <el-tag v-if="kbDetail.vector_dimension" effect="plain" type="danger">
            {{ kbDetail.vector_dimension }} dims
          </el-tag>
          <el-tag effect="plain" :type="kbDetail.embedding_base_url_source === 'custom' ? 'success' : 'info'">
            {{ kbDetail.embedding_base_url_source === 'custom' ? 'Custom Base URL' : 'Default Base URL' }}
          </el-tag>
          <el-tag effect="plain" :type="kbDetail.embedding_api_key_configured ? 'success' : 'info'">
            {{ kbDetail.embedding_api_key_configured ? 'Custom API Key' : 'Default API Key' }}
          </el-tag>
        </div>
      </div>
    </div>

    <div v-if="kbDetail" class="confluence-panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">Confluence Sync</h2>
          <p class="panel-subtitle">Manage KB-level Confluence binding, manual sync, and job history.</p>
        </div>
        <div class="panel-actions">
          <el-button v-if="canEdit" plain @click="openConfluenceDialog">
            Configure
          </el-button>
          <el-button plain @click="openHistoryDrawer">
            View History
          </el-button>
          <el-button
            v-if="canEdit"
            type="primary"
            :loading="syncTriggering"
            :disabled="!kbDetail.confluence_root_page_id"
            @click="triggerSyncNow"
          >
            Sync Now
          </el-button>
        </div>
      </div>

      <div class="confluence-grid">
        <div class="confluence-stat">
          <span class="confluence-label">Root Page ID</span>
          <span class="confluence-value confluence-value--mono">
            {{ kbDetail.confluence_root_page_id || 'Not configured' }}
          </span>
        </div>
        <div class="confluence-stat">
          <span class="confluence-label">Sync Enabled</span>
          <span class="confluence-value">
            <el-tag :type="kbDetail.confluence_sync_enabled ? 'success' : 'info'" effect="plain">
              {{ kbDetail.confluence_sync_enabled ? 'Enabled' : 'Disabled' }}
            </el-tag>
          </span>
        </div>
        <div class="confluence-stat">
          <span class="confluence-label">Retrieval Mode</span>
          <span class="confluence-value">
            <el-tag effect="plain" type="warning">
              {{ formatRetrievalMode(kbDetail.confluence_retrieval_mode) }}
            </el-tag>
          </span>
        </div>
        <div class="confluence-stat">
          <span class="confluence-label">Last Sync</span>
          <span class="confluence-value">
            {{ kbDetail.confluence_last_sync_at ? formatDateTime(kbDetail.confluence_last_sync_at) : 'Never synced' }}
          </span>
        </div>
        <div class="confluence-stat">
          <span class="confluence-label">Last Status</span>
          <span class="confluence-value">
            <el-tooltip
              v-if="kbDetail.confluence_last_sync_status === 'failed' && kbDetail.confluence_last_sync_error"
              :content="kbDetail.confluence_last_sync_error"
              placement="top"
            >
              <el-tag :type="syncStatusTagType(kbDetail.confluence_last_sync_status)" effect="plain">
                {{ formatSyncStatus(kbDetail.confluence_last_sync_status) }}
              </el-tag>
            </el-tooltip>
            <el-tag v-else :type="syncStatusTagType(kbDetail.confluence_last_sync_status)" effect="plain">
              {{ formatSyncStatus(kbDetail.confluence_last_sync_status) }}
            </el-tag>
          </span>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="infoDialogVisible"
      title="Edit Knowledge Base"
      width="520px"
      :close-on-click-modal="false"
      @closed="resetInfoForm"
    >
      <el-form
        ref="infoFormRef"
        :model="infoForm"
        :rules="infoRules"
        label-position="top"
      >
        <el-form-item label="Slug">
          <el-input :model-value="kbDetail?.name || ''" disabled />
          <div class="form-hint">Slug is part of the vector collection identity and cannot be changed.</div>
        </el-form-item>
        <el-form-item label="Display Name" prop="display_name">
          <el-input v-model="infoForm.display_name" clearable />
        </el-form-item>
        <el-form-item label="Description" prop="description">
          <el-input
            v-model="infoForm.description"
            type="textarea"
            :rows="3"
            placeholder="Optional description"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="infoDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="infoSaving" @click="submitInfoForm">
          Save
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="connectionDialogVisible"
      title="Embedding Connection"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetConnectionForm"
    >
      <el-alert
        title="Only update connection settings for the same embedding model. Changing to a different backend implementation may break retrieval consistency."
        type="warning"
        :closable="false"
        show-icon
        class="dialog-alert"
      />

      <div class="connection-readonly">
        <div class="readonly-item">
          <span class="readonly-label">Provider</span>
          <span class="readonly-value">{{ kbDetail?.embedding_provider || '-' }}</span>
        </div>
        <div class="readonly-item">
          <span class="readonly-label">Model</span>
          <span class="readonly-value">{{ kbDetail?.embedding_model || '-' }}</span>
        </div>
        <div class="readonly-item">
          <span class="readonly-label">Vector Dimension</span>
          <span class="readonly-value">{{ kbDetail?.vector_dimension || '-' }}</span>
        </div>
      </div>

      <el-form
        ref="connectionFormRef"
        :model="connectionForm"
        label-position="top"
      >
        <el-form-item label="Base URL">
          <el-input
            v-model="connectionForm.base_url"
            placeholder="Leave empty to use the system default"
            clearable
          />
          <div class="form-hint">
            Current source:
            {{ kbDetail?.embedding_base_url_source === 'custom' ? 'custom value' : 'system default' }}
          </div>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="connectionForm.api_key"
            type="password"
            show-password
            placeholder="Leave empty to use the system default"
            clearable
          />
          <div class="form-hint">
            Current source:
            {{ kbDetail?.embedding_api_key_configured ? 'custom key' : 'system default' }}
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="connectionDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="connectionSaving" @click="submitConnectionForm">
          Save
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="confluenceDialogVisible"
      title="Confluence Sync Settings"
      width="560px"
      :close-on-click-modal="false"
      @closed="resetConfluenceForm"
    >
      <el-form
        ref="confluenceFormRef"
        :model="confluenceForm"
        :rules="confluenceRules"
        label-position="top"
      >
        <el-form-item label="Root Page ID" prop="root_page_id">
          <el-input
            v-model="confluenceForm.root_page_id"
            placeholder="e.g. 39383288"
            clearable
          />
          <div class="form-hint">Bind this KB to a Confluence root page so sync can walk its page tree.</div>
        </el-form-item>

        <el-form-item label="Retrieval Mode" prop="retrieval_mode">
          <el-radio-group v-model="confluenceForm.retrieval_mode">
            <el-radio-button label="chunk">Fragment</el-radio-button>
            <el-radio-button label="full_doc">Full Article</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="Sync Enabled">
          <el-switch v-model="confluenceForm.sync_enabled" />
          <div class="form-hint">When enabled, the background worker can pick this KB up for scheduled sync.</div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="confluenceDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="confluenceSaving" @click="submitConfluenceForm">
          Save
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="historyDrawerVisible"
      title="Confluence Sync History"
      size="720px"
      :destroy-on-close="false"
      @closed="handleHistoryDrawerClosed"
    >
      <div class="history-toolbar">
        <el-button plain :loading="historyLoading" @click="loadSyncJobs">
          Refresh
        </el-button>
      </div>

      <el-skeleton v-if="historyLoading && syncJobs.length === 0" :rows="6" animated />

      <el-empty
        v-else-if="syncJobs.length === 0"
        description="No sync jobs yet."
        :image-size="72"
      />

      <div v-else class="history-list">
        <div
          v-for="job in syncJobs"
          :key="job.id"
          class="history-item"
        >
          <div class="history-item-main">
            <div class="history-item-header">
              <div class="history-job-meta">
                <el-tag :type="syncStatusTagType(job.status)" effect="plain">
                  {{ formatSyncStatus(job.status) }}
                </el-tag>
                <el-tag effect="plain" type="info">
                  {{ job.trigger_type === 'manual' ? 'Manual' : 'Scheduled' }}
                </el-tag>
              </div>
              <el-button
                text
                @click="toggleJobDetails(job)"
              >
                {{ expandedJobId === job.id ? 'Hide Records' : 'View Records' }}
              </el-button>
            </div>

            <div class="history-job-lines">
              <div>Created: {{ formatDateTime(job.created_at) }}</div>
              <div v-if="job.started_at">Started: {{ formatDateTime(job.started_at) }}</div>
              <div v-if="job.finished_at">Finished: {{ formatDateTime(job.finished_at) }}</div>
              <div class="history-job-id">Job ID: {{ job.id }}</div>
            </div>

            <el-alert
              v-if="job.error_message"
              :title="job.error_message"
              type="error"
              :closable="false"
              show-icon
              class="history-job-error"
            />

            <div v-if="expandedJobId === job.id" class="records-section">
              <el-skeleton v-if="recordsLoading" :rows="4" animated />

              <el-empty
                v-else-if="jobRecords.length === 0"
                description="No record details for this job."
                :image-size="64"
              />

              <el-table
                v-else
                :data="jobRecords"
                size="small"
                border
                class="records-table"
              >
                <el-table-column prop="operation" label="Operation" width="100">
                  <template #default="{ row }">
                    <el-tag size="small" effect="plain" :type="operationTagType(row.operation)">
                      {{ row.operation }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Status" width="120">
                  <template #default="{ row }">
                    <el-tooltip
                      v-if="row.status === 'failed' && row.error_message"
                      :content="row.error_message"
                      placement="top"
                    >
                      <el-tag size="small" effect="plain" :type="syncStatusTagType(row.status)">
                        {{ row.status }}
                      </el-tag>
                    </el-tooltip>
                    <el-tag v-else size="small" effect="plain" :type="syncStatusTagType(row.status)">
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="document_title" label="Document Title" min-width="180" />
                <el-table-column prop="source_url" label="Page URL" min-width="220">
                  <template #default="{ row }">
                    <a
                      v-if="row.source_url"
                      :href="row.source_url"
                      target="_blank"
                      rel="noreferrer"
                      class="record-link"
                    >
                      Open Page
                    </a>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="Created At" width="180">
                  <template #default="{ row }">
                    {{ formatDateTime(row.created_at) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <div class="page-body">
      <div class="upload-column">
        <div class="column-card">
          <h3 class="column-title">
            <el-icon><Upload /></el-icon>
            Upload Documents
          </h3>
          <el-divider />
          <UploadZone :kb-id="kbId" @uploaded="handleUploaded" />
        </div>
      </div>

      <div class="list-column">
        <div class="column-card">
          <h3 class="column-title">
            <el-icon><Files /></el-icon>
            My Documents
          </h3>
          <el-divider />
          <DocumentList
            ref="docListRef"
            :kb-id="kbId"
            :kb-name="kbDetail?.display_name"
            @deleted="handleDeleted"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Files, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { getKbSyncJobs, getKbSyncRecords, triggerKbSync } from '@/api/kb'
import UploadZone from '@/components/ingestion/UploadZone.vue'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const kbStore = useKbStore()

const kbId = computed(() => route.params.id)
const kbDetail = computed(() => kbStore.currentKb)
const canEdit = computed(() => authStore.isSuperAdmin)
const docListRef = ref(null)
const infoDialogVisible = ref(false)
const connectionDialogVisible = ref(false)
const confluenceDialogVisible = ref(false)
const historyDrawerVisible = ref(false)
const infoSaving = ref(false)
const connectionSaving = ref(false)
const confluenceSaving = ref(false)
const syncTriggering = ref(false)
const historyLoading = ref(false)
const recordsLoading = ref(false)
const syncJobs = ref([])
const jobRecords = ref([])
const expandedJobId = ref('')
const infoFormRef = ref(null)
const connectionFormRef = ref(null)
const confluenceFormRef = ref(null)
let historyPollingTimer = null

const infoForm = ref({
  display_name: '',
  description: '',
})

const connectionForm = ref({
  base_url: '',
  api_key: '',
})

const confluenceForm = ref({
  root_page_id: '',
  sync_enabled: false,
  retrieval_mode: 'chunk',
})

const infoRules = {
  display_name: [
    { required: true, message: 'Please enter a display name', trigger: 'blur' },
    { min: 1, max: 128, message: 'Length must be between 1 and 128 characters', trigger: 'blur' },
  ],
}

const confluenceRules = {
  root_page_id: [
    {
      validator: (_, value, callback) => {
        if (!value || !value.trim()) {
          callback()
          return
        }
        if (!/^\d+$/.test(value.trim())) {
          callback(new Error('Root page ID must be numeric'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

onMounted(async () => {
  await kbStore.fetchKbDetail(kbId.value)
  syncFormsFromKb()
})

onUnmounted(() => {
  clearHistoryPolling()
})

function syncFormsFromKb() {
  infoForm.value.display_name = kbDetail.value?.display_name || ''
  infoForm.value.description = kbDetail.value?.description || ''
  connectionForm.value.base_url = kbDetail.value?.embedding_base_url || ''
  connectionForm.value.api_key = ''
  confluenceForm.value.root_page_id = kbDetail.value?.confluence_root_page_id || ''
  confluenceForm.value.sync_enabled = Boolean(kbDetail.value?.confluence_sync_enabled)
  confluenceForm.value.retrieval_mode = kbDetail.value?.confluence_retrieval_mode || 'chunk'
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
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

function openInfoDialog() {
  syncFormsFromKb()
  infoDialogVisible.value = true
}

function openConnectionDialog() {
  syncFormsFromKb()
  connectionDialogVisible.value = true
}

function openConfluenceDialog() {
  syncFormsFromKb()
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

function resetInfoForm() {
  syncFormsFromKb()
  infoFormRef.value?.clearValidate()
}

function resetConnectionForm() {
  syncFormsFromKb()
  connectionFormRef.value?.clearValidate?.()
}

function resetConfluenceForm() {
  syncFormsFromKb()
  confluenceFormRef.value?.clearValidate?.()
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

async function submitConfluenceForm() {
  const valid = await confluenceFormRef.value?.validate().catch(() => false)
  if (!valid) return

  confluenceSaving.value = true
  try {
    await kbStore.updateKbInfo(kbId.value, {
      display_name: kbDetail.value.display_name,
      description: kbDetail.value.description || '',
      confluence: {
        root_page_id: confluenceForm.value.root_page_id.trim(),
        sync_enabled: confluenceForm.value.sync_enabled,
        retrieval_mode: confluenceForm.value.retrieval_mode,
      },
    })
    confluenceDialogVisible.value = false
    syncFormsFromKb()
    ElMessage.success('Confluence settings updated')
  } finally {
    confluenceSaving.value = false
  }
}

async function triggerSyncNow() {
  syncTriggering.value = true
  try {
    const data = await triggerKbSync(kbId.value)
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

function handleUploaded() {
  docListRef.value?.refresh()
  kbStore.fetchKbDetail(kbId.value)
}

function handleDeleted() {
  kbStore.fetchKbDetail(kbId.value)
}
</script>

<style scoped>
.kb-detail-page {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.kb-title-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.kb-display-name {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}

.kb-slug {
  font-size: 12px;
  color: #909399;
}

.kb-description {
  margin: 8px 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 600px;
}

.kb-overview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  padding-left: 40px;
}

.overview-card,
.confluence-panel,
.column-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
}

.overview-card {
  padding: 16px 18px;
}

.overview-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 12px;
}

.overview-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.confluence-panel {
  margin-left: 40px;
  padding: 20px 22px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.panel-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

.panel-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: #909399;
}

.panel-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.confluence-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.confluence-stat {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  background: #fafafa;
}

.confluence-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.confluence-value {
  display: block;
  font-size: 13px;
  color: #303133;
  word-break: break-word;
}

.confluence-value--mono,
.history-job-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

.history-job-error {
  margin-top: 16px;
}

.dialog-alert {
  margin-bottom: 18px;
}

.connection-readonly {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.readonly-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
}

.readonly-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.readonly-value {
  display: block;
  font-size: 13px;
  color: #303133;
  word-break: break-word;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.history-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.history-item {
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 16px;
  background: #fff;
}

.history-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-job-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.history-job-lines {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.records-section {
  margin-top: 16px;
}

.records-table {
  margin-top: 4px;
}

.record-link {
  color: var(--el-color-primary);
  text-decoration: none;
  font-weight: 600;
}

.record-link:hover {
  text-decoration: underline;
}


.page-body {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 24px;
  align-items: start;
  padding-left: 40px;
}

.upload-column,
.list-column {
  min-width: 0;
}

.list-column .column-card {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 180px);
  overflow: hidden;
}

.column-card {
  padding: 20px;
}

.column-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

@media (max-width: 1200px) {
  .confluence-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .kb-overview {
    grid-template-columns: 1fr;
  }

  .confluence-panel,
  .kb-overview,
  .page-body {
    margin-left: 0;
    padding-left: 0;
  }

  .page-body {
    grid-template-columns: 1fr;
  }

  .connection-readonly,
  .confluence-grid {
    grid-template-columns: 1fr;
  }
}
</style>
