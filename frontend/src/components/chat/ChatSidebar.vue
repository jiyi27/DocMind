<template>
  <aside class="chat-sidebar">
    <div
      class="chat-list scrollbar-hidden"
      :class="{ loading: loading }"
      ref="listRef"
      @scroll.passive="onScroll"
    >
      <button
        class="chat-item chat-create-item"
        type="button"
        aria-label="Create conversation"
        title="Create conversation"
        @click="$emit('create')"
      >
        <el-icon class="chat-create-icon"><EditPen /></el-icon>
        <span class="chat-title">New chat</span>
      </button>
      <div
        v-for="item in items"
        :key="item.id"
        class="chat-item"
        :class="{ active: item.id === activeId }"
        role="button"
        tabindex="0"
        @click="$emit('select', item.id)"
        @keydown.enter="$emit('select', item.id)"
        @keydown.space.prevent="$emit('select', item.id)"
      >
        <span class="chat-title">{{ item.title }}</span>
        <button
          class="chat-delete-btn"
          type="button"
          aria-label="Delete chat"
          title="Delete chat"
          @click.stop="$emit('delete', item)"
        >
          <el-icon><Delete /></el-icon>
        </button>
      </div>
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
import { Delete, EditPen } from '@element-plus/icons-vue'

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

const emit = defineEmits(['select', 'create', 'delete', 'load-more'])

const listRef = ref(null)

function onScroll() {
  const el = listRef.value
  if (!el || props.loadingMore || !props.hasMore) return
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 60) {
    emit('load-more')
  }
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
}

.chat-list {
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  overscroll-behavior: contain;
}

.chat-create-icon {
  font-size: 16px;
  color: var(--dm-text-muted);
}

.chat-list.loading {
  opacity: 0.7;
  pointer-events: none;
}

.chat-item {
  border: none;
  background: transparent;
  border-radius: 12px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  position: relative;
  transition: background-color 0.18s ease, color 0.18s ease;
}

.chat-item.chat-create-item {
  min-height: 40px;
  padding: 10px 12px;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
}

.chat-item:hover {
  background: rgba(255, 255, 255, 0.62);
}

.chat-item.active {
  background: rgba(255, 255, 255, 0.72);
}

.chat-item.active::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
}

.chat-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--dm-text);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-delete-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--dm-text-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.chat-item:hover .chat-delete-btn,
.chat-item:focus-within .chat-delete-btn,
.chat-item.active .chat-delete-btn {
  opacity: 1;
  pointer-events: auto;
}

.chat-delete-btn:hover {
  background: rgba(248, 113, 113, 0.12);
  color: #dc2626;
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
  }
}
</style>
