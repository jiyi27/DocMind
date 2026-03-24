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

      <el-form-item label="Source URL (optional)">
        <el-input
          v-model="form.url"
          placeholder="https://..."
          clearable
        />
      </el-form-item>

      <el-form-item label="Retrieval Mode">
        <el-radio-group v-model="form.retrieval_mode" style="width: 100%">
          <el-radio value="chunk">Fragment Mode</el-radio>
          <el-radio value="full_doc">Full Article Mode</el-radio>
        </el-radio-group>
        <div style="font-size: 12px; color: #909399; line-height: 1.2; margin-top: 6px;">
          <template v-if="form.retrieval_mode === 'chunk'">
            Retrieve individual matched fragments. Best for FAQs, manuals, and reference docs.
          </template>
          <template v-else>
            When any fragment matches, the entire article is fed to the LLM. Best for technical articles and design documents that require holistic understanding. Document size is limited.
          </template>
        </div>
      </el-form-item>

      <el-collapse accordion style="border: none; margin-bottom: 18px;">
        <el-collapse-item name="1">
          <template #title>
            <span style="font-size: 13px; color: #606266; font-weight: normal;">Advanced Chunking Settings</span>
          </template>
          <div style="padding: 10px 0 0 0;">
            <el-form-item label="Target Chunk Size" style="margin-bottom: 0;">
              <el-input-number v-model="form.chunk_size" :min="100" :max="8000" controls-position="right" style="width: 100%" />
              <div style="font-size: 11px; color: #909399; margin-top: 4px; line-height: 1.2;">
                Ideal token size for a combined chunk.
              </div>
            </el-form-item>
            <el-form-item label="Chunk Overlap" style="margin: 12px 0 0 0;">
              <el-input-number v-model="form.chunk_overlap" :min="0" :max="4000" controls-position="right" style="width: 100%" />
              <div style="font-size: 11px; color: #909399; margin-top: 4px; line-height: 1.2;">
                Repeats a small amount of trailing context in the next chunk.
              </div>
            </el-form-item>
          </div>
        </el-collapse-item>
      </el-collapse>

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
  url: '',
  retrieval_mode: 'chunk',
  chunk_size: 500,
  chunk_overlap: 100,
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
  formData.append('retrieval_mode', form.retrieval_mode)
  formData.append('chunk_size', form.chunk_size)
  formData.append('chunk_overlap', form.chunk_overlap)

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
  form.url = ''
  form.retrieval_mode = 'chunk'
  form.chunk_size = 500
  form.chunk_overlap = 100
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
