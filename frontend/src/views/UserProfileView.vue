<template>
  <div class="user-profile">
    <section class="profile-hero">
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
          <p class="profile-desc">
            Review your account scope and browse the documents you uploaded without leaving the
            workspace.
          </p>
        </div>
      </div>

      <div class="profile-stats">
        <article class="stat-card">
          <span class="stat-label">Username</span>
          <strong class="stat-value">{{ username }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">Role</span>
          <strong class="stat-value">{{ isSuperAdmin ? 'Super Admin' : 'User' }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">Knowledge Base Scope</span>
          <strong class="stat-value">{{ kbLabel }}</strong>
        </article>
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
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isSuperAdmin = computed(() => authStore.user?.role === 'super_admin')
const kbLabel = computed(() => (isSuperAdmin.value ? 'All workspaces' : authStore.kbId || 'Assigned workspace'))
</script>

<style scoped>
.user-profile {
  max-width: 1240px;
  width: 100%;
  margin: 0 auto;
}

.profile-hero {
  margin-bottom: 22px;
  padding: 24px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.14), transparent 34%),
    linear-gradient(135deg, #ffffff 0%, #f8fbff 58%, #f5f8fb 100%);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-lg);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 20px;
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
  margin-bottom: 8px;
}

.profile-name {
  margin: 0;
  font-size: 30px;
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--dm-text);
}

.profile-desc {
  margin: 0;
  color: var(--dm-text-muted);
  line-height: 1.7;
  font-size: 14px;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
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
  font-size: 20px;
  color: var(--dm-text);
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
  max-height: calc(100vh - 360px);
  min-height: 320px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 960px) {
  .profile-header {
    align-items: flex-start;
  }

  .profile-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .profile-hero,
  .documents-panel {
    padding: 18px;
  }

  .profile-header {
    flex-direction: column;
  }

  .profile-name {
    font-size: 26px;
  }
}
</style>
