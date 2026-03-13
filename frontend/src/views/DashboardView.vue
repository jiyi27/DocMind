<template>
  <div class="dashboard">
    <!-- Page Header -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h1 class="page-title">Knowledge Bases</h1>
        <el-tag type="info" size="small">{{ kbStore.kbCount }}</el-tag>
      </div>
      <el-button
        v-if="isSuperAdmin"
        type="primary"
        :icon="Plus"
        @click="openCreateDialog"
      >
        Create Knowledge Base
      </el-button>
      <!-- Only super admins can create KBs; KB admins manage their own KB from within -->
    </div>

    <!-- Loading State -->
    <div v-if="kbStore.loading" class="loading-wrap">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- Empty State -->
    <el-empty
      v-else-if="!kbStore.loading && kbStore.kbList.length === 0"
      description="No knowledge bases yet"
      :image-size="120"
    >
      <el-button v-if="isSuperAdmin" type="primary" @click="openCreateDialog">
        Create Now
      </el-button>
      <!-- KB admins see the empty state but cannot create new KBs -->
    </el-empty>

    <!-- KB Grid -->
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

    <!-- Create KB Dialog -->
    <CreateKbDialog ref="createDialogRef" @success="handleCreateKb" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { Plus } from '@element-plus/icons-vue'
import KbCard from '@/components/kb/KbCard.vue'
import CreateKbDialog from '@/components/kb/CreateKbDialog.vue'

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
}

async function handleDeleteKb(kbId) {
  await kbStore.removeKb(kbId)
}
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin: 0;
}

.loading-wrap {
  padding: 20px 0;
}

.kb-grid {
  margin-top: 8px;
}

.kb-col {
  margin-bottom: 20px;
}
</style>
