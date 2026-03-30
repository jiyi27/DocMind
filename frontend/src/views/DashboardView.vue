<template>
  <div class="dashboard">
    <section v-if="isSuperAdmin || kbStore.kbCount > 0" class="dashboard-toolbar">
      <div class="toolbar-actions">
        <span class="workspace-count">{{ kbStore.kbCount }} workspaces</span>
        <el-button
          v-if="isSuperAdmin"
          type="primary"
          :icon="Plus"
          class="create-button"
          @click="openCreateDialog"
        >
          Create Knowledge Base
        </el-button>
      </div>
    </section>

    <div v-if="kbStore.loading" class="loading-panel">
      <el-skeleton :rows="4" animated />
    </div>

    <section
      v-else-if="kbStore.kbList.length === 0"
      class="empty-panel"
    >
      <el-empty description="No knowledge bases yet" :image-size="120">
        <el-button v-if="isSuperAdmin" type="primary" @click="openCreateDialog">
          Create Now
        </el-button>
      </el-empty>
    </section>

    <el-row v-else :gutter="20" class="kb-grid">
      <el-col
        v-for="kb in kbStore.kbList"
        :key="kb.id"
        :xs="24"
        :sm="12"
        :md="8"
        :lg="6"
        class="kb-col"
      >
        <KbCard :kb="kb" @delete="handleDeleteKb" />
      </el-col>
    </el-row>

    <CreateKbDialog ref="createDialogRef" @success="handleCreateKb" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import CreateKbDialog from '@/components/kb/CreateKbDialog.vue'
import KbCard from '@/components/kb/KbCard.vue'

const authStore = useAuthStore()
const kbStore = useKbStore()

const createDialogRef = ref(null)
const isSuperAdmin = computed(() => authStore.isSuperAdmin)
onMounted(() => {
  kbStore.fetchKbs()
})

function openCreateDialog() {
  createDialogRef.value?.open()
}

async function handleCreateKb(formData) {
  await kbStore.addKb(formData)
  ElMessage.success('Knowledge base created successfully')
}

async function handleDeleteKb(kbId) {
  await kbStore.removeKb(kbId)
  ElMessage.success('Knowledge base deleted')
}
</script>

<style scoped>
.dashboard {
  max-width: 1380px;
  width: 100%;
  margin: 0 auto;
  padding-top: 28px;
}

.dashboard-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  padding: 4px 2px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.workspace-count {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--dm-border);
  background: rgba(255, 255, 255, 0.82);
  color: var(--dm-text-muted);
  font-size: 13px;
  font-weight: 700;
}

.create-button {
  min-width: 176px;
}

.loading-panel,
.empty-panel {
  padding: 26px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.kb-grid {
  margin-top: 4px;
}

.kb-col {
  margin-bottom: 20px;
}

@media (max-width: 960px) {
  .create-button {
    width: 100%;
  }
}
</style>
