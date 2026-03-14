<template>
  <section class="chat-main">
    <div class="chat-main-card">
      <h2 class="chat-main-title">Conversation</h2>
      <p class="chat-main-subtitle">
        {{ subtitle }}
      </p>
      <div v-if="loading" class="chat-loading">Loading conversation...</div>
      <div v-else-if="!conversation" class="chat-placeholder">
        Select a conversation from the left.
      </div>
      <div v-else class="chat-content">
        <div class="chat-meta-row">
          <span class="chat-meta-label">ID:</span>
          <span class="chat-meta-value">{{ conversation.id }}</span>
        </div>
        <div class="chat-meta-row">
          <span class="chat-meta-label">Title:</span>
          <span class="chat-meta-value">{{ conversation.title }}</span>
        </div>
        <div class="chat-thread">
          <div
            v-for="message in conversation.messages"
            :key="message.id"
            class="chat-message"
          >
            <div class="chat-message-role">{{ message.role }}</div>
            <div class="chat-message-text">{{ message.content }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  conversation: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const subtitle = computed(() => {
  return props.conversation?.id
    ? `Active conversation: ${props.conversation.id}`
    : 'Ready to load a conversation.'
})
</script>

<style scoped>
.chat-main {
  flex: 1;
  padding: 32px;
  display: flex;
  align-items: flex-start;
  background: radial-gradient(circle at top left, rgba(64, 158, 255, 0.08), transparent 55%);
  min-width: 0;
}

.chat-main-card {
  background-color: #ffffff;
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  border: 1px solid #e2e8f0;
  max-width: 620px;
  width: 100%;
}

.chat-main-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.chat-main-subtitle {
  margin: 0 0 16px;
  font-size: 14px;
  color: #4b5563;
}

.chat-loading {
  font-size: 13px;
  color: #6b7280;
}

.chat-placeholder {
  font-size: 13px;
  color: #6b7280;
}

.chat-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chat-meta-row {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.chat-meta-label {
  color: #6b7280;
  min-width: 44px;
}

.chat-meta-value {
  color: #111827;
  font-weight: 600;
}

.chat-thread {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.chat-message {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 14px;
  background-color: #f9fafb;
}

.chat-message-role {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #6b7280;
  margin-bottom: 6px;
}

.chat-message-text {
  font-size: 14px;
  color: #111827;
  line-height: 1.5;
}

@media (max-width: 960px) {
  .chat-main {
    padding: 24px;
  }
}
</style>
