<template>
  <div class="kb-detail-layout">
    <!-- Left Panel: Document Management -->
    <div class="left-panel">
      <!-- KB Info Header -->
      <div class="panel-header">
        <div class="kb-title-row">
          <el-button
            :icon="ArrowLeft"
            text
            size="small"
            @click="router.push('/')"
          />
          <div class="kb-title-info">
            <h2 class="kb-display-name">{{ kbDetail?.display_name || '知识库详情' }}</h2>
            <span class="kb-slug">{{ kbDetail?.name }}</span>
          </div>
        </div>
        <div v-if="kbDetail" class="kb-stats">
          <el-tag size="small" type="info">{{ kbDetail.document_count ?? 0 }} 篇文档</el-tag>
          <el-tag size="small" type="success">{{ kbDetail.total_points ?? 0 }} Chunks</el-tag>
        </div>
      </div>

      <el-divider />

      <!-- Upload Section -->
      <div class="section">
        <h3 class="section-title">
          <el-icon><Upload /></el-icon>
          上传文档
        </h3>
        <UploadZone @uploaded="handleUploaded" />
      </div>

      <el-divider />

      <!-- Document List Section -->
      <div class="section">
        <h3 class="section-title">
          <el-icon><Files /></el-icon>
          已有文档
        </h3>
        <DocumentList ref="docListRef" :kb-id="kbId" @deleted="handleDeleted" />
      </div>
    </div>

    <!-- Right Panel: Chat Placeholder -->
    <div class="right-panel">
      <div class="chat-placeholder">
        <el-icon class="placeholder-icon"><ChatDotRound /></el-icon>
        <p class="placeholder-title">RAG 对话</p>
        <p class="placeholder-desc">对话功能将在下一阶段实现</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Upload, Files, ChatDotRound } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import UploadZone from '@/components/ingestion/UploadZone.vue'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const route = useRoute()
const router = useRouter()
const kbStore = useKbStore()

const kbId = route.params.id
const kbDetail = ref(null)
const docListRef = ref(null)

onMounted(async () => {
  kbDetail.value = await kbStore.fetchKbDetail(kbId)
})

function handleUploaded() {
  // Refresh document list and KB stats after upload
  docListRef.value?.refresh()
  kbStore.fetchKbDetail(kbId).then((data) => {
    kbDetail.value = data
  })
}

function handleDeleted() {
  // Refresh KB stats after deletion
  kbStore.fetchKbDetail(kbId).then((data) => {
    kbDetail.value = data
  })
}
</script>

<style scoped>
.kb-detail-layout {
  display: flex;
  height: calc(100vh - 60px); /* Subtract AppHeader height */
  overflow: hidden;
}

/* Left Panel */
.left-panel {
  width: 420px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 20px;
  gap: 0;
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kb-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-title-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kb-display-name {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}

.kb-slug {
  font-size: 12px;
  color: #909399;
}

.kb-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin: 0;
}

/* Right Panel */
.right-panel {
  flex: 1;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #c0c4cc;
}

.placeholder-icon {
  font-size: 64px;
  color: #dcdfe6;
}

.placeholder-title {
  font-size: 18px;
  font-weight: 600;
  color: #909399;
  margin: 0;
}

.placeholder-desc {
  font-size: 13px;
  color: #c0c4cc;
  margin: 0;
}
</style>
