<template>
  <el-card class="kb-card" :class="{ 'kb-card--locked': !canAccess }" shadow="never" @click="handleClick">
    <div class="kb-card-header">
      <div class="kb-icon-wrap">
        <el-icon class="kb-icon"><Collection /></el-icon>
      </div>

      <div class="kb-card-tools">
        <el-tooltip v-if="!canAccess" content="You don't have access to this knowledge base" placement="top">
          <el-icon class="lock-icon"><Lock /></el-icon>
        </el-tooltip>
        <el-dropdown
          v-if="canManage"
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
                Delete
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="kb-card-body">
      <h3 class="kb-display-name">{{ kb.display_name }}</h3>
      <p class="kb-name">{{ kb.name }}</p>
      <p class="kb-description">{{ kb.description || 'No description yet.' }}</p>

      <div v-if="kb.embedding_provider || kb.embedding_model" class="kb-meta">
        <el-tag size="small" type="info" effect="plain">
          {{ kb.embedding_provider || 'embedding' }}
        </el-tag>
        <el-tag v-if="kb.embedding_model" size="small" effect="plain">
          {{ kb.embedding_model }}
        </el-tag>
      </div>
    </div>

    <div class="kb-card-footer">
      <span class="footer-item">
        <el-icon><Calendar /></el-icon>
        {{ formatDate(kb.created_at, { month: 'short', day: 'numeric' }) }}
      </span>
      <span class="footer-item footer-item--link">
        {{ canAccess ? 'Open workspace' : 'Restricted' }}
      </span>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Calendar, Collection, Delete, Lock, MoreFilled } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/format/date'

const props = defineProps({
  kb: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['delete'])

const router = useRouter()
const authStore = useAuthStore()

const canAccess = computed(() => authStore.canAccessKb(props.kb.id))
const canManage = computed(() => authStore.canManageKb(props.kb.id))

function handleClick() {
  if (!canAccess.value) {
    ElMessageBox.alert(
      'You do not have permission to access this knowledge base.',
      'Access Denied',
      {
        confirmButtonText: 'OK',
        type: 'warning',
        icon: Lock,
      }
    )
    return
  }
  router.push(`/kb/${props.kb.id}`)
}

async function handleCommand(command) {
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `Are you sure you want to delete "${props.kb.display_name}"? This will permanently remove all related documents and vector data.`,
        'Confirm Deletion',
        {
          confirmButtonText: 'Delete',
          cancelButtonText: 'Cancel',
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

</script>

<style scoped>
.kb-card {
  height: 100%;
  cursor: pointer;
  border-radius: 24px;
  border: 1px solid var(--dm-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(248, 250, 252, 0.92) 100%);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.kb-card:hover {
  transform: translateY(-2px);
  border-color: rgba(37, 99, 235, 0.22);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
}

.kb-card--locked {
  cursor: not-allowed;
  opacity: 0.72;
}

.kb-card--locked:hover {
  transform: none;
  box-shadow: none;
}

.kb-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 18px;
}

.kb-card-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-icon-wrap {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.kb-icon {
  font-size: 24px;
  color: var(--dm-primary);
}

.lock-icon {
  font-size: 16px;
  color: var(--dm-text-soft);
}

.more-btn {
  color: var(--dm-text-soft);
}

.kb-card-body {
  margin-bottom: 18px;
}

.kb-display-name {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: var(--dm-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kb-name {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--dm-text-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

.kb-description {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--dm-text-muted);
  min-height: 44px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.kb-card-footer {
  padding-top: 14px;
  border-top: 1px solid var(--dm-border-strong);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.footer-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--dm-text-soft);
}

.footer-item--link {
  color: var(--dm-primary);
  font-weight: 700;
}

:deep(.danger-item) {
  color: #f56c6c !important;
}
</style>
