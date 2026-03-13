<template>
  <el-dialog
    v-model="visible"
    title="Create Knowledge Base"
    width="480px"
    :close-on-click-modal="false"
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
import { ref, reactive } from 'vue'

const emit = defineEmits(['success'])

const visible = ref(false)
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  name: '',
  display_name: '',
  description: '',
})

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
}

function open() {
  visible.value = true
}

function resetForm() {
  form.name = ''
  form.display_name = ''
  form.description = ''
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    emit('success', { ...form })
    visible.value = false
  } finally {
    loading.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
