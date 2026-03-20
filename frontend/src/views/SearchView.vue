<template>
  <div class="search-page">
    <!-- Header -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon class="title-icon"><Search /></el-icon>
        Document Search
      </h1>
      <p class="page-desc">Search across your knowledge base using semantic similarity</p>
    </div>

    <!-- Search Bar -->
    <div class="search-bar-wrap">
      <el-input
        v-model="query"
        class="search-input"
        size="large"
        placeholder="Enter your query..."
        clearable
        @keyup.enter="doSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!query.trim() || !selectedKbName"
        @click="doSearch"
      >
        Search
      </el-button>
    </div>

    <!-- Filters -->
    <div class="filter-row">
      <div class="filter-item">
        <span class="filter-label">Knowledge Base</span>
        <el-select
          v-model="selectedKbName"
          placeholder="Select a knowledge base"
          style="width: 220px"
          :loading="kbStore.loading"
        >
          <el-option
            v-for="kb in kbStore.kbList"
            :key="kb.id"
            :label="kb.display_name || kb.name"
            :value="kb.name"
          />
        </el-select>
      </div>
      <div class="filter-item">
        <span class="filter-label">Results per page</span>
        <el-select v-model="topK" style="width: 100px" @change="handleTopKChange">
          <el-option v-for="n in topKOptions" :key="n" :label="n" :value="n" />
        </el-select>
      </div>
    </div>

    <!-- Results -->
    <div class="results-wrap">
      <!-- Idle state -->
      <div v-if="state === 'idle'" class="idle-state">
        <el-icon class="idle-icon"><DocumentCopy /></el-icon>
        <p>Enter a query above to search your knowledge base</p>
      </div>

      <!-- Loading skeleton -->
      <template v-else-if="state === 'loading'">
        <el-skeleton v-for="i in 3" :key="i" class="result-skeleton" animated>
          <template #template>
            <div class="skeleton-card">
              <el-skeleton-item variant="circle" style="width: 32px; height: 32px; flex-shrink: 0" />
              <div style="flex: 1">
                <el-skeleton-item variant="h3" style="width: 55%" />
                <el-skeleton-item variant="text" style="width: 35%; margin-top: 8px" />
              </div>
              <el-skeleton-item variant="button" style="width: 68px; height: 24px" />
            </div>
          </template>
        </el-skeleton>
      </template>

      <!-- Empty results -->
      <el-empty
        v-else-if="state === 'empty'"
        description="No matching documents found"
        :image-size="80"
      />

      <!-- Results list -->
      <template v-else-if="state === 'results'">
        <div class="results-meta">
          <span class="results-count">{{ allResults.length }} results found</span>
          <span class="results-query">for <em>"{{ lastQuery }}"</em></span>
        </div>

        <div class="result-list">
          <el-card
            v-for="item in pagedResults"
            :key="item.sourceLabel"
            class="result-card"
            shadow="never"
          >
            <div class="result-card-body">
              <!-- Index badge -->
              <div class="result-index">{{ item.index }}</div>

              <!-- Main content -->
              <div class="result-content">
                <div class="result-title">{{ item.title || item.sourceLabel }}</div>
                <div v-if="item.url" class="result-url">
                  <el-icon :size="12"><Link /></el-icon>
                  <a :href="item.url" target="_blank" rel="noopener noreferrer" class="url-link">
                    {{ item.url }}
                  </a>
                </div>
                <div v-else class="result-local">
                  <el-tag size="small" type="info" effect="plain">Local document</el-tag>
                </div>
              </div>

              <!-- Score badge -->
              <div class="result-score-wrap">
                <div class="score-label">Match</div>
                <div class="score-value" :style="{ color: scoreColor(item.score) }">
                  {{ toPercent(item.score) }}
                </div>
                <div class="score-bar-track">
                  <div
                    class="score-bar-fill"
                    :style="{ width: toPercent(item.score), backgroundColor: scoreColor(item.score) }"
                  />
                </div>
              </div>
            </div>
          </el-card>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination-wrap">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="topK"
            :total="allResults.length"
            layout="prev, pager, next"
            background
            @current-change="currentPage = $event"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Search, Link, DocumentCopy } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import { searchDocuments } from '@/api/search'

const kbStore = useKbStore()

// ── Search state ──────────────────────────────────────────
const query = ref('')
const lastQuery = ref('')
const selectedKbName = ref('')
const topK = ref(5)
const topKOptions = [3, 5, 10, 20]

// 'idle' | 'loading' | 'results' | 'empty'
const state = ref('idle')
const allResults = ref([])

// ── Pagination ────────────────────────────────────────────
const currentPage = ref(1)
const totalPages = computed(() => Math.ceil(allResults.value.length / topK.value))
const pagedResults = computed(() => {
  const start = (currentPage.value - 1) * topK.value
  return allResults.value.slice(start, start + topK.value).map((item, i) => ({
    ...item,
    index: start + i + 1,
  }))
})

// ── Score helpers ─────────────────────────────────────────
function toPercent(score) {
  return `${Math.round(score * 100)}%`
}

function scoreColor(score) {
  if (score >= 0.75) return '#409eff'
  if (score >= 0.5) return '#67c23a'
  return '#909399'
}

// ── Actions ───────────────────────────────────────────────
function handleTopKChange() {
  // When user changes top_k, re-run search if results are already showing
  if (state.value === 'results' || state.value === 'empty') {
    doSearch()
  }
}

async function doSearch() {
  const q = query.value.trim()
  if (!q || !selectedKbName.value) return

  state.value = 'loading'
  currentPage.value = 1
  lastQuery.value = q

  try {
    const data = await searchDocuments({
      query: q,
      kbName: selectedKbName.value,
      topK: topK.value,
    })
    allResults.value = data.results ?? []
    state.value = allResults.value.length > 0 ? 'results' : 'empty'
  } catch {
    // Error already shown by http interceptor
    state.value = 'idle'
  }
}

onMounted(() => {
  if (kbStore.kbList.length === 0) {
    kbStore.fetchKbs()
  }
})
</script>

<style scoped>
.search-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 8px 0 48px;
}

/* Header */
.page-header {
  margin-bottom: 28px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 6px;
}

.title-icon {
  font-size: 22px;
  color: #409eff;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

/* Search bar */
.search-bar-wrap {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  flex: 1;
}

/* Filters */
.filter-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

/* Idle state */
.idle-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 0;
  color: #c0c4cc;
  gap: 16px;
  font-size: 14px;
}

.idle-icon {
  font-size: 56px;
}

/* Skeleton */
.result-skeleton {
  margin-bottom: 12px;
}

.skeleton-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
}

/* Results meta */
.results-meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 16px;
  font-size: 13px;
}

.results-count {
  font-weight: 600;
  color: #303133;
}

.results-query {
  color: #909399;
}

.results-query em {
  font-style: normal;
  color: #606266;
}

/* Result cards */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-card {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.result-card:hover {
  border-color: #c6d9ff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.10);
}

.result-card-body {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* Index badge */
.result-index {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: rgba(64, 158, 255, 0.1);
  color: #409eff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Content */
.result-content {
  flex: 1;
  min-width: 0;
}

.result-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-url {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  overflow: hidden;
}

.url-link {
  color: #409eff;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.url-link:hover {
  text-decoration: underline;
}

.result-local {
  margin-top: 2px;
}

/* Score */
.result-score-wrap {
  flex-shrink: 0;
  width: 72px;
  text-align: center;
}

.score-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 2px;
}

.score-value {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 6px;
}

.score-bar-track {
  height: 4px;
  background-color: #f0f2f5;
  border-radius: 2px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* Pagination */
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 28px;
}
</style>
