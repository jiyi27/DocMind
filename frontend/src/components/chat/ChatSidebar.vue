<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <div class="sidebar-copy">
        <span class="sidebar-eyebrow">Conversations</span>
        <h2 class="sidebar-title">Recent chats</h2>
      </div>
      <el-button type="primary" :icon="Plus" class="new-chat-btn" @click="$emit('create')">
        New Chat
      </el-button>
    </div>

    <div
      class="chat-list scrollbar-hidden"
      :class="{ loading: loading }"
      ref="listRef"
      @scroll.passive="onScroll"
    >
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
          <span v-if="item.updated_at" class="chat-time">{{ formatTime(item.updated_at) }}</span>
        </span>
      </button>
      <div v-if="!loading && items.length === 0" class="chat-empty">
        No conversations yet. Start one from the button above.
      </div>
      <div v-if="loadingMore" class="chat-loading-more">Loading...</div>
      <div v-else-if="!hasMore && items.length > 0" class="chat-no-more">No more conversations</div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  activeId: {
    type: String,
    default: '',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  loadingMore: {
    type: Boolean,
    default: false,
  },
  hasMore: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['select', 'create', 'load-more'])

const listRef = ref(null)

function onScroll() {
  const el = listRef.value
  if (!el || props.loadingMore || !props.hasMore) return
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 60) {
    emit('load-more')
  }
}

function formatTime(raw) {
  if (!raw) return ''
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  return date.toLocaleString()
}
</script>

<style scoped>
.chat-sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.94) 0%, rgba(241, 245, 249, 0.92) 100%);
  border-right: 1px solid var(--dm-border-strong);
}

.sidebar-header {
  padding: 24px 20px 18px;
  border-bottom: 1px solid var(--dm-border-strong);
}

.sidebar-copy {
  margin-bottom: 14px;
}

.sidebar-eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dm-text-soft);
}

.sidebar-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--dm-text);
}

.new-chat-btn {
  width: 100%;
}

.chat-list {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  overscroll-behavior: contain;
}

.chat-list.loading {
  opacity: 0.7;
  pointer-events: none;
}

.chat-item {
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.86);
  border-radius: 18px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.chat-item:hover {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.16);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.chat-item.active {
  border-color: rgba(37, 99, 235, 0.24);
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.98) 0%, rgba(248, 250, 252, 0.94) 100%);
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.1);
}

.chat-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--dm-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-preview {
  font-size: 12px;
  color: var(--dm-text-muted);
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-meta {
  font-size: 12px;
  color: var(--dm-text-soft);
}

.chat-time {
  color: var(--dm-text-soft);
}

.chat-empty,
.chat-loading-more,
.chat-no-more {
  padding: 18px 12px;
  font-size: 12px;
  text-align: center;
  color: var(--dm-text-soft);
}

@media (max-width: 960px) {
  .chat-sidebar {
    width: 100%;
    max-height: 38vh;
    min-height: 240px;
    border-right: none;
    border-bottom: 1px solid var(--dm-border-strong);
  }
}
</style>
