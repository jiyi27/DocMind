<template>
  <div class="chat-layout">
    <ChatSidebar
      :items="chatList"
      :active-id="activeChatId"
      :loading="loadingList"
      @select="selectChat"
      @create="createNewChat"
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
import { v4 as uuidv4 } from 'uuid'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatMain from '@/components/chat/ChatMain.vue'
import { fetchChatList, fetchChatDetail } from '@/services/chat'
import { getChatSessions, sendChatMessage } from '@/api/chats'

const chatList = ref([])
const activeChatId = ref('')
const activeConversation = ref(null)
const loadingList = ref(false)
const loadingDetail = ref(false)
const sending = ref(false)

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
  try {
    const data = await getChatSessions({ limit: 50 })
    chatList.value = data.items || []
  } finally {
    loadingList.value = false
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
  const sessionId = uuidv4()
  const newItem = { id: sessionId, title: 'New Conversation', message_count: 0 }

  // Optimistically add to sidebar list
  chatList.value = [newItem, ...chatList.value]

  // Seed an empty conversation — session is created on first message send
  const seededDetail = { id: sessionId, title: newItem.title, messages: [] }
  detailCache.set(sessionId, seededDetail)
  activeConversation.value = seededDetail
  activeChatId.value = sessionId
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

  // Snapshot current history (prior turns only, excluding the new question)
  const history = conversation.messages.map(({ role, content }) => ({ role, content }))

  // Optimistically append the user message to the UI
  conversation.messages.push({ role: 'user', content: input, id: Date.now() })
  activeConversation.value = { ...conversation }

  sending.value = true
  try {
    const result = await sendChatMessage(sessionId, input, history)

    const assistantMsg = {
      role: 'assistant',
      content: result.answer,
      sources: result.sources || [],
      id: Date.now() + 1,
    }
    conversation.messages.push(assistantMsg)
    activeConversation.value = { ...conversation }

    // Update the sidebar title on the first turn
    const sidebarItem = chatList.value.find((c) => c.id === sessionId)
    if (sidebarItem && sidebarItem.message_count === 0) {
      sidebarItem.title = input.slice(0, 60)
      conversation.title = sidebarItem.title
    }
    if (sidebarItem) {
      sidebarItem.message_count = (sidebarItem.message_count || 0) + 2
      sidebarItem.last_message_preview = result.answer.slice(0, 80)
    }
  } catch {
    // Remove the optimistically added user message on failure
    conversation.messages.pop()
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
