<template>
  <div class="search-page">
    <section class="search-hero">
      <div class="hero-panel">
        <div class="search-bar-wrap">
          <el-input
            v-model="query"
            class="search-input"
            size="large"
            placeholder="Ask a question or search by topic..."
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
            class="search-button"
            :loading="isLoading"
            :disabled="!query.trim() || !selectedKbName"
            @click="doSearch"
          >
            Search
          </el-button>
        </div>

        <div class="toolbar-row">
          <div class="filter-item filter-item-wide">
            <span class="filter-label">Knowledge Base</span>
            <el-select
              v-model="selectedKbName"
              class="toolbar-select"
              placeholder="Select a knowledge base"
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
            <span class="filter-label">Max Results</span>
            <el-select v-model="topK" class="compact-select" @change="handleTopKChange">
              <el-option v-for="n in topKOptions" :key="n" :label="n" :value="n" />
            </el-select>
          </div>

          <div class="toolbar-note">
            <span v-if="selectedKbLabel">Current KB: {{ selectedKbLabel }}</span>
            <span v-else>Select a knowledge base to start searching.</span>
          </div>
        </div>

        <div v-if="state === 'idle'" class="suggestion-row">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            type="button"
            class="suggestion-chip"
            @click="applySuggestion(suggestion)"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>
    </section>

    <section class="results-wrap">
      <div v-if="state === 'idle'" class="idle-state">
        <div class="idle-card">
          <el-icon class="idle-icon"><DocumentCopy /></el-icon>
          <h2>Start with a question, not a page number</h2>
          <p>
            Search works best when you describe a topic, a policy, or a concrete problem you want
            to find in your documents.
          </p>
        </div>
      </div>

      <template v-else-if="state === 'loading'">
        <el-skeleton v-for="i in 4" :key="i" class="result-skeleton" animated>
          <template #template>
            <div class="skeleton-card">
              <el-skeleton-item variant="circle" style="width: 40px; height: 40px; flex-shrink: 0" />
              <div style="flex: 1">
                <el-skeleton-item variant="h3" style="width: 48%" />
                <el-skeleton-item variant="text" style="width: 76%; margin-top: 12px" />
                <el-skeleton-item variant="text" style="width: 32%; margin-top: 10px" />
              </div>
              <el-skeleton-item variant="button" style="width: 84px; height: 34px" />
            </div>
          </template>
        </el-skeleton>
      </template>

      <div v-else-if="state === 'empty'" class="empty-state">
        <el-empty description="No matching documents found" :image-size="92" />
        <p class="empty-hint">
          Try a broader query, switch to another knowledge base, or increase max results.
        </p>
      </div>

      <template v-else-if="state === 'results'">
        <div class="results-meta">
          <div class="results-meta-main">
            <span class="results-count">{{ allResults.length }} results</span>
            <span class="results-query">for "{{ lastQuery }}"</span>
          </div>
          <div class="results-meta-side">
            <el-tag size="small" type="info" effect="plain">{{ selectedKbLabel }}</el-tag>
            <span class="results-hint">Scroll to review all matches</span>
          </div>
        </div>

        <div class="result-list">
          <el-card
            v-for="(item, index) in allResults"
            :key="item.sourceLabel"
            class="result-card"
            shadow="never"
          >
            <div class="result-card-body">
              <div class="result-index">{{ index + 1 }}</div>

              <div class="result-content">
                <div class="result-head">
                  <div class="result-title">{{ item.title || item.sourceLabel }}</div>
                  <el-tag size="small" effect="plain" class="result-type-tag">
                    {{ item.url ? 'Web source' : 'Local document' }}
                  </el-tag>
                </div>

                <div class="result-source-label">{{ item.sourceLabel }}</div>

                <div v-if="item.url" class="result-url">
                  <el-icon :size="12"><Link /></el-icon>
                  <a :href="item.url" target="_blank" rel="noopener noreferrer" class="url-link">
                    {{ item.url }}
                  </a>
                </div>
                <div v-else class="result-local">
                  Stored inside your current knowledge base.
                </div>
              </div>

              <div class="result-score-wrap">
                <div class="score-label">Match Score</div>
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
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { DocumentCopy, Link, Search } from '@element-plus/icons-vue'
import { useKbStore } from '@/stores/kb'
import { useAuthStore } from '@/stores/auth'
import { searchDocuments } from '@/api/search'

const kbStore = useKbStore()
const authStore = useAuthStore()

const query = ref('')
const lastQuery = ref('')
const selectedKbName = ref('')
const topK = ref(10)
const topKOptions = [5, 10, 20, 30, 50]
const state = ref('idle')
const allResults = ref([])

const suggestions = [
  'What are the latest onboarding steps?',
  'Find documents about SQLite optimization',
  'Where is the API error handling logic?',
]

const isLoading = computed(() => state.value === 'loading')
const selectedKbLabel = computed(() => {
  const selectedKb = kbStore.kbList.find((kb) => kb.name === selectedKbName.value)
  return selectedKb ? selectedKb.display_name || selectedKb.name : ''
})

function toPercent(score) {
  return `${Math.round(score * 100)}%`
}

function scoreColor(score) {
  if (score >= 0.75) return '#2563eb'
  if (score >= 0.5) return '#059669'
  return '#6b7280'
}

function pickDefaultKb() {
  if (selectedKbName.value || kbStore.kbList.length === 0) return

  const ownedKb = kbStore.kbList.find((kb) => String(kb.id) === String(authStore.kbId))
  selectedKbName.value = ownedKb?.name || kbStore.kbList[0]?.name || ''
}

function applySuggestion(suggestion) {
  query.value = suggestion
}

function handleTopKChange() {
  if (state.value === 'results' || state.value === 'empty') {
    doSearch()
  }
}

async function doSearch() {
  const q = query.value.trim()
  if (!q || !selectedKbName.value) return

  state.value = 'loading'
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
    allResults.value = []
    state.value = 'idle'
  }
}

watch(
  () => kbStore.kbList,
  () => {
    pickDefaultKb()
  },
  { deep: true }
)

onMounted(async () => {
  if (kbStore.kbList.length === 0) {
    await kbStore.fetchKbs()
  }
  pickDefaultKb()
})
</script>

<style scoped>
.search-page {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
  padding: 8px 0 48px;
  box-sizing: border-box;
}

.search-hero {
  position: relative;
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 20px;
  padding: 20px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.16), transparent 34%),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.12), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #f7fbff 52%, #f3f8f7 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.06);
}

.hero-panel {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.92);
  backdrop-filter: blur(12px);
}

.search-bar-wrap {
  display: flex;
  gap: 14px;
  margin-bottom: 18px;
}

.search-input {
  flex: 1;
}

.search-button {
  min-width: 132px;
}

.toolbar-row {
  display: grid;
  grid-template-columns: minmax(280px, 1.4fr) minmax(140px, 180px) minmax(220px, 1fr);
  gap: 16px;
  align-items: end;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-item-wide {
  min-width: 0;
}

.filter-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.toolbar-select,
.compact-select {
  width: 100%;
}

.toolbar-note {
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: 0 2px 2px;
  font-size: 13px;
  color: #475569;
}

.suggestion-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.suggestion-chip {
  border: none;
  padding: 10px 14px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
  cursor: pointer;
  transition: transform 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.suggestion-chip:hover {
  background: #dbeafe;
  color: #1e3a8a;
  transform: translateY(-1px);
}

.results-wrap {
  min-height: 320px;
}

.idle-state,
.empty-state {
  display: flex;
  align-items: center;
  padding: 0;
}

.idle-card {
  width: 100%;
  padding: 40px 32px;
  text-align: center;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e2e8f0;
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.04);
}

.idle-card h2 {
  margin: 0 0 10px;
  font-size: 24px;
  color: #0f172a;
}

.idle-card p,
.empty-hint {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.idle-icon {
  margin-bottom: 18px;
  font-size: 52px;
  color: #60a5fa;
}

.result-skeleton {
  margin-bottom: 14px;
}

.skeleton-card {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.95);
}

.results-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
  padding: 0 4px;
}

.results-meta-main,
.results-meta-side {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.results-count {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.results-query {
  font-size: 14px;
  color: #64748b;
}

.results-hint {
  font-size: 13px;
  color: #64748b;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.result-card {
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.96);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.result-card:hover {
  border-color: rgba(59, 130, 246, 0.35);
  transform: translateY(-1px);
  box-shadow: 0 14px 32px rgba(37, 99, 235, 0.08);
}

.result-card-body {
  display: flex;
  align-items: flex-start;
  gap: 18px;
}

.result-index {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%);
  color: #1d4ed8;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.result-content {
  flex: 1;
  min-width: 0;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.result-title {
  min-width: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-type-tag {
  flex-shrink: 0;
}

.result-source-label {
  margin-bottom: 10px;
  font-size: 12px;
  color: #64748b;
}

.result-url {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
  overflow: hidden;
}

.url-link {
  color: #2563eb;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.url-link:hover {
  text-decoration: underline;
}

.result-local {
  font-size: 13px;
  color: #64748b;
}

.result-score-wrap {
  width: 116px;
  padding: 14px 14px 12px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.score-label {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.score-value {
  margin-bottom: 8px;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
}

.score-bar-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.35s ease;
}

@media (max-width: 960px) {
  .search-hero {
    padding: 16px;
    border-radius: 24px;
  }

  .toolbar-row {
    grid-template-columns: 1fr;
  }

  .toolbar-note {
    min-height: auto;
    padding-bottom: 0;
  }

  .result-card-body {
    flex-direction: column;
  }

  .result-score-wrap {
    width: 100%;
  }
}

@media (max-width: 720px) {
  .search-page {
    padding-bottom: 32px;
  }

  .search-hero {
    padding: 14px;
  }

  .hero-panel,
  .idle-card {
    padding: 18px;
  }

  .page-title {
    font-size: 26px;
  }

  .search-bar-wrap {
    flex-direction: column;
  }

  .search-button {
    width: 100%;
  }

  .result-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
