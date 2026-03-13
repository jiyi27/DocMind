<template>
  <div class="user-profile">
    <div class="page-header">
      <div class="page-title-wrap">
        <h1 class="page-title">My Profile</h1>
      </div>
    </div>

    <!-- User Info Card -->
    <el-card class="profile-card" shadow="never">
      <div class="profile-header">
        <el-avatar :size="64" class="profile-avatar">
          {{ userInitial }}
        </el-avatar>
        <div class="profile-details">
          <h2 class="profile-name">{{ username }}</h2>
          <div class="profile-meta">
            <el-tag v-if="isSuperAdmin" type="danger" size="small">Super Admin</el-tag>
            <el-tag v-else type="info" size="small">User</el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Uploaded Documents -->
    <div class="documents-section">
      <h3 class="section-title">My Uploaded Documents</h3>
      <DocumentList ref="docListRef" mode="profile" />
    </div>
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

</script>

<style scoped>
.user-profile {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin: 0;
}

.profile-card {
  margin-bottom: 32px;
  border-radius: 8px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 24px;
}

.profile-avatar {
  background-color: #409eff;
  color: #ffffff;
  font-size: 28px;
  font-weight: 600;
}

.profile-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-name {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.profile-meta {
  display: flex;
  gap: 8px;
}

.documents-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
</style>
