// Chat service abstraction for fetching list + detail.
// Replace the mock implementations with real HTTP requests later.

const mockChats = [
  { id: 'chat-001', title: 'RAG Onboarding' },
  { id: 'chat-002', title: 'Product FAQs' },
  { id: 'chat-003', title: 'Document Search' },
  { id: 'chat-004', title: 'Policy Assistant' }
]

const mockDetails = {
  'chat-001': {
    id: 'chat-001',
    title: 'RAG Onboarding',
    messages: [
      { id: 'm-1', role: 'user', content: 'How do we set up RAG?' },
      { id: 'm-2', role: 'assistant', content: 'Start with chunking and embeddings.' }
    ]
  },
  'chat-002': {
    id: 'chat-002',
    title: 'Product FAQs',
    messages: [
      { id: 'm-3', role: 'user', content: 'What is our SLA?' },
      { id: 'm-4', role: 'assistant', content: 'We promise a 99.9% uptime.' }
    ]
  },
  'chat-003': {
    id: 'chat-003',
    title: 'Document Search',
    messages: [
      { id: 'm-5', role: 'user', content: 'Find the onboarding PDF.' },
      { id: 'm-6', role: 'assistant', content: 'Here are the top matches.' }
    ]
  },
  'chat-004': {
    id: 'chat-004',
    title: 'Policy Assistant',
    messages: [
      { id: 'm-7', role: 'user', content: 'Summarize the policy change.' },
      { id: 'm-8', role: 'assistant', content: 'Here is the summary.' }
    ]
  }
}

function simulateDelay(data, delay = 300) {
  return new Promise(resolve => {
    setTimeout(() => resolve(data), delay)
  })
}

export async function fetchChatList() {
  return simulateDelay([...mockChats])
}

export async function fetchChatDetail(chatId) {
  const detail = mockDetails[chatId]
  return simulateDelay(
    detail || { id: chatId, title: 'Untitled', messages: [] },
    350
  )
}
