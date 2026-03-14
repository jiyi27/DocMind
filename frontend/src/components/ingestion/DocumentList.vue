<template>
  <div class="document-list">
    <!-- Loading -->
    <div v-if="loading" class="list-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- Empty -->
    <el-empty
      v-else-if="documents.length === 0"
      description="No documents yet. Upload your first document."
      :image-size="80"
    />

    <!-- Document Items -->
    <div v-else class="doc-items">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="doc-item"
        role="button"
        tabindex="0"
        @click="goToDetail(doc)"
        @keydown.enter="goToDetail(doc)"
        @keydown.space.prevent="goToDetail(doc)"
      >
        <div class="doc-item-left">
          <el-icon class="doc-icon">
            <component :is="getFileIcon(doc.file_name)" />
          </el-icon>
          <div class="doc-info">
            <p class="doc-title">{{ doc.title || doc.file_name }}</p>
            <p class="doc-meta">
              <el-tag size="small" type="info">{{ doc.doc_type || 'all' }}</el-tag>
              <span class="doc-chunks">
                <el-icon><Coin /></el-icon>
                {{ doc.chunk_count }} Chunks
              </span>
              <span class="doc-date">{{ formatDate(doc.created_at) }}</span>
              <span class="doc-kb" v-if="mode === 'profile' && doc.kb_display_name">
                <el-icon><Folder /></el-icon>
                {{ doc.kb_display_name }}
              </span>
              <span class="doc-uploader" v-if="mode !== 'profile' && doc.uploader_name">
                <el-icon><User /></el-icon>
                {{ doc.uploader_name }}
              </span>
            </p>
          </div>
        </div>
        <div class="doc-item-right">
          <el-button
            type="danger"
            :icon="Delete"
            size="small"
            text
            :loading="deletingId === doc.id"
            @click.stop="handleDelete(doc)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Delete, Coin, Document, Memo, User, Folder } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getDocuments, getDocumentsByKb, deleteDocument } from '@/api/ingest'

const props = defineProps({
  // Pass kbId if needed for future filtering; currently API returns user's docs
  kbId: {
    type: String,
    default: null,
  },
  mode: {
    type: String,
    default: 'kb', // 'kb' or 'profile'
  },
  kbName: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['deleted'])

const documents = ref([])
const loading = ref(false)
const deletingId = ref(null)
const router = useRouter()

function getFileIcon(fileName) {
  if (!fileName) return Document
  const ext = fileName.split('.').pop().toLowerCase()
  if (ext === 'md' || ext === 'markdown') return Memo
  return Document
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function goToDetail(doc) {
  if (!doc?.id) return
  const kbId = props.kbId || doc.kb_id || null
  const kbName = props.kbName || doc.kb_display_name || null
  router.push({
    name: 'DocumentDetail',
    params: { id: doc.id },
    query: {
      kbId: kbId || undefined,
      kbName: kbName || undefined,
      title: doc.title || undefined,
      fileName: doc.file_name || undefined,
      docType: doc.doc_type || undefined,
      chunkCount: doc.chunk_count ?? undefined,
    },
  })
}

async function fetchDocuments() {
  loading.value = true
  try {
    const res = props.kbId
      ? await getDocumentsByKb(props.kbId)
      : await getDocuments()
    // API returns { total, documents } envelope
    documents.value = res?.documents ?? res ?? []
  } catch (err) {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete "${doc.title || doc.file_name}" and all its vector data? This cannot be undone.`,
      'Confirm Deletion',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    return // User cancelled
  }

  deletingId.value = doc.id
  try {
    await deleteDocument(doc.id)
    documents.value = documents.value.filter((d) => d.id !== doc.id)
    ElMessage.success('Document deleted')
    emit('deleted', doc.id)
  } catch (err) {
    // Error handled by interceptor
  } finally {
    deletingId.value = null
  }
}

// Expose refresh method so parent can call it after upload
function refresh() {
  fetchDocuments()
}

defineExpose({ refresh })

onMounted(() => {
  fetchDocuments()
})
</script>

<style scoped>
.document-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.list-loading {
  padding: 8px 0;
}

.doc-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.doc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fafafa;
  transition: box-shadow 0.2s;
  cursor: pointer;
}

.doc-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  background: #fff;
}

.doc-item:focus-visible {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.doc-item-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.doc-icon {
  font-size: 24px;
  color: #409eff;
  flex-shrink: 0;
  margin-top: 2px;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  flex-wrap: wrap;
}

.doc-chunks {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: #909399;
}

.doc-date {
  font-size: 12px;
  color: #c0c4cc;
}

.doc-uploader,
.doc-kb {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: #909399;
}

.doc-item-right {
  flex-shrink: 0;
  margin-left: 8px;
}
</style>
