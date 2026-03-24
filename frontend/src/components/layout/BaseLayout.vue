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
  height: 100%;
  background:
    radial-gradient(circle at top, rgba(59, 130, 246, 0.08), transparent 32%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  flex-direction: column;
  overflow: hidden;
}

.main-content {
  padding: 20px 24px 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  overflow-y: scroll;
  scrollbar-gutter: stable;
}
</style>
