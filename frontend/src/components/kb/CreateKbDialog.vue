<template>
  <el-dialog
    v-model="visible"
    title="创建知识库"
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
      <el-form-item label="知识库标识 (Slug)" prop="name">
        <el-input
          v-model="form.name"
          placeholder="例如: tech-docs 或 hr_manual"
          clearable
        />
        <div class="form-hint">只允许字母、数字、横杠和下划线</div>
      </el-form-item>

      <el-form-item label="显示名称" prop="display_name">
        <el-input
          v-model="form.display_name"
          placeholder="例如: 技术文档库"
          clearable
        />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="可选，简要描述该知识库的用途"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        创建
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
    { required: true, message: '请输入知识库标识', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_-]+$/,
      message: '只允许字母、数字、横杠和下划线',
      trigger: 'blur',
    },
    { min: 2, max: 64, message: '长度在 2 到 64 个字符', trigger: 'blur' },
  ],
  display_name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' },
    { min: 1, max: 128, message: '长度在 1 到 128 个字符', trigger: 'blur' },
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
