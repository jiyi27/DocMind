<template>
  <div class="settings-view">
    <div v-if="loading" class="loading-panel">
      <el-skeleton :rows="6" animated />
    </div>

    <section v-else class="settings-shell">
      <div class="settings-status">
        <span class="status-item">
          <span class="status-label">LLM Key</span>
          <el-tag :type="settings.llm.api_key_configured ? 'success' : 'warning'" effect="plain">
            {{ settings.llm.api_key_configured ? 'Configured' : 'Incomplete' }}
          </el-tag>
        </span>
        <span class="status-item">
          <span class="status-label">Chat History</span>
          <strong>{{ chatForm.max_messages }}</strong>
        </span>
        <span class="status-item">
          <span class="status-label">Retrieval Top K</span>
          <strong>{{ retrievalForm.top_k }}</strong>
        </span>
      </div>

      <section class="settings-section">
        <div class="section-head">
          <div>
            <h3 class="section-title">LLM Settings</h3>
            <p class="section-desc">Update the shared chat model connection used by the backend.</p>
          </div>
        </div>

        <el-form class="settings-form-grid" label-position="top" @submit.prevent>
          <el-form-item label="Base URL">
            <el-input v-model="llmForm.base_url" placeholder="https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="Model">
            <el-input v-model="llmForm.model" placeholder="gpt-4.1-mini" />
          </el-form-item>
          <el-form-item class="full-span" label="API Key">
            <el-input
              v-model="llmForm.api_key"
              type="password"
              show-password
              placeholder="Leave blank to keep the current key"
            />
            <div class="field-hint">Current key: {{ settings.llm.api_key_masked || 'Not configured' }}</div>
          </el-form-item>
        </el-form>

        <div class="section-actions">
          <el-button type="primary" :loading="savingLlm" @click="saveLlmSettings">
            Save LLM Settings
          </el-button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-head">
          <div>
            <h3 class="section-title">Chat Settings</h3>
            <p class="section-desc">Cap how many prior messages are kept in conversation history.</p>
          </div>
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="Max Messages">
            <el-input-number v-model="chatForm.max_messages" :min="0" :max="200" />
          </el-form-item>
        </el-form>

        <div class="section-actions">
          <el-button type="primary" :loading="savingChat" @click="saveChatSettings">
            Save Chat Settings
          </el-button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-head">
          <div>
            <h3 class="section-title">Retrieval Settings</h3>
            <p class="section-desc">Adjust how many vector hits the retrieval layer uses per request.</p>
          </div>
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="Top K">
            <el-input-number v-model="retrievalForm.top_k" :min="1" :max="100" />
          </el-form-item>
        </el-form>

        <div class="section-actions">
          <el-button type="primary" :loading="savingRetrieval" @click="saveRetrievalSettings">
            Save Retrieval Settings
          </el-button>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getRuntimeSettings,
  updateChatSettings,
  updateLlmSettings,
  updateRetrievalSettings,
} from '@/api/admin'

const loading = ref(true)
const savingLlm = ref(false)
const savingChat = ref(false)
const savingRetrieval = ref(false)

const settings = reactive({
  llm: {
    base_url: '',
    model: '',
    api_key_masked: '',
    api_key_configured: false,
  },
  chat: {
    max_messages: 20,
  },
  retrieval: {
    top_k: 3,
  },
})

const llmForm = reactive({
  base_url: '',
  model: '',
  api_key: '',
})

const chatForm = reactive({
  max_messages: 20,
})

const retrievalForm = reactive({
  top_k: 3,
})

function syncForms(data) {
  settings.llm = { ...data.llm }
  settings.chat = { ...data.chat }
  settings.retrieval = { ...data.retrieval }

  llmForm.base_url = data.llm.base_url || ''
  llmForm.model = data.llm.model || ''
  llmForm.api_key = ''
  chatForm.max_messages = data.chat.max_messages
  retrievalForm.top_k = data.retrieval.top_k
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

async function saveLlmSettings() {
  savingLlm.value = true
  try {
    const payload = {
      base_url: llmForm.base_url.trim(),
      model: llmForm.model.trim(),
      api_key: llmForm.api_key.trim() || null,
    }
    const data = await updateLlmSettings(payload)
    syncForms(data)
    ElMessage.success('LLM settings updated')
  } finally {
    savingLlm.value = false
  }
}

async function saveChatSettings() {
  savingChat.value = true
  try {
    const data = await updateChatSettings({ max_messages: chatForm.max_messages })
    syncForms(data)
    ElMessage.success('Chat settings updated')
  } finally {
    savingChat.value = false
  }
}

async function saveRetrievalSettings() {
  savingRetrieval.value = true
  try {
    const data = await updateRetrievalSettings({ top_k: retrievalForm.top_k })
    syncForms(data)
    ElMessage.success('Retrieval settings updated')
  } finally {
    savingRetrieval.value = false
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

.settings-status {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 800;
  color: var(--dm-text);
}

.section-desc {
  margin: 0;
  font-size: 13px;
  color: var(--dm-text-soft);
}

.settings-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
}

.full-span {
  grid-column: 1 / -1;
}

.field-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--dm-text-soft);
}

.section-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

@media (max-width: 720px) {
  .settings-view {
    max-width: 100%;
  }

  .loading-panel,
  .settings-shell {
    padding: 18px;
    border-radius: 22px;
  }

  .settings-status {
    grid-template-columns: 1fr;
  }

  .settings-form-grid {
    grid-template-columns: 1fr;
  }

  .section-actions {
    justify-content: flex-start;
  }
}
</style>
