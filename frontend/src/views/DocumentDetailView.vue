<template>
  <div class="document-detail">
    <div class="page-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" text @click="router.back()" />
        <div class="doc-title-info">
          <h1 class="doc-title">{{ docTitle }}</h1>
          <span v-if="docMeta.file_name" class="doc-file">{{ docMeta.file_name }}</span>
        </div>
      </div>
      <div class="header-right">
        <el-tag type="info">{{ displayedChunkCount }} Chunks</el-tag>
        <el-tag v-if="docMeta.doc_type" type="success">{{ docMeta.doc_type }}</el-tag>
      </div>
    </div>

    <div class="page-body">
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">Knowledge Base</div>
          <div class="summary-value">
            <el-icon><Folder /></el-icon>
            <span>{{ kbDisplayName }}</span>
          </div>
          <div v-if="kbSlug" class="summary-sub">{{ kbSlug }}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">Uploaded</div>
          <div class="summary-value">{{ formatDate(docMeta.created_at) }}</div>
        </div>
      </div>

      <div class="chunks-card">
        <div class="chunks-header">
          <h3 class="section-title">
            <el-icon><List /></el-icon>
            Chunks
          </h3>
          <span class="chunks-count">{{ chunkTotal }} total</span>
        </div>
        <el-divider />

        <div v-if="loadingChunks && chunks.length === 0" class="chunks-loading">
          <el-skeleton :rows="6" animated />
        </div>
        <el-empty
          v-else-if="chunks.length === 0"
          description="No chunks found for this document."
          :image-size="80"
        />
        <div v-else class="chunk-list">
          <div
            v-for="(chunk, index) in chunks"
            :key="chunk.point_id || `${docId}-${index}`"
            class="chunk-item"
          >
            <div class="chunk-meta">
              <span class="chunk-index">Chunk {{ index + 1 }}</span>
              <span class="chunk-chars">{{ chunk.char_count ?? '-' }} chars</span>
            </div>
            <p class="chunk-content">{{ chunk.content }}</p>
          </div>
        </div>

        <div class="load-more">
          <el-button v-if="hasMore" :loading="loadingMore" @click="loadMore">
            Load More
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Folder, List } from '@element-plus/icons-vue'
import { getDocumentById, getDocumentChunks } from '@/api/ingest'

const route = useRoute()
const router = useRouter()

const docId = computed(() => route.params.id)

const preset = {
  title: typeof route.query.title === 'string' ? route.query.title : '',
  fileName: typeof route.query.fileName === 'string' ? route.query.fileName : '',
  docType: typeof route.query.docType === 'string' ? route.query.docType : '',
  kbName: typeof route.query.kbName === 'string' ? route.query.kbName : '',
  chunkCount: typeof route.query.chunkCount === 'string'
    ? Number(route.query.chunkCount)
    : null,
  kbId: typeof route.query.kbId === 'string' ? route.query.kbId : null,
}

const docMeta = ref({
  title: preset.title || null,
  file_name: preset.fileName || null,
  doc_type: preset.docType || null,
  chunk_count: Number.isFinite(preset.chunkCount) ? preset.chunkCount : null,
  created_at: null,
  kb_id: preset.kbId || null,
  kb_display_name: preset.kbName || null,
})

const kbDetail = ref(null)
const chunks = ref([])
const chunkTotal = ref(0)
const loadingMeta = ref(false)
const loadingChunks = ref(false)
const loadingMore = ref(false)
const limit = 20
const offset = ref(0)

const docTitle = computed(() => {
  return docMeta.value.title || docMeta.value.file_name || 'Document'
})

const kbDisplayName = computed(() => {
  return (
    kbDetail.value?.display_name ||
    docMeta.value.kb_display_name ||
    preset.kbName ||
    'Unknown KB'
  )
})

const kbSlug = computed(() => kbDetail.value?.name || null)

const displayedChunkCount = computed(() => {
  return docMeta.value.chunk_count ?? chunkTotal.value ?? 0
})

const hasMore = computed(() => chunks.value.length < chunkTotal.value)

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

async function fetchMeta() {
  loadingMeta.value = true
  try {
    const doc = await getDocumentById(docId.value)
    if (doc) {
      docMeta.value = { ...docMeta.value, ...doc }
      // kb info is already included in the response (kb_display_name, kb_name)
      kbDetail.value = doc.kb_name ? { name: doc.kb_name, display_name: doc.kb_display_name } : null
    }
  } catch {
    // Errors handled by interceptor
  } finally {
    loadingMeta.value = false
  }
}

async function fetchChunks(reset = false) {
  if (!docId.value) return
  if (reset) {
    offset.value = 0
    chunks.value = []
  }

  if (reset) {
    loadingChunks.value = true
  } else {
    loadingMore.value = true
  }

  try {
    const res = await getDocumentChunks(docId.value, offset.value, limit)
    const items = res?.items ?? []
    chunkTotal.value = res?.total ?? 0
    if (reset) {
      chunks.value = items
    } else {
      chunks.value = [...chunks.value, ...items]
    }
    offset.value = chunks.value.length
  } catch {
    // Errors handled by interceptor
  } finally {
    loadingChunks.value = false
    loadingMore.value = false
  }
}

function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  fetchChunks(false)
}

onMounted(async () => {
  await fetchMeta()
  fetchChunks(true)
})
</script>

<style scoped>
.document-detail {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

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

.doc-title-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-title {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin: 0;
  line-height: 1.3;
}

.doc-file {
  font-size: 12px;
  color: #909399;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.page-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.summary-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #909399;
}

.summary-value {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.summary-sub {
  font-size: 12px;
  color: #c0c4cc;
}

.chunks-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 20px;
}

.chunks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.chunks-count {
  font-size: 12px;
  color: #909399;
}

.chunks-loading {
  padding: 8px 0;
}

.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chunk-item {
  border: 1px solid #ebeef5;
  background: #fafafa;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chunk-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.chunk-content {
  margin: 0;
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.load-more {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
@media (max-width: 768px) {
  .document-detail {
    padding: 0 4px;
  }
}
</style>
