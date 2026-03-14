<template>
  <div class="kb-detail-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" text @click="router.push('/')" />
        <div class="kb-title-info">
          <h1 class="kb-display-name">{{ kbDetail?.display_name || 'Knowledge Base' }}</h1>
          <span class="kb-slug">{{ kbDetail?.name }}</span>
        </div>
      </div>
      <div v-if="kbDetail" class="kb-stats">
        <el-tag type="info">{{ kbDetail.document_count ?? 0 }} Documents</el-tag>
        <el-tag type="success">{{ kbDetail.total_points ?? 0 }} Chunks</el-tag>
      </div>
    </div>

    <!-- Main Content: Two columns -->
    <div class="page-body">
      <!-- Upload Column -->
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

      <!-- Document List Column -->
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Upload, Files } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import UploadZone from '@/components/ingestion/UploadZone.vue'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const route = useRoute()
const router = useRouter()
const kbStore = useKbStore()

const kbId = computed(() => route.params.id)
const kbDetail = computed(() => kbStore.currentKb)
const docListRef = ref(null)

onMounted(async () => {
  await kbStore.fetchKbDetail(kbId.value)
})

function handleUploaded() {
  // Refresh document list and KB stats after upload
  docListRef.value?.refresh()
  kbStore.fetchKbDetail(kbId.value)
}

function handleDeleted() {
  // Refresh KB stats after deletion
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

/* Page Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
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

.kb-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Two-column body */
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

</style>
