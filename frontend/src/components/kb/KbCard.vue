<template>
  <el-card class="kb-card" shadow="hover" @click="handleClick">
    <div class="kb-card-header">
      <div class="kb-icon-wrap">
        <el-icon class="kb-icon"><Collection /></el-icon>
      </div>
      <el-dropdown
        v-if="isSuperAdmin"
        trigger="click"
        @command="handleCommand"
        @click.stop
      >
        <el-button
          class="more-btn"
          :icon="MoreFilled"
          circle
          text
          size="small"
          @click.stop
        />
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="delete" class="danger-item">
              <el-icon><Delete /></el-icon>
              删除知识库
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div class="kb-card-body">
      <h3 class="kb-display-name">{{ kb.display_name }}</h3>
      <p class="kb-name">{{ kb.name }}</p>
      <p class="kb-description">{{ kb.description || '暂无描述' }}</p>
    </div>

    <div class="kb-card-footer">
      <span class="kb-date">
        <el-icon><Calendar /></el-icon>
        {{ formatDate(kb.created_at) }}
      </span>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Collection, MoreFilled, Delete, Calendar } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const props = defineProps({
  kb: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['delete'])

const router = useRouter()
const authStore = useAuthStore()

const isSuperAdmin = computed(() => authStore.isSuperAdmin)

function handleClick() {
  router.push(`/kb/${props.kb.id}`)
}

async function handleCommand(command) {
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除知识库「${props.kb.display_name}」吗？此操作将同时删除所有相关文档和向量数据，且不可恢复。`,
        '删除确认',
        {
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
        }
      )
      emit('delete', props.kb.id)
    } catch {
      // User cancelled
    }
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
</script>

<style scoped>
.kb-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border-radius: 12px;
  height: 100%;
}

.kb-card:hover {
  transform: translateY(-4px);
}

.kb-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.kb-icon-wrap {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #409eff22, #409eff44);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kb-icon {
  font-size: 24px;
  color: #409eff;
}

.more-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.kb-card:hover .more-btn {
  opacity: 1;
}

.kb-card-body {
  margin-bottom: 16px;
}

.kb-display-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kb-name {
  font-size: 12px;
  color: #909399;
  margin: 0 0 10px 0;
  font-family: monospace;
}

.kb-description {
  font-size: 13px;
  color: #606266;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
  min-height: 39px;
}

.kb-card-footer {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}

.kb-date {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

:deep(.danger-item) {
  color: #f56c6c !important;
}
</style>
