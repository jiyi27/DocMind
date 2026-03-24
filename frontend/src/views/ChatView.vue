<template>
  <div class="chat-page">
    <section class="chat-shell">
      <ChatSidebar
        :items="chatList"
        :active-id="activeChatId"
        :loading="loadingList"
        :loading-more="loadingMore"
        :has-more="chatList.length < chatTotal"
        @select="selectChat"
        @create="createNewChat"
        @delete="removeChat"
        @load-more="loadMoreChats"
      />
      <ChatMain
        :conversation="activeConversation"
        :loading="loadingDetail"
        :sending="sending"
        @send="sendMessage"
      />
    </section>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatMain from '@/components/chat/ChatMain.vue'
import { fetchChatDetail } from '@/services/chat'
import {
  createChatSession,
  deleteChatSession,
  getChatSessionDetail,
  getChatSessions,
  sendChatMessageStream,
} from '@/api/chats'

const chatList = ref([])
const activeChatId = ref('')
const activeConversation = ref(null)
const loadingList = ref(false)
const loadingDetail = ref(false)
const sending = ref(false)

const PAGE_SIZE = 50
const chatTotal = ref(0)
const chatOffset = ref(0)
const loadingMore = ref(false)

const detailCache = new Map()
let detailRequestToken = 0
let activeStreamController = null
let activeStreamSessionId = ''

function isConversationEmpty(conversation) {
  return Boolean(conversation) && Array.isArray(conversation.messages) && conversation.messages.length === 0
}

function findReusableEmptyChatId() {
  if (isConversationEmpty(activeConversation.value) && activeChatId.value) {
    return activeChatId.value
  }

  for (const [sessionId, conversation] of detailCache.entries()) {
    if (isConversationEmpty(conversation)) {
      return sessionId
    }
  }

  const listMatch = chatList.value.find((item) => (item.message_count ?? 0) === 0)
  return listMatch?.id || ''
}

function getNextChatIdAfterDelete(deletedChatId) {
  const remainingItems = chatList.value.filter((item) => item.id !== deletedChatId)
  return remainingItems[0]?.id || ''
}

function syncActiveConversation(sessionId, conversation) {
  if (activeChatId.value === sessionId) {
    activeConversation.value = { ...conversation }
  }
}

function abortActiveStream() {
  if (!activeStreamController) return
  activeStreamController.abort()
  activeStreamController = null
  activeStreamSessionId = ''
  sending.value = false
}

onMounted(async () => {
  await loadChatList()
  if (chatList.value.length > 0) {
    selectChat(chatList.value[0].id)
  }
})

onBeforeUnmount(() => {
  abortActiveStream()
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

  if (sending.value && activeStreamSessionId && activeStreamSessionId !== chatId) {
    abortActiveStream()
  }

  activeChatId.value = chatId
  const requestToken = ++detailRequestToken

  const cached = detailCache.get(chatId)
  if (cached) {
    activeConversation.value = cached
    loadingDetail.value = false
    return
  }

  loadingDetail.value = true
  try {
    const detail = await fetchChatDetail(chatId)
    detailCache.set(chatId, detail)
    if (requestToken === detailRequestToken && activeChatId.value === chatId) {
      activeConversation.value = detail
    }
  } finally {
    if (requestToken === detailRequestToken && activeChatId.value === chatId) {
      loadingDetail.value = false
    }
  }
}

async function createNewChat() {
  const reusableChatId = findReusableEmptyChatId()
  if (reusableChatId) {
    await selectChat(reusableChatId)
    return
  }

  try {
    const session = await createChatSession({ title: 'New Conversation' })
    const sessionId = session.id

    const newItem = {
      id: sessionId,
      title: session.title,
      message_count: session.message_count ?? 0,
      created_at: session.created_at,
      updated_at: session.updated_at,
    }
    chatList.value = [newItem, ...chatList.value]

    const seededDetail = { id: sessionId, title: session.title, messages: [] }
    detailCache.set(sessionId, seededDetail)
    activeConversation.value = seededDetail
    activeChatId.value = sessionId
  } catch {
    ElMessage.error('Failed to create new chat, please try again')
  }
}

async function removeChat(item) {
  if (!item?.id) return

  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete "${item.title || 'this chat'}"? This cannot be undone.`,
      'Delete Chat',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }

  const sessionId = item.id
  const nextChatId = getNextChatIdAfterDelete(sessionId)

  if (activeStreamSessionId === sessionId) {
    abortActiveStream()
  }

  try {
    await deleteChatSession(sessionId)
    chatList.value = chatList.value.filter((chat) => chat.id !== sessionId)
    detailCache.delete(sessionId)
    chatTotal.value = Math.max(0, chatTotal.value - 1)

    if (activeChatId.value === sessionId) {
      activeChatId.value = ''
      activeConversation.value = null

      if (nextChatId) {
        await selectChat(nextChatId)
      }
    }

    ElMessage.success('Chat deleted')
  } catch {
    // Error handled by interceptor.
  }
}

function pollForTitle(sessionId, sidebarItem, conversation, attempt = 1, maxAttempts = 3, intervalMs = 3000) {
  setTimeout(async () => {
    try {
      const refreshed = await getChatSessionDetail(sessionId)
      const session = refreshed.session || {}
      const title = session.title || ''

      if (title && title !== 'New Conversation') {
        if (sidebarItem) sidebarItem.title = title
        conversation.title = title
        return
      }
    } catch {
      // Non-critical
    }

    if (attempt < maxAttempts) {
      pollForTitle(sessionId, sidebarItem, conversation, attempt + 1, maxAttempts, intervalMs)
    }
  }, intervalMs)
}

async function sendMessage(input) {
  if (!activeChatId.value || sending.value) return

  const sessionId = activeChatId.value
  const conversation = detailCache.get(sessionId)
  if (!conversation) return

  const isFirstTurn = conversation.messages.length === 0
  conversation.messages.push({ role: 'user', content: input, id: Date.now() })

  const assistantMsg = { role: 'assistant', content: '', sources: [], id: Date.now() + 1, streaming: true }
  conversation.messages.push(assistantMsg)
  activeConversation.value = { ...conversation }

  sending.value = true
  const controller = new AbortController()
  activeStreamController = controller
  activeStreamSessionId = sessionId
  try {
    let pendingSources = []
    await sendChatMessageStream(sessionId, input, {
      signal: controller.signal,
      onSources(sources) {
        pendingSources = sources
      },
      onChunk(text) {
        assistantMsg.content += text
        syncActiveConversation(sessionId, conversation)
      },
      onDone() {
        assistantMsg.streaming = false
        assistantMsg.sources = pendingSources
        syncActiveConversation(sessionId, conversation)

        const sidebarItem = chatList.value.find((c) => c.id === sessionId)
        if (sidebarItem) {
          sidebarItem.message_count = (sidebarItem.message_count || 0) + 2
          sidebarItem.last_message_preview = assistantMsg.content.slice(0, 80)
        }

        if (isFirstTurn) {
          pollForTitle(sessionId, sidebarItem, conversation)
        }
      },
      onError(message) {
        assistantMsg.streaming = false
        assistantMsg.status = 'error'
        syncActiveConversation(sessionId, conversation)
        ElMessage.error(message || 'Stream error, please try again')
      },
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      assistantMsg.streaming = false
      syncActiveConversation(sessionId, conversation)
      return
    }

    assistantMsg.streaming = false
    assistantMsg.status = 'error'
    syncActiveConversation(sessionId, conversation)
    ElMessage.error('Failed to send message, please try again')
  } finally {
    if (activeStreamController === controller) {
      activeStreamController = null
      activeStreamSessionId = ''
    }
    sending.value = false
  }
}
</script>

<style scoped>
.chat-page {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.chat-shell {
  display: flex;
  height: 100%;
  min-height: 0;
  border-radius: 30px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(247, 250, 252, 0.94) 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow:
    0 20px 50px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

@media (max-width: 960px) {
  .chat-page {
    overflow: visible;
  }

  .chat-shell {
    flex-direction: column;
  }
}
</style>
