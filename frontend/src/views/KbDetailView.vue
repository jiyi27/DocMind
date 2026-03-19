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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Files, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
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

onMounted(async () => {
  await kbStore.fetchKbDetail(kbId.value)
})

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
  infoFormRef.value?.clearValidate()
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
}

.kb-overview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.overview-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
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

.page-body {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 24px;
  align-items: start;
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
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
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

@media (max-width: 960px) {
  .kb-overview {
    grid-template-columns: 1fr;
  }

  .page-body {
    grid-template-columns: 1fr;
  }

  .connection-readonly {
    grid-template-columns: 1fr;
  }
}
</style>
