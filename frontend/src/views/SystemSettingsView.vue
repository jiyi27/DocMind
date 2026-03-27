<template>
  <div class="settings-view">
    <div v-if="loading" class="loading-panel">
      <el-skeleton :rows="10" animated />
    </div>

    <section v-else class="settings-shell">
      <div class="settings-status">
        <span class="status-item">
          <span class="status-label">Qdrant</span>
          <el-tag :type="settings.qdrant.configured ? 'success' : 'warning'" effect="plain">
            {{ settings.qdrant.configured ? 'Configured' : 'Missing' }}
          </el-tag>
        </span>
        <span class="status-item">
          <span class="status-label">LLM</span>
          <el-tag :type="settings.llm.configured ? 'success' : 'warning'" effect="plain">
            {{ settings.llm.configured ? 'Configured' : 'Incomplete' }}
          </el-tag>
        </span>
        <span class="status-item">
          <span class="status-label">Image Vision</span>
          <el-tag :type="settings.ingestion.image_vision_configured ? 'success' : 'warning'" effect="plain">
            {{ settings.ingestion.image_vision_configured ? 'Configured' : 'Not Configured' }}
          </el-tag>
        </span>
        <span class="status-item">
          <span class="status-label">Confluence</span>
          <el-tag :type="settings.confluence.configured ? 'success' : 'warning'" effect="plain">
            {{ settings.confluence.configured ? 'Configured' : 'Not Configured' }}
          </el-tag>
        </span>
      </div>

      <el-form class="settings-stack" label-position="top" @submit.prevent>
        <section class="settings-section">
          <div class="section-head">
            <div>
              <h3 class="section-title">Qdrant</h3>
              <p class="section-desc">Vector store endpoint used by ingestion and retrieval.</p>
            </div>
          </div>
          <div class="settings-form-grid">
            <el-form-item class="full-span" label="Qdrant URL">
              <el-input v-model="form.qdrant.url" placeholder="http://localhost:6333" />
            </el-form-item>
          </div>
        </section>

        <section class="settings-section">
          <div class="section-head">
            <div>
              <h3 class="section-title">LLM</h3>
              <p class="section-desc">Shared chat model connection used by the backend.</p>
            </div>
          </div>
          <div class="settings-form-grid">
            <el-form-item label="Base URL">
              <el-input v-model="form.llm.base_url" placeholder="https://api.openai.com/v1" />
            </el-form-item>
            <el-form-item label="Model">
              <el-input v-model="form.llm.model" placeholder="gpt-5-mini" />
            </el-form-item>
            <el-form-item class="full-span" label="API Key">
              <el-input
                v-model="form.llm.api_key"
                type="password"
                show-password
                placeholder="API key"
              />
              <div class="field-hint">Leave empty and save to clear the stored key.</div>
            </el-form-item>
          </div>
        </section>

        <section class="settings-section">
          <div class="section-head">
            <div>
              <h3 class="section-title">Ingestion</h3>
              <p class="section-desc">Chunking and optional image processing defaults.</p>
            </div>
          </div>
          <div class="settings-form-grid">
            <el-form-item label="Chunk Size">
              <el-input-number v-model="form.ingestion.chunk_size" :min="1" :max="5000" />
            </el-form-item>
            <el-form-item label="Chunk Overlap">
              <el-input-number v-model="form.ingestion.chunk_overlap" :min="0" :max="2000" />
            </el-form-item>
            <el-form-item label="Image Processor">
              <el-select v-model="form.ingestion.image_processor">
                <el-option label="None" value="none" />
                <el-option label="OCR" value="ocr" />
                <el-option label="Multimodal" value="multimodal" />
              </el-select>
              <div v-if="requiresMultimodalVision" class="field-hint field-hint--warning">
                Multimodal requires Vision Base URL, Vision Model, and Vision API Key.
              </div>
            </el-form-item>
            <el-form-item label="Code Summarization">
              <el-switch v-model="form.ingestion.enable_code_summarization" />
            </el-form-item>
            <el-form-item label="Vision Base URL">
              <el-input
                v-model="form.ingestion.image_vision_base_url"
                placeholder="https://api.openai.com/v1"
              />
            </el-form-item>
            <el-form-item label="Vision Model">
              <el-input v-model="form.ingestion.image_vision_model" placeholder="gpt-4.1-mini" />
            </el-form-item>
            <el-form-item class="full-span" label="Vision API Key">
              <el-input
                v-model="form.ingestion.image_vision_api_key"
                type="password"
                show-password
                placeholder="Vision API key"
              />
              <div class="field-hint">Leave empty and save to clear the stored key.</div>
            </el-form-item>
          </div>
        </section>

        <section class="settings-section">
          <div class="section-head">
            <div>
              <h3 class="section-title">Retrieval</h3>
              <p class="section-desc">Search breadth, chat history window, and full-doc expansion caps.</p>
            </div>
          </div>
          <div class="settings-form-grid">
            <el-form-item label="Top K">
              <el-input-number v-model="form.retrieval.top_k" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="Chat Max Messages">
              <el-input-number v-model="form.chat.max_messages" :min="0" :max="500" />
            </el-form-item>
            <el-form-item label="Max Full Docs">
              <el-input-number v-model="form.retrieval.max_full_docs" :min="1" :max="20" />
            </el-form-item>
            <el-form-item label="Max Full Doc Chars">
              <el-input-number
                v-model="form.retrieval.max_full_doc_chars"
                :min="1"
                :max="200000"
              />
            </el-form-item>
          </div>
        </section>

        <section class="settings-section">
          <div class="section-head">
            <div>
              <h3 class="section-title">Confluence</h3>
              <p class="section-desc">System-wide Confluence credentials used by KB sync features.</p>
            </div>
          </div>
          <div class="settings-form-grid">
            <el-form-item class="full-span" label="Base URL">
              <el-input
                v-model="form.confluence.base_url"
                placeholder="https://your-domain.atlassian.net/wiki"
              />
            </el-form-item>
            <el-form-item class="full-span" label="PAT">
              <el-input
                v-model="form.confluence.pat"
                type="password"
                show-password
                placeholder="Confluence personal access token"
              />
              <div class="field-hint">Leave empty and save to clear the stored token.</div>
            </el-form-item>
          </div>
        </section>
      </el-form>

      <div class="section-actions">
        <el-button type="primary" :loading="saving" @click="saveSettings">
          Save All Settings
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getRuntimeSettings, updateRuntimeSettings } from '@/api/admin'

const loading = ref(true)
const saving = ref(false)

const settings = reactive({
  qdrant: {
    url: '',
    configured: false,
  },
  llm: {
    base_url: '',
    api_key: '',
    model: '',
    configured: false,
    status: {
      configured: false,
      missing_fields: [],
      message: '',
    },
    api_key_masked: '',
    api_key_configured: false,
  },
  ingestion: {
    chunk_size: 500,
    chunk_overlap: 50,
    enable_code_summarization: false,
    image_processor: 'none',
    image_vision_api_key: '',
    image_vision_base_url: '',
    image_vision_model: '',
    image_vision_configured: false,
    image_vision_status: {
      configured: false,
      missing_fields: [],
      message: '',
    },
    image_vision_api_key_masked: '',
    image_vision_api_key_configured: false,
  },
  chat: {
    max_messages: 20,
  },
  retrieval: {
    top_k: 3,
    max_full_docs: 2,
    max_full_doc_chars: 8000,
  },
  confluence: {
    base_url: '',
    pat: '',
    enabled: false,
    configured: false,
    status: {
      configured: false,
      missing_fields: [],
      message: '',
    },
    pat_masked: '',
    pat_configured: false,
  },
})

const form = reactive({
  qdrant: {
    url: '',
  },
  llm: {
    base_url: '',
    model: '',
    api_key: '',
  },
  ingestion: {
    chunk_size: 500,
    chunk_overlap: 50,
    enable_code_summarization: false,
    image_processor: 'none',
    image_vision_base_url: '',
    image_vision_model: '',
    image_vision_api_key: '',
  },
  chat: {
    max_messages: 20,
  },
  retrieval: {
    top_k: 3,
    max_full_docs: 2,
    max_full_doc_chars: 8000,
  },
  confluence: {
    base_url: '',
    pat: '',
  },
})

const requiresMultimodalVision = computed(() => form.ingestion.image_processor === 'multimodal')

function syncForms(data) {
  Object.assign(settings.qdrant, data.qdrant || {})
  Object.assign(settings.llm, data.llm || {})
  Object.assign(settings.ingestion, data.ingestion || {})
  Object.assign(settings.chat, data.chat || {})
  Object.assign(settings.retrieval, data.retrieval || {})
  Object.assign(settings.confluence, data.confluence || {})

  form.qdrant.url = data.qdrant?.url || ''

  form.llm.base_url = data.llm?.base_url || ''
  form.llm.model = data.llm?.model || ''
  form.llm.api_key = data.llm?.api_key || ''

  form.ingestion.chunk_size = data.ingestion?.chunk_size ?? 500
  form.ingestion.chunk_overlap = data.ingestion?.chunk_overlap ?? 50
  form.ingestion.enable_code_summarization = Boolean(data.ingestion?.enable_code_summarization)
  form.ingestion.image_processor = data.ingestion?.image_processor || 'none'
  form.ingestion.image_vision_api_key = data.ingestion?.image_vision_api_key || ''
  form.ingestion.image_vision_base_url = data.ingestion?.image_vision_base_url || ''
  form.ingestion.image_vision_model = data.ingestion?.image_vision_model || ''

  form.chat.max_messages = data.chat?.max_messages ?? 20
  form.retrieval.top_k = data.retrieval?.top_k ?? 3
  form.retrieval.max_full_docs = data.retrieval?.max_full_docs ?? 2
  form.retrieval.max_full_doc_chars = data.retrieval?.max_full_doc_chars ?? 8000

  form.confluence.base_url = data.confluence?.base_url || ''
  form.confluence.pat = data.confluence?.pat || ''
}

async function loadSettings() {
  loading.value = true
  try {
    const data = await getRuntimeSettings()
    syncForms(data)
  } finally {
    loading.value = false
  }
}

function resolveSecretValue(value) {
  return value.trim()
}

function validateBeforeSave() {
  const hasConfluenceBaseUrl = Boolean(form.confluence.base_url.trim())
  const hasConfluencePat = Boolean(form.confluence.pat.trim())

  if (hasConfluenceBaseUrl !== hasConfluencePat) {
    ElMessage.error('Confluence Base URL and PAT must be set together')
    return false
  }

  if (
    requiresMultimodalVision.value &&
    (!form.ingestion.image_vision_base_url.trim() ||
      !form.ingestion.image_vision_model.trim() ||
      !resolveSecretValue(form.ingestion.image_vision_api_key))
  ) {
    ElMessage.error('Multimodal image processing requires Vision Base URL, Vision Model, and Vision API Key')
    return false
  }

  return true
}

async function saveSettings() {
  if (!validateBeforeSave()) {
    return
  }

  saving.value = true
  try {
    const data = await updateRuntimeSettings({
      qdrant: {
        url: form.qdrant.url.trim(),
      },
      llm: {
        base_url: form.llm.base_url.trim(),
        model: form.llm.model.trim(),
        api_key: resolveSecretValue(form.llm.api_key),
      },
      ingestion: {
        chunk_size: form.ingestion.chunk_size,
        chunk_overlap: form.ingestion.chunk_overlap,
        enable_code_summarization: form.ingestion.enable_code_summarization,
        image_processor: form.ingestion.image_processor,
        image_vision_base_url: form.ingestion.image_vision_base_url.trim(),
        image_vision_model: form.ingestion.image_vision_model.trim(),
        image_vision_api_key: resolveSecretValue(form.ingestion.image_vision_api_key),
      },
      chat: {
        max_messages: form.chat.max_messages,
      },
      retrieval: {
        top_k: form.retrieval.top_k,
        max_full_docs: form.retrieval.max_full_docs,
        max_full_doc_chars: form.retrieval.max_full_doc_chars,
      },
      confluence: {
        base_url: form.confluence.base_url.trim(),
        pat: resolveSecretValue(form.confluence.pat),
      },
    })
    syncForms(data)
    ElMessage.success('System settings updated')
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings-view {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
}

.loading-panel,
.settings-shell {
  padding: 24px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.settings-shell {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.settings-stack {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.settings-status {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(248, 250, 252, 0.88);
}

.status-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--dm-text-soft);
}

.settings-section + .settings-section {
  padding-top: 28px;
  border-top: 1px solid rgba(148, 163, 184, 0.22);
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--dm-text);
}

.section-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--dm-text-soft);
}

.settings-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.full-span {
  grid-column: 1 / -1;
}

.field-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--dm-text-soft);
}

.field-hint--warning {
  color: #b45309;
}

.section-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .settings-status,
  .settings-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
