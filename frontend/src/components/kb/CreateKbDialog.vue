<template>
  <el-dialog
    v-model="visible"
    title="Create Knowledge Base"
    width="560px"
    :close-on-click-modal="false"
    class="create-kb-dialog"
    @closed="resetForm"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="Slug" prop="name">
        <el-input
          v-model="form.name"
          placeholder="e.g. tech-docs or hr_manual"
          clearable
        />
        <div class="form-hint">Only letters, numbers, hyphens, and underscores allowed</div>
      </el-form-item>

      <el-form-item label="Display Name" prop="display_name">
        <el-input
          v-model="form.display_name"
          placeholder="e.g. Tech Docs"
          clearable
        />
      </el-form-item>

      <el-form-item label="Description" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="Optional. Briefly describe the purpose of this knowledge base."
        />
      </el-form-item>

      <div class="section-title">Embedding Settings</div>

      <el-alert
        v-if="embeddingOptions.creation_hint"
        :title="embeddingOptions.creation_hint"
        type="warning"
        :closable="false"
        show-icon
        class="section-alert"
      />

      <el-form-item label="Provider" prop="embedding.provider">
        <el-select
          v-model="form.embedding.provider"
          placeholder="Select embedding provider"
          class="full-width"
          @change="handleProviderChange"
        >
          <el-option
            v-for="provider in embeddingProviders"
            :key="provider.value"
            :label="provider.label"
            :value="provider.value"
          />
        </el-select>
        <div v-if="selectedProvider?.description" class="form-hint">
          {{ selectedProvider.description }}
        </div>
      </el-form-item>

      <el-form-item
        v-for="field in selectedFields"
        :key="field.name"
        :label="field.label"
        :prop="`embedding.${field.name}`"
        :rules="buildEmbeddingFieldRules(field)"
      >
        <el-input
          v-model="form.embedding[field.name]"
          :type="field.type === 'password' ? 'password' : 'text'"
          :placeholder="field.placeholder || ''"
          :show-password="field.type === 'password'"
          clearable
        />
        <div class="form-hint">
          {{ field.help }}
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">Cancel</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        Create
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { getKbEmbeddingOptions } from '@/api/kb'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['success'])

const visible = ref(false)
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  name: '',
  display_name: '',
  description: '',
  embedding: {
    provider: 'openai_compatible',
    model: '',
    base_url: '',
    api_key: '',
  },
})

const embeddingOptions = reactive({
  creation_hint: '',
  default_provider: 'openai_compatible',
  providers: [],
})

const embeddingLoading = ref(false)

const rules = {
  name: [
    { required: true, message: 'Please enter a slug', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_-]+$/,
      message: 'Only letters, numbers, hyphens, and underscores allowed',
      trigger: 'blur',
    },
    { min: 2, max: 64, message: 'Length must be between 2 and 64 characters', trigger: 'blur' },
  ],
  display_name: [
    { required: true, message: 'Please enter a display name', trigger: 'blur' },
    { min: 1, max: 128, message: 'Length must be between 1 and 128 characters', trigger: 'blur' },
  ],
  'embedding.provider': [
    { required: true, message: 'Please select an embedding provider', trigger: 'change' },
  ],
}

const embeddingProviders = computed(() => embeddingOptions.providers || [])

const selectedProvider = computed(() => {
  return embeddingProviders.value.find((provider) => provider.value === form.embedding.provider) || null
})

const selectedFields = computed(() => selectedProvider.value?.fields || [])

function buildEmbeddingFieldRules(field) {
  const rulesForField = []
  if (field.required) {
    rulesForField.push({
      required: true,
      message: `Please enter ${field.label.toLowerCase()}`,
      trigger: 'blur',
    })
  }
  return rulesForField
}

async function loadEmbeddingOptions() {
  if (embeddingProviders.value.length > 0 || embeddingLoading.value) {
    return
  }

  embeddingLoading.value = true
  try {
    const data = await getKbEmbeddingOptions()
    embeddingOptions.creation_hint = data.creation_hint || ''
    embeddingOptions.default_provider = data.default_provider || 'openai_compatible'
    embeddingOptions.providers = Array.isArray(data.providers) ? data.providers : []
    form.embedding.provider = embeddingOptions.default_provider
  } catch (error) {
    ElMessage.error('Failed to load embedding options')
  } finally {
    embeddingLoading.value = false
  }
}

function open() {
  loadEmbeddingOptions()
  visible.value = true
}

function resetForm() {
  form.name = ''
  form.display_name = ''
  form.description = ''
  form.embedding.provider = embeddingOptions.default_provider || 'openai_compatible'
  form.embedding.model = ''
  form.embedding.base_url = ''
  form.embedding.api_key = ''
  formRef.value?.clearValidate()
}

function handleProviderChange() {
  form.embedding.model = ''
  form.embedding.base_url = ''
  form.embedding.api_key = ''
  formRef.value?.clearValidate([
    'embedding.provider',
    'embedding.model',
    'embedding.base_url',
    'embedding.api_key',
  ])
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const payload = {
      name: form.name,
      display_name: form.display_name,
      description: form.description,
      embedding: {
        provider: form.embedding.provider,
      },
    }

    selectedFields.value.forEach((field) => {
      payload.embedding[field.name] = form.embedding[field.name]?.trim?.() || ''
    })

    emit('success', payload)
    visible.value = false
  } finally {
    loading.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.create-kb-dialog :deep(.el-dialog) {
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid var(--dm-border);
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.14);
}

.create-kb-dialog :deep(.el-dialog__header) {
  margin: 0;
  padding: 24px 28px 16px;
  border-bottom: 1px solid var(--dm-border);
}

.create-kb-dialog :deep(.el-dialog__title) {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--dm-text);
}

.create-kb-dialog :deep(.el-dialog__headerbtn) {
  top: 20px;
  right: 22px;
}

.create-kb-dialog :deep(.el-dialog__body) {
  padding: 22px 28px 18px;
}

.create-kb-dialog :deep(.el-dialog__footer) {
  padding: 18px 28px 24px;
  border-top: 1px solid rgba(226, 232, 240, 0.78);
}

.create-kb-dialog :deep(.el-form-item) {
  margin-bottom: 22px;
}

.create-kb-dialog :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 700;
  color: var(--dm-text);
}

.create-kb-dialog :deep(.el-input__wrapper),
.create-kb-dialog :deep(.el-textarea__inner),
.create-kb-dialog :deep(.el-select__wrapper) {
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.92);
}

.create-kb-dialog :deep(.el-input__wrapper.is-focus),
.create-kb-dialog :deep(.el-textarea__inner:focus),
.create-kb-dialog :deep(.el-select__wrapper.is-focused) {
  box-shadow:
    inset 0 0 0 1px rgba(37, 99, 235, 0.45),
    0 0 0 4px rgba(37, 99, 235, 0.08);
}

.create-kb-dialog :deep(.el-alert) {
  border-radius: 18px;
}

.create-kb-dialog :deep(.el-button) {
  border-radius: 14px;
}

.create-kb-dialog :deep(.el-button--primary) {
  padding-inline: 20px;
}

.section-title {
  position: relative;
  margin: 10px 0 16px;
  padding-top: 6px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--dm-text-soft);
}

.section-title::after {
  content: '';
  display: block;
  width: 100%;
  height: 1px;
  margin-top: 10px;
  background: linear-gradient(90deg, rgba(148, 163, 184, 0.34), rgba(148, 163, 184, 0.08));
}

.section-alert {
  margin-bottom: 18px;
}

.full-width {
  width: 100%;
}

.form-hint {
  font-size: 12px;
  line-height: 1.5;
  color: var(--dm-text-soft);
  margin-top: 6px;
}
</style>
