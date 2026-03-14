<template>
  <div class="chat-layout">
    <ChatSidebar
      :items="chatList"
      :active-id="activeChatId"
      :loading="loadingList"
      :loading-more="loadingMore"
      :has-more="chatList.length < chatTotal"
      @select="selectChat"
      @create="createNewChat"
      @load-more="loadMoreChats"
    />
    <ChatMain
      :conversation="activeConversation"
      :loading="loadingDetail"
      :sending="sending"
      @send="sendMessage"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatMain from '@/components/chat/ChatMain.vue'
import { fetchChatList, fetchChatDetail } from '@/services/chat'
import { getChatSessions, createChatSession, sendChatMessage, getChatSessionDetail } from '@/api/chats'

const chatList = ref([])
const activeChatId = ref('')
const activeConversation = ref(null)
const loadingList = ref(false)
const loadingDetail = ref(false)
const sending = ref(false)

// Pagination state for sidebar
const PAGE_SIZE = 50
const chatTotal = ref(0)
const chatOffset = ref(0)
const loadingMore = ref(false)

// Cache: sessionId → { id, title, messages[] }
// Messages in cache use { role: 'user'|'assistant', content, sources? }
const detailCache = new Map()

onMounted(async () => {
  await loadChatList()
  if (chatList.value.length > 0) {
    selectChat(chatList.value[0].id)
  }
})

async function loadChatList() {
  loadingList.value = true
  chatOffset.value = 0
  try {
    const data = await getChatSessions({ limit: PAGE_SIZE, offset: 0 })
    chatList.value = data.items || []
    chatTotal.value = data.total ?? chatList.value.length
    chatOffset.value = chatList.value.length
  } finally {
    loadingList.value = false
  }
}

async function loadMoreChats() {
  if (loadingMore.value || chatList.value.length >= chatTotal.value) return
  loadingMore.value = true
  try {
    const data = await getChatSessions({ limit: PAGE_SIZE, offset: chatOffset.value })
    const newItems = data.items || []
    chatList.value = [...chatList.value, ...newItems]
    chatOffset.value += newItems.length
    chatTotal.value = data.total ?? chatTotal.value
  } finally {
    loadingMore.value = false
  }
}

async function selectChat(chatId) {
  if (activeChatId.value === chatId && activeConversation.value) return

  activeChatId.value = chatId

  const cached = detailCache.get(chatId)
  if (cached) {
    activeConversation.value = cached
    return
  }

  loadingDetail.value = true
  try {
    const detail = await fetchChatDetail(chatId)
    detailCache.set(chatId, detail)
    activeConversation.value = detail
  } finally {
    loadingDetail.value = false
  }
}

async function createNewChat() {
  try {
    const session = await createChatSession({ title: 'New Conversation' })
    const sessionId = session.id

    // Add to top of sidebar list using the server-assigned id
    const newItem = {
      id: sessionId,
      title: session.title,
      message_count: session.message_count ?? 0,
      created_at: session.created_at,
      updated_at: session.updated_at,
    }
    chatList.value = [newItem, ...chatList.value]

    // Seed an empty local conversation in the cache
    const seededDetail = { id: sessionId, title: session.title, messages: [] }
    detailCache.set(sessionId, seededDetail)
    activeConversation.value = seededDetail
    activeChatId.value = sessionId
  } catch {
    ElMessage.error('Failed to create new chat, please try again')
  }
}

/**
 * Poll GET /chats/{sessionId} until the server has written an LLM-generated
 * title (i.e. title is no longer "New Conversation"), then update the sidebar.
 * Stops after maxAttempts regardless of the result — never loops infinitely.
 */
function pollForTitle(sessionId, sidebarItem, conversation, attempt = 1, maxAttempts = 3, intervalMs = 3000) {
  setTimeout(async () => {
    try {
      const refreshed = await getChatSessionDetail(sessionId)
      const session = refreshed.session || {}
      const title = session.title || ''

      if (title && title !== 'New Conversation') {
        // Real title is ready — update sidebar and cached conversation
        if (sidebarItem) sidebarItem.title = title
        conversation.title = title
        return
      }
    } catch {
      // Non-critical — let the retry logic continue
    }

    // Title not ready yet, retry if attempts remain
    if (attempt < maxAttempts) {
      pollForTitle(sessionId, sidebarItem, conversation, attempt + 1, maxAttempts, intervalMs)
    }
    // After maxAttempts the sidebar keeps showing "New Conversation" — acceptable fallback
  }, intervalMs)
}

/**
 * Send a user message in the active conversation.
 * Called by ChatMain via the @send event.
 *
 * @param {string} input - The user's question
 */
async function sendMessage(input) {
  if (!activeChatId.value || sending.value) return

  const sessionId = activeChatId.value
  const conversation = detailCache.get(sessionId)
  if (!conversation) return

  // Optimistically append the user message to the UI
  conversation.messages.push({ role: 'user', content: input, id: Date.now() })
  activeConversation.value = { ...conversation }

  sending.value = true
  try {
    const result = await sendChatMessage(sessionId, input)

    // Mark the optimistic user message as successfully sent
    const userMsg = conversation.messages[conversation.messages.length - 1]
    if (userMsg) delete userMsg.status

    const assistantMsg = {
      role: 'assistant',
      content: result.answer,
      sources: result.sources || [],
      id: Date.now() + 1,
    }
    conversation.messages.push(assistantMsg)
    activeConversation.value = { ...conversation }

    // Update sidebar preview counters immediately
    const sidebarItem = chatList.value.find((c) => c.id === sessionId)
    if (sidebarItem) {
      sidebarItem.message_count = (sidebarItem.message_count || 0) + 2
      sidebarItem.last_message_preview = result.answer.slice(0, 80)
    }

    // First turn: title is generated async on the server after the response.
    // Poll GET /chats/{id} up to 3 times (every 3s) until a real title appears.
    if (result.is_first_turn) {
      pollForTitle(sessionId, sidebarItem, conversation)
    }
  } catch {
    // Keep the user message in the UI but mark it as failed so the user can
    // see what they sent. Removing it entirely risks losing input on timeout
    // when the backend may have already persisted it successfully.
    const userMsg = conversation.messages[conversation.messages.length - 1]
    if (userMsg) userMsg.status = 'error'
    activeConversation.value = { ...conversation }
    ElMessage.error('Failed to send message, please try again')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  border-radius: 16px;
  overflow: hidden;
  background-color: #ffffff;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

@media (max-width: 960px) {
  .chat-layout {
    flex-direction: column;
  }
}
</style>
