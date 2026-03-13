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
        拖拽文件到此处，或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">支持 PDF 或 Markdown 文件</div>
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
      <el-form-item label="文档标题">
        <el-input
          v-model="form.title"
          placeholder="留空则使用文件名"
          clearable
        />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="文档类型 (doc_type)">
            <el-select v-model="form.doc_type" placeholder="选择类型" style="width: 100%">
              <el-option label="全部 (all)" value="all" />
              <el-option label="手册 (manual)" value="manual" />
              <el-option label="FAQ" value="faq" />
              <el-option label="政策 (policy)" value="policy" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="适用服务 (service)">
            <el-input
              v-model="form.service"
              placeholder="例如: all 或 service1,service2"
              clearable
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="适用部门 (department)">
        <el-input
          v-model="form.department"
          placeholder="例如: all 或 dept1,dept2"
          clearable
        />
      </el-form-item>

      <el-form-item label="来源 URL（选填）">
        <el-input
          v-model="form.url"
          placeholder="https://..."
          clearable
        />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile"
          style="width: 100%"
          @click="handleUpload"
        >
          {{ uploading ? '上传中...' : '开始上传' }}
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
})

function handleFileChange(file) {
  selectedFile.value = file.raw
  // Pre-fill title with filename (without extension) if empty
  if (!form.title) {
    form.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

function handleExceed() {
  ElMessage.warning('每次只能上传一个文件，请先移除已选文件')
}

async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择一个文件')
    return
  }

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (form.title) formData.append('title', form.title)
  if (form.url) formData.append('url', form.url)
  if (form.doc_type) formData.append('doc_type', form.doc_type)
  if (form.service) formData.append('service', form.service)
  if (form.department) formData.append('department', form.department)

  uploading.value = true
  try {
    const result = await uploadDocument(formData)
    ElMessage.success(`上传成功！共切分 ${result.chunk_count} 个 Chunk`)
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
