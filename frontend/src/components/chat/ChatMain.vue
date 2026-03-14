<template>
  <section class="chat-main">
    <!-- Empty state -->
    <div v-if="loading" class="chat-status">Loading conversation...</div>
    <div v-else-if="!conversation" class="chat-status">
      Select a conversation or create a new one.
    </div>

    <!-- Active conversation -->
    <template v-else>
      <!-- Message thread -->
      <div class="chat-thread" ref="threadRef">
        <div v-if="conversation.messages.length === 0" class="chat-empty-thread">
          Ask anything about your knowledge base.
        </div>
        <div
          v-for="(message, index) in conversation.messages"
          :key="message.id ?? index"
          class="chat-message"
          :class="message.role"
        >
          <div class="chat-message-role">
            {{ message.role === 'user' ? 'You' : 'Assistant' }}
          </div>
          <div class="chat-message-text">{{ message.content }}</div>
          <!-- Sources -->
          <div v-if="message.sources && message.sources.length" class="chat-sources">
            <span class="sources-label">Sources:</span>
            <span v-for="(src, i) in message.sources" :key="i" class="source-item">
              {{ src }}
            </span>
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="sending" class="chat-message assistant typing">
          <div class="chat-message-role">Assistant</div>
          <div class="chat-message-text typing-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="Type your question and press Enter or click Send..."
          :disabled="sending"
          resize="none"
          @keydown.enter.exact.prevent="submit"
        />
        <el-button
          type="primary"
          :loading="sending"
          :disabled="!inputText.trim()"
          @click="submit"
        >
          Send
        </el-button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  conversation: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  // Whether the parent is currently awaiting an LLM response
  sending: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['send'])

const inputText = ref('')
const threadRef = ref(null)

function submit() {
  const text = inputText.value.trim()
  if (!text || props.sending) return
  inputText.value = ''
  emit('send', text)
}

// Auto-scroll to the bottom when new messages arrive or sending state changes
watch(
  () => [props.conversation?.messages?.length, props.sending],
  async () => {
    await nextTick()
    if (threadRef.value) {
      threadRef.value.scrollTop = threadRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: radial-gradient(circle at top left, rgba(64, 158, 255, 0.06), transparent 55%);
}

.chat-status {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #6b7280;
  padding: 40px;
}

/* ── Thread ─────────────────────────────────────────── */
.chat-thread {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-empty-thread {
  font-size: 14px;
  color: #9ca3af;
  text-align: center;
  margin-top: 48px;
}

.chat-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 78%;
  padding: 12px 16px;
  border-radius: 14px;
  line-height: 1.55;
  font-size: 14px;
}

.chat-message.user {
  align-self: flex-end;
  background-color: #eff6ff;
  border: 1px solid #bfdbfe;
}

.chat-message.assistant {
  align-self: flex-start;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
}

.chat-message-role {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: #9ca3af;
}

.chat-message.user .chat-message-role {
  color: #60a5fa;
}

.chat-message-text {
  color: #111827;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Sources ─────────────────────────────────────────── */
.chat-sources {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.sources-label {
  color: #6b7280;
  font-weight: 600;
}

.source-item {
  color: #3b82f6;
  background: #eff6ff;
  border-radius: 6px;
  padding: 2px 8px;
}

/* ── Typing indicator ───────────────────────────────── */
.typing-dots {
  display: flex;
  gap: 5px;
  align-items: center;
  height: 20px;
}

.typing-dots span {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #9ca3af;
  animation: bounce 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40%           { transform: translateY(-6px); }
}

/* ── Input area ─────────────────────────────────────── */
.chat-input-area {
  padding: 16px 24px 20px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background-color: #ffffff;
}

.chat-input-area .el-textarea {
  flex: 1;
}

.chat-input-area .el-button {
  flex-shrink: 0;
  height: 40px;
  padding: 0 20px;
}

@media (max-width: 960px) {
  .chat-thread {
    padding: 16px;
  }

  .chat-message {
    max-width: 92%;
  }

  .chat-input-area {
    padding: 12px 16px 16px;
  }
}
</style>
