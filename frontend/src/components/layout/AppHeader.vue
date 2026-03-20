<template>
  <el-header class="app-header-shell">
    <nav class="main-nav">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="item.to"
        class="nav-link"
        :class="{ active: route.name === item.name }"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </router-link>

      <el-dropdown trigger="click" @command="handleCommand">
        <button class="nav-link user-link" type="button">
          <el-avatar :size="24" class="user-avatar">
            {{ userInitial }}
          </el-avatar>
          <span class="username">{{ username }}</span>
          <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
        </button>
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
    </nav>
  </el-header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  ArrowDown,
  ChatRound,
  House,
  Search,
  SwitchButton,
  User,
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())
const isSuperAdmin = computed(() => authStore.user?.role === 'super_admin')
const navItems = [
  { name: 'Chat', label: 'Chat', to: '/chat', icon: ChatRound },
  { name: 'Dashboard', label: 'Knowledge Base', to: '/', icon: House },
  { name: 'Search', label: 'Search', to: '/search', icon: Search },
  { name: 'UserProfile', label: 'Profile', to: '/profile', icon: User },
]

function handleCommand(command) {
  if (command === 'logout') {
    authStore.clearAuth()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header-shell {
  display: flex;
  justify-content: center;
  height: 60px;
  padding: 10px 24px 6px;
  background: transparent;
}

.main-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid var(--dm-border);
  min-width: 0;
  max-width: 100%;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 10px;
  color: var(--dm-text-muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  transition: background-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.82);
  color: var(--dm-text);
}

.nav-link.active {
  background: #ffffff;
  color: var(--dm-primary);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.1);
}

.user-link {
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.user-avatar {
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  color: #ffffff;
  font-weight: 700;
}

.username {
  color: var(--dm-text);
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}

.dropdown-icon {
  color: var(--dm-text-soft);
}

@media (max-width: 1080px) {
  .app-header-shell {
    height: auto;
    padding-bottom: 8px;
  }

  .main-nav {
    overflow-x: auto;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .app-header-shell {
    padding: 12px 12px 6px;
  }

  .nav-link span {
    display: none;
  }
}
</style>
