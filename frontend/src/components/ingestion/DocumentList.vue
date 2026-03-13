<template>
  <div class="document-list">
    <!-- Loading -->
    <div v-if="loading" class="list-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- Empty -->
    <el-empty
      v-else-if="documents.length === 0"
      description="暂无文档，请上传第一个文档"
      :image-size="80"
    />

    <!-- Document Items -->
    <div v-else class="doc-items">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="doc-item"
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
            @click="handleDelete(doc)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Delete, Coin, Document, Memo } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getDocuments, deleteDocument } from '@/api/ingest'

const props = defineProps({
  // Pass kbId if needed for future filtering; currently API returns user's docs
  kbId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['deleted'])

const documents = ref([])
const loading = ref(false)
const deletingId = ref(null)

function getFileIcon(fileName) {
  if (!fileName) return Document
  const ext = fileName.split('.').pop().toLowerCase()
  if (ext === 'md' || ext === 'markdown') return Memo
  return Document
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

async function fetchDocuments() {
  loading.value = true
  try {
    const data = await getDocuments()
    documents.value = data || []
  } catch (err) {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档「${doc.title || doc.file_name}」及其所有向量数据吗？此操作不可撤销。`,
      '删除确认',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
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
    ElMessage.success('文档已删除')
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
}

.doc-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  background: #fff;
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

.doc-item-right {
  flex-shrink: 0;
  margin-left: 8px;
}
</style>
