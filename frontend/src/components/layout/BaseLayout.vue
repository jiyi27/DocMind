<template>
  <el-container class="base-layout">
    <AppHeader />
    <el-main class="main-content">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
</script>

<style scoped>
.base-layout {
  min-height: 100vh;
  background-color: #f5f7fa;
  flex-direction: column;
}

.main-content {
  padding: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
