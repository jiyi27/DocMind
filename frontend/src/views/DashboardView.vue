<template>
  <div class="dashboard">
    <section class="dashboard-toolbar">
      <div class="toolbar-copy">
        <div class="toolbar-title-row">
          <h1 class="page-title">Knowledge Bases</h1>
          <el-tag type="info" effect="plain" round>{{ kbStore.kbCount }}</el-tag>
        </div>
        <div class="toolbar-meta">
          <span class="meta-pill">
            <span class="meta-label">Accessible</span>
            <strong>{{ accessibleCount }}</strong>
          </span>
          <span class="meta-pill">
            <span class="meta-label">Scope</span>
            <strong>{{ isSuperAdmin ? 'All workspaces' : 'Assigned only' }}</strong>
          </span>
        </div>
      </div>

      <div class="toolbar-actions">
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
const accessibleCount = computed(() => {
  if (isSuperAdmin.value) return kbStore.kbCount
  return kbStore.kbList.filter((kb) => authStore.canAccessKb(kb.id)).length
})

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
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  padding: 4px 2px;
}

.toolbar-copy {
  min-width: 0;
}

.toolbar-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 30px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dm-text);
}

.toolbar-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--dm-border);
  background: rgba(255, 255, 255, 0.86);
  color: var(--dm-text);
  font-size: 13px;
}

.meta-label {
  color: var(--dm-text-soft);
}

.toolbar-actions {
  flex-shrink: 0;
}

.create-button {
  min-width: 188px;
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
  .dashboard-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-meta {
    gap: 8px;
  }

  .create-button {
    width: 100%;
  }
}
</style>
