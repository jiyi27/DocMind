<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <el-button type="primary" :icon="Plus" class="new-chat-btn" @click="$emit('create')">
        New Chat
      </el-button>
    </div>
    <div class="chat-list" :class="{ loading: loading }">
      <button
        v-for="item in items"
        :key="item.id"
        class="chat-item"
        :class="{ active: item.id === activeId }"
        @click="$emit('select', item.id)"
      >
        <span class="chat-title">{{ item.title }}</span>
        <span v-if="item.last_message_preview" class="chat-preview">{{ item.last_message_preview }}</span>
        <span class="chat-meta">
          <span>{{ item.id }}</span>
          <span v-if="item.updated_at" class="chat-time">{{ formatTime(item.updated_at) }}</span>
        </span>
      </button>
      <div v-if="!loading && items.length === 0" class="chat-empty">
        No conversations yet.
      </div>
    </div>
  </aside>
</template>

<script setup>
import { Plus } from '@element-plus/icons-vue'

defineProps({
  items: {
    type: Array,
    default: () => []
  },
  activeId: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select', 'create'])

function formatTime(raw) {
  if (!raw) {
    return ''
  }
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) {
    return raw
  }
  return date.toLocaleString()
}
</script>

<style scoped>
.chat-sidebar {
  width: 280px;
  background-color: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
}

.new-chat-btn {
  width: 100%;
  font-weight: 600;
}

.chat-list {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
}

.chat-list.loading {
  opacity: 0.7;
  pointer-events: none;
}

.chat-item {
  border: 1px solid transparent;
  background-color: #ffffff;
  border-radius: 12px;
  padding: 12px 14px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
}

.chat-item:hover {
  border-color: #cbd5f5;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.chat-item.active {
  border-color: #409eff;
  background-color: rgba(64, 158, 255, 0.08);
}

.chat-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.chat-preview {
  font-size: 12px;
  color: #4b5563;
  line-height: 1.4;
}

.chat-meta {
  font-size: 12px;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chat-time {
  color: #94a3b8;
  white-space: nowrap;
}

.chat-empty {
  font-size: 13px;
  color: #6b7280;
  text-align: center;
  padding: 24px 12px;
}

@media (max-width: 960px) {
  .chat-sidebar {
    width: 100%;
  }
}
</style>
