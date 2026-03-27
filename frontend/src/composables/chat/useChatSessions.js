import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createChatSession, deleteChatSession, getChatSessions } from '@/api/chats'
import { fetchChatDetail } from '@/services/chat'

const PAGE_SIZE = 50

export function useChatSessions() {
  const chatList = ref([])
  const activeChatId = ref('')
  const activeConversation = ref(null)
  const loadingList = ref(false)
  const loadingDetail = ref(false)
  const chatTotal = ref(0)
  const chatOffset = ref(0)
  const loadingMore = ref(false)

  const detailCache = new Map()
  let detailRequestToken = 0

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

  function getConversationById(sessionId) {
    return detailCache.get(sessionId)
  }

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

  async function selectChat(chatId, options = {}) {
    const { onBeforeSelect } = options

    if (activeChatId.value === chatId && activeConversation.value) return

    onBeforeSelect?.(chatId)

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

      chatList.value = [
        {
          id: sessionId,
          title: session.title,
          message_count: session.message_count ?? 0,
          created_at: session.created_at,
          updated_at: session.updated_at,
        },
        ...chatList.value,
      ]

      const seededDetail = { id: sessionId, title: session.title, messages: [] }
      detailCache.set(sessionId, seededDetail)
      activeConversation.value = seededDetail
      activeChatId.value = sessionId
      chatTotal.value += 1
    } catch {
      ElMessage.error('Failed to create new chat, please try again')
    }
  }

  async function removeChat(item, options = {}) {
    const { onBeforeDelete } = options

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

    onBeforeDelete?.(sessionId)

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

  onMounted(async () => {
    await loadChatList()
    if (chatList.value.length > 0) {
      selectChat(chatList.value[0].id)
    }
  })

  return {
    chatList,
    activeChatId,
    activeConversation,
    loadingList,
    loadingDetail,
    chatTotal,
    loadingMore,
    detailCache,
    getConversationById,
    syncActiveConversation,
    loadMoreChats,
    selectChat,
    createNewChat,
    removeChat,
  }
}
