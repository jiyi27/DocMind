<template>
  <div class="dashboard">
    <section class="dashboard-hero">
      <div class="hero-copy">
        <div class="hero-title-row">
          <h1 class="page-title">Knowledge Bases</h1>
          <el-tag type="info" effect="plain" round>{{ kbStore.kbCount }}</el-tag>
        </div>
        <p class="page-desc">
          Keep your retrieval spaces organized, inspect embedding settings quickly, and jump into
          document operations without digging through tables.
        </p>
      </div>

      <div class="hero-actions">
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

    <section class="stats-grid">
      <article class="stat-card">
        <span class="stat-label">Knowledge Bases</span>
        <strong class="stat-value">{{ kbStore.kbCount }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">Accessible Spaces</span>
        <strong class="stat-value">{{ accessibleCount }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">Admin Scope</span>
        <strong class="stat-value">{{ isSuperAdmin ? 'All workspaces' : 'Assigned only' }}</strong>
      </article>
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

.dashboard-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding: 24px 26px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.14), transparent 34%),
    linear-gradient(135deg, #ffffff 0%, #f8fbff 58%, #f3f8f7 100%);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-lg);
}

.hero-copy {
  max-width: 760px;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 32px;
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dm-text);
}

.page-desc {
  margin: 0;
  color: var(--dm-text-muted);
  line-height: 1.7;
  font-size: 14px;
}

.hero-actions {
  flex-shrink: 0;
}

.create-button {
  min-width: 220px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 22px;
}

.stat-card {
  padding: 18px 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.stat-label {
  display: block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--dm-text-soft);
}

.stat-value {
  font-size: 24px;
  color: var(--dm-text);
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
  .dashboard-hero {
    flex-direction: column;
    align-items: stretch;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .create-button {
    width: 100%;
  }
}
</style>
