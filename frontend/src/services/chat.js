// Chat service abstraction for fetching list + detail via API.

import { getChatSessions, getChatSessionDetail } from '@/api/chats'

export async function fetchChatList({ limit = 50, offset = 0, kbId = null } = {}) {
  const params = { limit, offset }
  if (kbId) {
    params.kb_id = kbId
  }
  const data = await getChatSessions(params)
  return data.items || []
}

export async function fetchChatDetail(chatId) {
  const data = await getChatSessionDetail(chatId)
  const session = data.session || {}
  const messages = data.messages || []
  return {
    id: session.id || chatId,
    title: session.title || 'Untitled',
    messages
  }
}
