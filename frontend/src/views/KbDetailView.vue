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
            :disabled="!kbDetail.confluence_root_page_id || !kbDetail.confluence_capability_enabled"
            @click="triggerSyncNow"
          >
            Sync Now
          </el-button>
        </div>
      </div>

      <div class="confluence-grid">
        <div class="confluence-stat">
          <span class="confluence-label">Root Page</span>
          <span class="confluence-value">
            {{ kbDetail.confluence_root_page_title || kbDetail.confluence_root_page_id || 'Not configured' }}
          </span>
        </div>
        <div class="confluence-stat">
          <span class="confluence-label">Auto Sync</span>
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
          <span class="confluence-label">Last Sync Status</span>
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
      <el-alert
        :title="kbDetail?.confluence_capability_message || 'Confluence status unavailable.'"
        :type="kbDetail?.confluence_capability_enabled ? 'success' : 'warning'"
        :closable="false"
        show-icon
        class="dialog-alert"
      />

      <el-form
        ref="confluenceFormRef"
        :model="confluenceForm"
        :rules="confluenceRules"
        label-position="top"
      >
        <el-form-item label="Root Page URL" prop="root_page_url">
          <el-input
            v-model="confluenceForm.root_page_url"
            placeholder="Confluence page URL"
            clearable
          />
          <div class="form-hint">
            <template v-if="kbDetail?.confluence_root_page_title || kbDetail?.confluence_root_page_id">
              Currently bound to: <strong>{{ kbDetail.confluence_root_page_title || kbDetail.confluence_root_page_id }}</strong>
            </template>
          </div>
        </el-form-item>

        <el-form-item label="Retrieval Mode" prop="retrieval_mode">
          <el-radio-group v-model="confluenceForm.retrieval_mode">
            <el-radio-button label="chunk">Fragment</el-radio-button>
            <el-radio-button label="full_doc">Full Article</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="Sync Interval" prop="sync_interval_minutes">
          <el-input-number
            v-model="confluenceForm.sync_interval_minutes"
            :min="5"
            :step="5"
            :precision="0"
          />
          <div class="form-hint">Auto sync checks this KB on the configured minute interval. Minimum 5 minutes.</div>
        </el-form-item>

        <el-form-item label="Auto Sync">
          <div class="switch-field">
            <el-switch
              v-model="confluenceForm.sync_enabled"
              :disabled="!kbDetail?.confluence_capability_enabled"
            />
            <div class="switch-field-copy">
              <div class="form-hint form-hint--spacious">
                Automatically sync content from the configured Confluence page tree.
              </div>
              <div
                v-if="!kbDetail?.confluence_capability_enabled"
                class="form-hint form-hint--spacious"
              >
                Configure Confluence Base URL and PAT in System Settings first.
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="confluenceDialogVisible = false">Cancel</el-button>
        <el-button
          type="primary"
          :loading="confluenceSaving"
          :disabled="!confluenceForm.root_page_url.trim()"
          @click="submitConfluenceForm"
        >
          Save
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="syncPreviewDialogVisible"
      title="Confirm Confluence Sync"
      width="640px"
      :close-on-click-modal="false"
      @closed="syncPreview = null"
    >
      <div v-if="syncPreview" class="sync-preview-dialog">
        <div class="sync-preview-header">
          <div class="sync-preview-title">Preview Result</div>
          <p class="sync-preview-copy">
            We scanned the current Confluence page tree and estimated the changes below before starting the sync job.
          </p>
        </div>

        <div class="sync-preview-overview">
          <div class="sync-preview-card">
            <span class="sync-preview-card__label">Scanned Pages</span>
            <strong class="sync-preview-card__value">{{ syncPreview.scanned || 0 }}</strong>
          </div>
          <div class="sync-preview-card sync-preview-card--accent">
            <span class="sync-preview-card__label">Pending Changes</span>
            <strong class="sync-preview-card__value">{{ syncPreview.total_operations || 0 }}</strong>
          </div>
        </div>

        <div class="sync-preview-breakdown">
          <div class="sync-preview-stat sync-preview-stat--create">
            <span class="sync-preview-stat__label">Create</span>
            <strong class="sync-preview-stat__value">{{ syncPreview.created || 0 }}</strong>
          </div>
          <div class="sync-preview-stat sync-preview-stat--update">
            <span class="sync-preview-stat__label">Update</span>
            <strong class="sync-preview-stat__value">{{ syncPreview.updated || 0 }}</strong>
          </div>
          <div class="sync-preview-stat sync-preview-stat--delete">
            <span class="sync-preview-stat__label">Delete</span>
            <strong class="sync-preview-stat__value">{{ syncPreview.deleted || 0 }}</strong>
          </div>
          <div class="sync-preview-stat sync-preview-stat--neutral">
            <span class="sync-preview-stat__label">Unchanged</span>
            <strong class="sync-preview-stat__value">{{ syncPreview.unchanged || 0 }}</strong>
          </div>
        </div>

        <el-alert
          v-if="syncPreview.deleted > 0"
          :title="`${syncPreview.deleted} document(s) will be removed from this KB because they no longer exist in the scanned page tree.`"
          type="warning"
          :closable="false"
          show-icon
          class="sync-preview-alert"
        />
      </div>

      <template #footer>
        <el-button @click="syncPreviewDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="syncTriggering" @click="confirmTriggerSync">
          Start Sync
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

              <template v-else-if="jobRecords.length === 0">
                <el-empty
                  v-if="job.summary && job.summary.scanned > 0"
                  :description="`Scanned ${job.summary.scanned} page(s) — all up to date, no updates needed.`"
                  :image-size="64"
                />
                <el-empty
                  v-else-if="job.summary && job.summary.scanned === 0"
                  description="No pages found in the Confluence space."
                  :image-size="64"
                />
                <el-empty
                  v-else
                  description="No record details for this job."
                  :image-size="64"
                />
              </template>

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
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Files, Upload } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import UploadZone from '@/components/ingestion/UploadZone.vue'
import DocumentList from '@/components/ingestion/DocumentList.vue'
import { useKbDetail } from '@/composables/kb/useKbDetail'
import { useKbConfluenceSync } from '@/composables/kb/useKbConfluenceSync'
import { formatDateTime } from '@/utils/format/date'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const kbStore = useKbStore()

const kbId = computed(() => route.params.id)
const kbDetail = computed(() => kbStore.currentKb)
const canEdit = computed(() => authStore.canManageKb(kbId.value))
const docListRef = ref(null)
const {
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
} = useKbDetail({ kbId, kbDetail, kbStore })

const {
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
  toggleJobDetails,
} = useKbConfluenceSync({ kbId, kbDetail, kbStore })

watch(
  kbId,
  async () => {
    await kbStore.fetchKbDetail(kbId.value)
    syncFormsFromKb()
    syncFormFromKb()
  },
  { immediate: true },
)

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

.sync-preview-dialog {
  display: grid;
  gap: 18px;
}

.sync-preview-header {
  display: grid;
  gap: 6px;
}

.sync-preview-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.sync-preview-copy {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
}

.sync-preview-overview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sync-preview-card,
.sync-preview-stat {
  border-radius: 10px;
  padding: 16px;
  display: grid;
  gap: 8px;
  border: 1px solid #ebeef5;
  background: #fafafa;
}

.sync-preview-card--accent {
  background: #f4f8ff;
  border-color: #c6d8ff;
}

.sync-preview-card__label,
.sync-preview-stat__label {
  font-size: 12px;
  color: #909399;
}

.sync-preview-card__value,
.sync-preview-stat__value {
  font-size: 28px;
  line-height: 1;
  color: #303133;
}

.sync-preview-breakdown {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.sync-preview-stat--create {
  background: #f3fbf6;
  border-color: #ccebd6;
}

.sync-preview-stat--create .sync-preview-stat__value {
  color: #1f8f4e;
}

.sync-preview-stat--update {
  background: #fff8ee;
  border-color: #f4ddba;
}

.sync-preview-stat--update .sync-preview-stat__value {
  color: #b76a00;
}

.sync-preview-stat--delete {
  background: #fff2f0;
  border-color: #f3c6c3;
}

.sync-preview-stat--delete .sync-preview-stat__value {
  color: #cf3f36;
}

.sync-preview-stat--neutral {
  background: #f7f8fa;
}

.sync-preview-alert {
  margin-top: 4px;
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

.form-hint--spacious {
  margin-top: 0;
}

.switch-field {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.switch-field-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  justify-content: center;
  min-height: 32px;
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
  display: flex;
  gap: 24px;
  align-items: stretch;
  min-height: calc(100vh - 180px);
  padding-left: 40px;
}

.upload-column,
.list-column {
  display: flex;
  align-self: stretch;
  min-width: 0;
}

.upload-column {
  flex: 0 0 420px;
}

.list-column {
  flex: 1 1 auto;
}

.page-body .column-card {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 100%;
}

.list-column .column-card {
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

  .sync-preview-breakdown {
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
    flex-direction: column;
  }

  .connection-readonly,
  .confluence-grid {
    grid-template-columns: 1fr;
  }

  .sync-preview-overview,
  .sync-preview-breakdown {
    grid-template-columns: 1fr;
  }
}
</style>
