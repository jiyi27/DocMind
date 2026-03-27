<template>
  <section class="chat-main">
    <div v-if="loading" class="chat-status">Loading conversation...</div>
    <div v-else-if="!conversation" class="chat-status">
      Select a conversation or create a new one.
    </div>

    <template v-else>
      <div class="chat-thread scrollbar-hidden" ref="threadRef">
        <div v-if="conversation.messages.length === 0" class="chat-empty-thread">
          Start a conversation with your knowledge base.
        </div>
        <div
          v-for="(message, index) in conversation.messages"
          :key="message.id ?? index"
          class="chat-message"
          :class="[message.role, { 'msg-error': message.status === 'error' }]"
        >
          <div class="chat-message-role">
            {{ message.role === 'user' ? 'You' : 'Assistant' }}
          </div>
          <div class="chat-message-text">
            <template v-if="message.streaming && !message.content">
              <div class="typing-dots"><span></span><span></span><span></span></div>
            </template>
            <template v-else>{{ message.content }}</template>
          </div>
          <div v-if="message.status === 'error'" class="msg-error-hint">
            Send failed, please try again.
          </div>
          <div v-if="message.sources && message.sources.length" class="chat-sources">
            <div class="sources-label">Sources</div>
            <div class="sources-list">
              <a
                v-for="(src, i) in parseChatSources(message.sources)"
                :key="i"
                :href="src.url || undefined"
                :target="src.url ? '_blank' : undefined"
                :rel="src.url ? 'noopener noreferrer' : undefined"
                class="source-item"
                :class="{ 'source-item--no-link': !src.url }"
              >
                <span class="source-index">{{ src.index }}</span>
                <span class="source-title">{{ src.title }}</span>
              </a>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 5 }"
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
import { computed, nextTick, ref, watch } from 'vue'
import { parseChatSources } from '@/utils/chat/sources'

const props = defineProps({
  conversation: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  sending: {
    type: Boolean,
    default: false,
  },
})

const streamingContent = computed(() =>
  props.conversation?.messages?.find((m) => m.streaming)?.content,
)

const emit = defineEmits(['send'])

const inputText = ref('')
const threadRef = ref(null)
const AUTO_SCROLL_THRESHOLD = 50

function isNearBottom() {
  if (!threadRef.value) return true
  const { scrollTop, scrollHeight, clientHeight } = threadRef.value
  return scrollHeight - scrollTop - clientHeight <= AUTO_SCROLL_THRESHOLD
}

function submit() {
  const text = inputText.value.trim()
  if (!text || props.sending) return
  inputText.value = ''
  emit('send', text)
}

watch(
  () => [props.conversation?.id, props.conversation?.messages?.length, props.sending, streamingContent.value],
  async ([conversationId], previousValues = []) => {
    const [previousConversationId] = previousValues
    const shouldAutoScroll = conversationId !== previousConversationId || isNearBottom()

    await nextTick()
    if (threadRef.value && shouldAutoScroll) {
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
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.05), transparent 42%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(248, 250, 252, 0.92) 100%);
}

.chat-status {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--dm-text-soft);
  padding: 40px;
}

.chat-thread {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overscroll-behavior: contain;
}

.chat-empty-thread {
  margin: auto 0;
  padding: 20px 12px;
  text-align: center;
  font-size: 18px;
  font-weight: 500;
  letter-spacing: 0.01em;
  color: var(--dm-text-soft);
}

.chat-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 78%;
  padding: 14px 16px;
  border-radius: 20px;
  line-height: 1.6;
  font-size: 14px;
  border: 1px solid transparent;
}

.chat-message.user {
  align-self: flex-end;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #bfdbfe;
}

.chat-message.assistant {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.9);
  border-color: var(--dm-border-strong);
}

.chat-message.msg-error {
  border-color: #fca5a5;
  background: #fff5f5;
}

.chat-message-role {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--dm-text-soft);
  font-weight: 700;
}

.chat-message.user .chat-message-role {
  color: #1d4ed8;
}

.chat-message-text {
  color: var(--dm-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-error-hint {
  font-size: 12px;
  color: #ef4444;
}

.chat-sources {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--dm-border-strong);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sources-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--dm-text-soft);
  font-weight: 700;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: var(--dm-primary);
  text-decoration: none;
  background: rgba(239, 246, 255, 0.7);
  transition: background-color 0.18s ease;
}

.source-item:hover {
  background: rgba(219, 234, 254, 0.92);
}

.source-item--no-link {
  color: var(--dm-text-soft);
  cursor: default;
}

.source-item--no-link:hover {
  background: rgba(239, 241, 245, 0.72);
}

.source-index {
  flex-shrink: 0;
  font-weight: 700;
}

.source-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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
  background-color: #94a3b8;
  animation: bounce 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}

.chat-input-area {
  padding: 0 28px 20px;
  display: flex;
  gap: 12px;
  align-items: center;
  background: transparent;
}

.chat-input-area .el-textarea {
  flex: 1;
}

.chat-input-area :deep(.el-textarea__inner) {
  min-height: 0 !important;
  padding: 10px 14px;
  border-radius: 16px;
  line-height: 1.45;
}

.chat-input-area .el-button {
  flex-shrink: 0;
  height: 40px;
  min-width: 96px;
  padding: 0 18px;
  border-radius: 14px;
  align-self: center;
}

@media (max-width: 960px) {
  .chat-thread {
    padding: 18px;
  }

  .chat-message {
    max-width: 92%;
  }

  .chat-input-area {
    padding: 0 18px 18px;
    align-items: stretch;
  }
}

@media (max-width: 720px) {
  .chat-input-area {
    flex-direction: column;
  }

  .chat-input-area .el-button {
    width: 100%;
  }
}
</style>
