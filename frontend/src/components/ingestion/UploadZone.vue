<template>
  <div class="upload-zone-wrapper">
    <!-- Upload Area -->
    <el-upload
      ref="uploadRef"
      class="upload-dragger"
      drag
      :auto-upload="false"
      :multiple="false"
      :limit="1"
      accept=".pdf,.md,.markdown"
      :on-change="handleFileChange"
      :on-exceed="handleExceed"
      :file-list="fileList"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        Drop file here, or <em>click to upload</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">Supports PDF and Markdown files</div>
      </template>
    </el-upload>

    <!-- Metadata Form -->
    <el-form
      ref="formRef"
      :model="form"
      label-position="top"
      class="upload-form"
      size="default"
    >
      <el-form-item label="Document Title">
        <el-input
          v-model="form.title"
          placeholder="Leave blank to use filename"
          clearable
        />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="Doc Type">
              <el-select v-model="form.doc_type" placeholder="Select type" style="width: 100%">
              <el-option label="All" value="all" />
              <el-option label="Manual" value="manual" />
              <el-option label="FAQ" value="faq" />
              <el-option label="Policy" value="policy" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Service">
            <el-input
              v-model="form.service"
              placeholder="e.g. all or service1,service2"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="Department">
        <el-input
          v-model="form.department"
          placeholder="e.g. all or dept1,dept2"
          clearable
        />
      </el-form-item>

      <el-form-item label="Source URL (optional)">
        <el-input
          v-model="form.url"
          placeholder="https://..."
          clearable
        />
      </el-form-item>

      <el-form-item>
        <el-checkbox v-model="form.strict_mode">
          Strict Chunking Validation
        </el-checkbox>
        <div style="font-size: 12px; color: #909399; line-height: 1.2; margin-top: 4px;">
          If enabled, extremely long text blocks or code snippets that exceed limits will fail the ingestion to guarantee semantic integrity. If disabled, they will be forcefully chunked.
        </div>
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile"
          style="width: 100%"
          @click="handleUpload"
        >
          {{ uploading ? 'Uploading...' : 'Upload' }}
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { uploadDocument } from '@/api/ingest'

const props = defineProps({
  kbId: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['uploaded'])

const uploadRef = ref(null)
const formRef = ref(null)
const uploading = ref(false)
const selectedFile = ref(null)
const fileList = ref([])

const form = reactive({
  title: '',
  doc_type: 'all',
  service: 'all',
  department: 'all',
  url: '',
  strict_mode: true,
})

function handleFileChange(file) {
  selectedFile.value = file.raw
  // Pre-fill title with filename (without extension) if empty
  if (!form.title) {
    form.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

function handleExceed() {
  ElMessage.warning('Only one file at a time. Please remove the current file first.')
}

async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('Please select a file first.')
    return
  }

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (form.title) formData.append('title', form.title)
  if (form.url) formData.append('url', form.url)
  if (form.doc_type) formData.append('doc_type', form.doc_type)
  if (form.service) formData.append('service', form.service)
  if (form.department) formData.append('department', form.department)
  formData.append('strict_mode', form.strict_mode)

  uploading.value = true
  try {
    const result = await uploadDocument(props.kbId, formData)
    ElMessage.success('Document uploaded and ingestion queued successfully.')
    // Reset form and file list
    resetForm()
    emit('uploaded', result)
  } catch (err) {
    // Error already handled by http interceptor
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  selectedFile.value = null
  fileList.value = []
  form.title = ''
  form.doc_type = 'all'
  form.service = 'all'
  form.department = 'all'
  form.url = ''
  form.strict_mode = true
  uploadRef.value?.clearFiles()
}
</script>

<style scoped>
.upload-zone-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-dragger {
  width: 100%;
}

.upload-dragger :deep(.el-upload),
.upload-dragger :deep(.el-upload-dragger) {
  width: 100%;
}

.upload-form {
  margin-top: 4px;
}
</style>
