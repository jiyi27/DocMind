<template>
  <div class="user-profile">
    <section class="profile-toolbar">
      <div class="profile-header">
        <el-avatar :size="72" class="profile-avatar">
          {{ userInitial }}
        </el-avatar>
        <div class="profile-details">
          <div class="profile-title-row">
            <h1 class="profile-name">{{ username }}</h1>
            <el-tag v-if="isSuperAdmin" type="danger" effect="plain" round>Super Admin</el-tag>
            <el-tag v-else type="info" effect="plain" round>User</el-tag>
          </div>
          <div class="profile-meta">
            <span class="meta-pill">
              <span class="meta-label">Username</span>
              <strong>{{ username }}</strong>
            </span>
            <span class="meta-pill">
              <span class="meta-label">Role</span>
              <strong>{{ isSuperAdmin ? 'Super Admin' : 'User' }}</strong>
            </span>
            <span class="meta-pill">
              <span class="meta-label">Knowledge Base</span>
              <strong>{{ kbLabel }}</strong>
            </span>
          </div>
        </div>
      </div>
    </section>

    <section class="documents-panel">
      <div class="section-head">
        <div>
          <h2 class="section-title">My Uploaded Documents</h2>
          <p class="section-desc">Everything you uploaded across accessible workspaces.</p>
        </div>
      </div>
      <div class="doc-list-wrap">
        <DocumentList mode="profile" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const authStore = useAuthStore()
const kbStore = useKbStore()

const username = computed(() => authStore.user?.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isSuperAdmin = computed(() => authStore.isSuperAdmin)
const scopedKb = computed(() =>
  kbStore.kbList.find((kb) => String(kb.id) === String(authStore.kbId)) || null,
)
const kbLabel = computed(() => {
  if (isSuperAdmin.value) return 'All workspaces'
  return scopedKb.value?.display_name || scopedKb.value?.name || 'Assigned workspace'
})

onMounted(() => {
  if (!isSuperAdmin.value && authStore.kbId && kbStore.kbList.length === 0) {
    kbStore.fetchKbs()
  }
})
</script>

<style scoped>
.user-profile {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
}

.profile-toolbar {
  margin-bottom: 20px;
  padding: 4px 2px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 18px;
}

.profile-avatar {
  background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%);
  color: #ffffff;
  font-size: 28px;
  font-weight: 700;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
}

.profile-details {
  min-width: 0;
}

.profile-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-name {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dm-text);
}

.profile-meta {
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

.documents-panel {
  padding: 22px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.section-head {
  margin-bottom: 16px;
}

.section-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 800;
  color: var(--dm-text);
}

.section-desc {
  margin: 0;
  font-size: 13px;
  color: var(--dm-text-soft);
}

.doc-list-wrap {
  max-height: calc(100vh - 320px);
  min-height: 320px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 960px) {
  .profile-header {
    align-items: flex-start;
  }
}

@media (max-width: 720px) {
  .documents-panel {
    padding: 18px;
  }

  .profile-header {
    flex-direction: column;
  }

  .profile-name {
    font-size: 24px;
  }
}
</style>
