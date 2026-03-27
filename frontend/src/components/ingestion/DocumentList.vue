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
            <p class="doc-title">
              <span class="doc-title-text">{{ doc.title || doc.file_name }}</span>
              <el-tag v-if="doc.status === 'pending'" class="doc-status-tag" size="small" type="info">Pending</el-tag>
              <el-tag v-else-if="doc.status === 'processing'" class="doc-status-tag doc-status-tag-processing" size="small" type="warning">
                <el-icon class="doc-status-icon is-loading"><Loading /></el-icon>
                <span>Processing</span>
              </el-tag>
              <el-tag v-else-if="doc.status === 'failed'" class="doc-status-tag" size="small" type="danger">
                Failed
              </el-tag>
              <el-tag v-else-if="doc.status === 'completed'" class="doc-status-tag" size="small" type="success">
                Ready
              </el-tag>
            </p>
            <p class="doc-meta">
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
              <el-tooltip v-if="doc.status === 'failed' && doc.error_message" :content="doc.error_message" placement="top">
                <span class="doc-error-msg">
                  <el-icon><Warning /></el-icon>
                  View Error
                </span>
              </el-tooltip>
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
import { Delete, Coin, User, Folder, Loading, Warning } from '@element-plus/icons-vue'
import { useDocumentList } from '@/composables/documents/useDocumentList'
import { getFileIcon } from '@/utils/documents/file'
import { formatDate } from '@/utils/format/date'

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
const { documents, loading, deletingId, goToDetail, handleDelete, refresh } = useDocumentList(props, emit)

// Expose refresh method so parent can call it after upload
defineExpose({ refresh })
</script>

<style scoped>
.document-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  gap: 10px;
}

.doc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px;
  border: 1px solid var(--dm-border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.88);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  cursor: pointer;
}

.doc-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  border-color: rgba(37, 99, 235, 0.18);
  background: #fff;
}

.doc-item:focus-visible {
  outline: 2px solid var(--dm-primary);
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
  color: var(--dm-primary);
  flex-shrink: 0;
  margin-top: 2px;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--dm-text);
  margin: 0 0 6px;
  min-width: 0;
}

.doc-title-text {
  min-width: 0;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  vertical-align: middle;
  line-height: 1;
}

.doc-status-tag :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  line-height: 1;
}

.doc-status-tag-processing {
  padding-top: 0;
  padding-bottom: 0;
}

.doc-status-icon {
  font-size: 12px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  flex-wrap: wrap;
  color: var(--dm-text-soft);
}

.doc-chunks {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--dm-text-soft);
}

.doc-date {
  font-size: 12px;
  color: #94a3b8;
}

.doc-uploader,
.doc-kb,
.doc-error-msg {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--dm-text-soft);
}

.doc-error-msg {
  color: #f56c6c;
  cursor: help;
}

.doc-item-right {
  flex-shrink: 0;
  margin-left: 8px;
}
</style>
