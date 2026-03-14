<template>
  <div class="chat-layout">
    <ChatSidebar
      :items="chatList"
      :active-id="activeChatId"
      :loading="loadingList"
      @select="selectChat"
      @create="createNewChat"
    />
    <ChatMain :conversation="activeConversation" :loading="loadingDetail" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatMain from '@/components/chat/ChatMain.vue'
import { fetchChatList, fetchChatDetail } from '@/services/chat'

const chatList = ref([])
const activeChatId = ref('')
const activeConversation = ref(null)
const loadingList = ref(false)
const loadingDetail = ref(false)
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
    chatList.value = await fetchChatList()
  } finally {
    loadingList.value = false
  }
}

async function selectChat(chatId) {
  if (activeChatId.value === chatId && activeConversation.value) {
    return
  }
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

function createNewChat() {
  const nextId = `chat-${String(Date.now()).slice(-6)}`
  const newItem = { id: nextId, title: 'New Conversation' }
  // Optimistically add the new chat to the list.
  chatList.value = [newItem, ...chatList.value]
  // Seed an empty detail to keep UI responsive.
  const seededDetail = { id: nextId, title: newItem.title, messages: [] }
  detailCache.set(nextId, seededDetail)
  activeConversation.value = seededDetail
  activeChatId.value = nextId
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
