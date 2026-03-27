<template>
  <div class="chat-page">
    <section class="chat-shell">
      <ChatSidebar
        :items="chatList"
        :active-id="activeChatId"
        :loading="loadingList"
        :loading-more="loadingMore"
        :has-more="chatList.length < chatTotal"
        @select="handleSelectChat"
        @create="createNewChat"
        @delete="handleRemoveChat"
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
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatMain from '@/components/chat/ChatMain.vue'
import { useChatSessions } from '@/composables/chat/useChatSessions'
import { useChatStreaming } from '@/composables/chat/useChatStreaming'

const {
  chatList,
  activeChatId,
  activeConversation,
  loadingList,
  loadingDetail,
  chatTotal,
  loadingMore,
  getConversationById,
  syncActiveConversation,
  loadMoreChats,
  selectChat,
  createNewChat,
  removeChat,
} = useChatSessions()

const { sending, handleSessionSwitch, handleChatDelete, sendMessage } = useChatStreaming({
  activeChatId,
  chatList,
  getConversationById,
  syncActiveConversation,
})

function handleSelectChat(chatId) {
  return selectChat(chatId, { onBeforeSelect: handleSessionSwitch })
}

function handleRemoveChat(item) {
  return removeChat(item, { onBeforeDelete: handleChatDelete })
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
