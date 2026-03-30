<template>
  <div class="my-documents-view">
    <section class="page-toolbar">
      <div>
        <div class="toolbar-title-row">
          <h1 class="page-title">My Documents</h1>
          <el-tag type="info" effect="plain" round>Personal Uploads</el-tag>
        </div>
        <p class="page-desc">Everything you uploaded across the workspaces you can access, in one dedicated page.</p>
      </div>
      <el-button plain @click="goToProfile">Back to Profile</el-button>
    </section>

    <section class="documents-shell">
      <div class="doc-list-wrap">
        <DocumentList mode="profile" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import DocumentList from '@/components/ingestion/DocumentList.vue'

const router = useRouter()

function goToProfile() {
  router.push({ name: 'UserProfile' })
}
</script>

<style scoped>
.my-documents-view {
  max-width: 1160px;
  width: 100%;
  margin: 0 auto;
  padding-top: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 2px;
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

.page-desc {
  margin: 10px 0 0;
  font-size: 14px;
  color: var(--dm-text-soft);
}

.documents-shell {
  padding: 20px 24px 24px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--dm-border);
  box-shadow: var(--dm-shadow-md);
}

.doc-list-wrap {
  min-height: 320px;
  max-height: calc(100vh - 320px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 720px) {
  .page-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .documents-shell {
    padding: 18px;
    border-radius: 22px;
  }
}
</style>
