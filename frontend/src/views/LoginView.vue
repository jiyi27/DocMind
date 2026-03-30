<template>
  <div class="auth-shell">
    <div class="auth-background auth-background-primary" />
    <div class="auth-background auth-background-secondary" />

    <div class="auth-layout">
      <section class="auth-brand-panel">
        <BrandLogo
          size="lg"
          stacked
          tagline="AI knowledge workspace for teams, documents, and answers."
        />
        <div class="auth-brand-copy">
          <span class="auth-kicker">Knowledge Base Platform</span>
          <h1>Find the right answer without digging through scattered docs.</h1>
          <p>
            Centralize your team knowledge, search faster, and chat with the context that matters.
          </p>
        </div>
        <div class="auth-feature-strip">
          <span>Semantic search</span>
          <span>Workspace access</span>
          <span>Document chat</span>
        </div>
      </section>

      <section class="auth-card">
        <div class="auth-card-header">
          <BrandLogo size="sm" tone="muted" tagline="Sign in to continue" />
          <div>
            <h2 class="auth-title">Welcome back</h2>
            <p class="auth-subtitle">
              Or
              <router-link to="/register" class="auth-link">
                register a new account
              </router-link>
            </p>
          </div>
        </div>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <el-form-item label="Username" prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="Enter your username"
              autocomplete="username"
            />
          </el-form-item>

          <el-form-item label="Password" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="Enter your password"
              autocomplete="current-password"
              show-password
            />
          </el-form-item>

          <div class="mt-6">
            <el-button
              type="primary"
              class="w-full auth-submit"
              native-type="submit"
              :loading="isLoading"
            >
              Sign in
            </el-button>
          </div>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BrandLogo from '@/components/brand/BrandLogo.vue'
import { useAuthStore } from '../stores/auth'
import { login } from '../api/auth'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const isLoading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [
    { required: true, message: 'Please input your username', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please input your password', trigger: 'blur' }
  ]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      isLoading.value = true
      try {
        const response = await login({
          username: loginForm.username,
          password: loginForm.password
        })
        
        // Save the token, super admin flag, userInfo, kb_id and role to Pinia store (persists to localStorage)
        authStore.setAuth(response.access_token, response.is_super_admin === true, { username: response.username }, response.kb_id, response.role)
        
        ElMessage.success('Login successful')
        
        // Redirect to dashboard after successful login
        router.push('/')
      } catch (error) {
        // Error is already handled by the HTTP interceptor
        // but we log here just in case
        console.error('Login failed:', error)
      } finally {
        isLoading.value = false
      }
    }
  })
}
</script>

<style scoped>
.auth-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(20, 184, 166, 0.12), transparent 30%),
    linear-gradient(180deg, #f5fbfd 0%, #eef5f8 48%, #f8fafc 100%);
}

.auth-background {
  position: absolute;
  border-radius: 999px;
  filter: blur(20px);
  pointer-events: none;
}

.auth-background-primary {
  top: -120px;
  left: -60px;
  width: 320px;
  height: 320px;
  background: rgba(20, 184, 166, 0.16);
}

.auth-background-secondary {
  right: -80px;
  bottom: -120px;
  width: 380px;
  height: 380px;
  background: rgba(125, 211, 252, 0.18);
}

.auth-layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 460px);
  align-items: center;
  gap: 32px;
  width: 100%;
  max-width: 1180px;
  min-height: calc(100vh - 56px);
  margin: 0 auto;
}

.auth-brand-panel {
  padding: 28px 12px 28px 6px;
}

.auth-brand-copy {
  margin-top: 28px;
  max-width: 560px;
}

.auth-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(15, 61, 86, 0.08);
  color: #0f3d56;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-brand-copy h1 {
  margin: 18px 0 14px;
  color: #0f172a;
  font-size: clamp(2.3rem, 4vw, 4rem);
  line-height: 1.02;
  font-weight: 800;
  letter-spacing: -0.05em;
}

.auth-brand-copy p {
  margin: 0;
  max-width: 48ch;
  color: #475569;
  font-size: 17px;
  line-height: 1.7;
}

.auth-feature-strip {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 28px;
}

.auth-feature-strip span {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #0f3d56;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
}

.auth-card {
  width: 100%;
  box-sizing: border-box;
  padding: 28px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(18px);
}

.auth-card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.auth-title {
  margin: 0;
  color: var(--dm-text);
  font-size: 28px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.auth-subtitle {
  margin: 8px 0 0;
  color: var(--dm-text-soft);
  font-size: 14px;
}

.auth-link {
  color: #0f8f85;
  font-weight: 700;
  text-decoration: none;
}

.auth-link:hover {
  color: #0f3d56;
}

.auth-submit {
  width: 100%;
  height: 2.8rem;
}

@media (max-width: 980px) {
  .auth-shell {
    padding: 20px 16px;
  }

  .auth-layout {
    grid-template-columns: 1fr;
    min-height: auto;
    padding: 32px 0;
  }

  .auth-brand-panel {
    padding: 0;
    text-align: center;
  }

  .auth-brand-copy {
    margin-right: auto;
    margin-left: auto;
  }

  .auth-feature-strip {
    justify-content: center;
  }
}
</style>
