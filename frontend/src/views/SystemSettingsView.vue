<template>
  <div class="settings-view">
    <section class="settings-toolbar">
      <div>
        <div class="toolbar-title-row">
          <h1 class="page-title">System Settings</h1>
          <el-tag type="danger" effect="plain" round>Super Admin</el-tag>
        </div>
        <p class="page-desc">Runtime LLM, chat, and retrieval settings apply immediately after saving.</p>
      </div>
    </section>

    <div v-if="loading" class="loading-panel">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else class="settings-grid">
      <section class="settings-card">
        <div class="card-head">
          <div>
            <h2 class="card-title">LLM</h2>
            <p class="card-desc">Update the shared chat model connection used by the backend.</p>
          </div>
          <el-tag :type="settings.llm.api_key_configured ? 'success' : 'warning'" effect="plain">
            {{ settings.llm.api_key_configured ? 'Configured' : 'Incomplete' }}
          </el-tag>
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="Base URL">
            <el-input v-model="llmForm.base_url" placeholder="https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="Model">
            <el-input v-model="llmForm.model" placeholder="gpt-4.1-mini" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input
              v-model="llmForm.api_key"
              type="password"
              show-password
              placeholder="Leave blank to keep the current key"
            />
            <div class="field-hint">Current key: {{ settings.llm.api_key_masked || 'Not configured' }}</div>
          </el-form-item>
          <el-button type="primary" :loading="savingLlm" @click="saveLlmSettings">
            Save LLM Settings
          </el-button>
        </el-form>
      </section>

      <section class="settings-card">
        <div class="card-head">
          <div>
            <h2 class="card-title">Chat</h2>
            <p class="card-desc">Cap how many prior messages are kept in conversation history.</p>
          </div>
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="Max Messages">
            <el-input-number v-model="chatForm.max_messages" :min="0" :max="200" />
          </el-form-item>
          <el-button type="primary" :loading="savingChat" @click="saveChatSettings">
            Save Chat Settings
          </el-button>
        </el-form>
      </section>

      <section class="settings-card">
        <div class="card-head">
          <div>
            <h2 class="card-title">Retrieval</h2>
            <p class="card-desc">Adjust how many vector hits the retrieval layer uses per request.</p>
          </div>
        </div>

        <el-form label-position="top" @submit.prevent>
          <el-form-item label="Top K">
            <el-input-number v-model="retrievalForm.top_k" :min="1" :max="100" />
          </el-form-item>
          <el-button type="primary" :loading="savingRetrieval" @click="saveRetrievalSettings">
            Save Retrieval Settings
          </el-button>
        </el-form>
      </section>
    </div>
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

.settings-toolbar {
  margin-bottom: 20px;
  padding: 4px 2px;
}

.toolbar-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 30px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dm-text);
}

.page-desc {
  margin: 10px 0 0;
  font-size: 14px;
  color: var(--dm-text-soft);
}

.loading-panel,
.settings-card {
  padding: 24px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.settings-card:last-child {
  grid-column: 1 / -1;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.card-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 800;
  color: var(--dm-text);
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: var(--dm-text-soft);
}

.field-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--dm-text-soft);
}

@media (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .settings-card:last-child {
    grid-column: auto;
  }
}
</style>
