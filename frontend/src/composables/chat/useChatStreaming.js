import { onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getChatSessionDetail, sendChatMessageStream } from '@/api/chats'

export function useChatStreaming({ activeChatId, chatList, getConversationById, syncActiveConversation }) {
  const sending = ref(false)

  let activeStreamController = null
  let activeStreamSessionId = ''

  function abortActiveStream() {
    if (!activeStreamController) return

    activeStreamController.abort()
    activeStreamController = null
    activeStreamSessionId = ''
    sending.value = false
  }

  function handleSessionSwitch(nextChatId) {
    if (sending.value && activeStreamSessionId && activeStreamSessionId !== nextChatId) {
      abortActiveStream()
    }
  }

  function handleChatDelete(sessionId) {
    if (activeStreamSessionId === sessionId) {
      abortActiveStream()
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
          syncActiveConversation(sessionId, conversation)
          return
        }
      } catch {
        // Non-critical follow-up request.
      }

      if (attempt < maxAttempts) {
        pollForTitle(sessionId, sidebarItem, conversation, attempt + 1, maxAttempts, intervalMs)
      }
    }, intervalMs)
  }

  async function sendMessage(input) {
    if (!activeChatId.value || sending.value) return

    const sessionId = activeChatId.value
    const conversation = getConversationById(sessionId)
    if (!conversation) return

    const isFirstTurn = conversation.messages.length === 0

    conversation.messages.push({ role: 'user', content: input, id: Date.now() })

    const assistantMessage = {
      role: 'assistant',
      content: '',
      citations: [],
      id: Date.now() + 1,
      streaming: true,
    }
    conversation.messages.push(assistantMessage)
    syncActiveConversation(sessionId, conversation)

    sending.value = true

    const controller = new AbortController()
    activeStreamController = controller
    activeStreamSessionId = sessionId

    try {
      let pendingCitations = []

      await sendChatMessageStream(sessionId, input, {
        signal: controller.signal,
        onCitations(citations) {
          pendingCitations = citations
        },
        onChunk(text) {
          assistantMessage.content += text
          syncActiveConversation(sessionId, conversation)
        },
        onDone() {
          assistantMessage.streaming = false
          assistantMessage.citations = pendingCitations
          syncActiveConversation(sessionId, conversation)

          const sidebarItem = chatList.value.find((item) => item.id === sessionId)
          if (sidebarItem) {
            sidebarItem.message_count = (sidebarItem.message_count || 0) + 2
            sidebarItem.last_message_preview = assistantMessage.content.slice(0, 80)
          }

          if (isFirstTurn) {
            pollForTitle(sessionId, sidebarItem, conversation)
          }
        },
        onError(message) {
          assistantMessage.streaming = false
          assistantMessage.status = 'error'
          syncActiveConversation(sessionId, conversation)
          ElMessage.error(message || 'Stream error, please try again')
        },
      })
    } catch (error) {
      if (error?.name === 'AbortError') {
        assistantMessage.streaming = false
        syncActiveConversation(sessionId, conversation)
        return
      }

      assistantMessage.streaming = false
      assistantMessage.status = 'error'
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

  onBeforeUnmount(() => {
    abortActiveStream()
  })

  return {
    sending,
    abortActiveStream,
    handleSessionSwitch,
    handleChatDelete,
    sendMessage,
  }
}
