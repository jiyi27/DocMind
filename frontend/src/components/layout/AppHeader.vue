<template>
  <el-header class="app-header">
    <div class="header-left">
      <router-link to="/" class="brand">
        <el-icon class="logo-icon"><Reading /></el-icon>
        <span class="logo-text">SurfinDocMind</span>
      </router-link>
      <nav class="main-nav">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.name === item.name }"
        >
          {{ item.label }}
        </router-link>
      </nav>
    </div>
    <div class="header-right">
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32" class="user-avatar">
            {{ userInitial }}
          </el-avatar>
          <span class="username">{{ username }}</span>
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <el-tag v-if="isSuperAdmin" type="danger" size="small">Super Admin</el-tag>
              <el-tag v-else type="info" size="small">User</el-tag>
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              Sign Out
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Reading, ArrowDown, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isSuperAdmin = computed(() => authStore.user?.role === 'super_admin')
const navItems = [
  { name: 'Chat', label: 'Chat', to: '/chat' },
  { name: 'Dashboard', label: 'Knowledge Base', to: '/' },
  { name: 'UserProfile', label: 'Profile', to: '/profile' }
]

function handleCommand(command) {
  if (command === 'logout') {
    authStore.clearAuth()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 24px;
  height: 60px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  text-decoration: none;
}

.logo-icon {
  font-size: 24px;
  color: #409eff;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  letter-spacing: 0.5px;
}

.main-nav {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-link {
  color: #606266;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  padding: 6px 8px;
  border-radius: 6px;
  transition: background-color 0.2s, color 0.2s;
}

.nav-link:hover {
  background-color: #f5f7fa;
  color: #303133;
}

.nav-link.active {
  color: #409eff;
  background-color: rgba(64, 158, 255, 0.12);
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.user-avatar {
  background-color: #409eff;
  color: #ffffff;
  font-weight: 600;
  font-size: 14px;
}

.username {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}
</style>
