<template>
  <div class="auth-shell">
    <div class="auth-background auth-background-primary" />
    <div class="auth-background auth-background-secondary" />

    <div class="auth-layout">
      <section class="auth-brand-panel">
        <BrandLogo
          size="lg"
          stacked
          tagline="Build a shared workspace for documents, search, and AI-assisted answers."
        />
        <div class="auth-brand-copy">
          <span class="auth-kicker">{{ brandKicker }}</span>
          <h1>Start your team knowledge base with a clear home for every document.</h1>
          <p>
            Create an account, join a workspace, and make knowledge easier to search, manage, and reuse.
          </p>
        </div>
      </section>

      <section class="auth-card">
        <div class="auth-card-header">
          <BrandLogo size="sm" tone="muted" tagline="Create your account" />
          <div>
            <h2 class="auth-title">Register an account</h2>
            <p class="auth-subtitle">
              Already have an account?
              <router-link to="/login" class="auth-link">
                Sign in here
              </router-link>
            </p>
          </div>
        </div>

        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleRegister"
        >
          <el-form-item label="Username" prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="Choose a username"
              autocomplete="username"
            />
          </el-form-item>

          <el-form-item label="Password" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="Choose a password"
              autocomplete="new-password"
              show-password
            />
          </el-form-item>

          <el-form-item label="Knowledge Base" prop="kb_id">
            <el-select
              v-model="registerForm.kb_id"
              placeholder="Select a knowledge base (optional)"
              :loading="loadingKbs"
              :disabled="loadingKbs || kbOptions.length === 0"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="kb in kbOptions"
                :key="kb.id"
                :label="kb.display_name"
                :value="kb.id"
              />
            </el-select>
          </el-form-item>

          <div class="mt-6">
            <el-button
              type="primary"
              class="w-full auth-submit"
              native-type="submit"
              :loading="isLoading"
            >
              Register
            </el-button>
          </div>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BrandLogo from '@/components/brand/BrandLogo.vue'
import { branding } from '@/config/branding'
import { register } from '../api/auth'
import { getKbs } from '../api/kb'

const router = useRouter()
const brandKicker = `${branding.name} Workspace`

const registerFormRef = ref(null)
const isLoading = ref(false)
const loadingKbs = ref(false)
const kbOptions = ref([])

onMounted(async () => {
  loadingKbs.value = true
  try {
    const res = await getKbs()
    kbOptions.value = Array.isArray(res) ? res : []
  } catch {
    ElMessage.error('Failed to load knowledge bases')
  } finally {
    loadingKbs.value = false
  }
})

const registerForm = reactive({
  username: '',
  password: '',
  kb_id: ''
})

const rules = reactive({
  username: [
    { required: true, message: 'Please input your username', trigger: 'blur' },
    { min: 3, message: 'Length should be at least 3 characters', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please input your password', trigger: 'blur' },
    { min: 6, message: 'Length should be at least 6 characters', trigger: 'blur' }
  ]
})

const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      isLoading.value = true
      try {
        const payload = {
          username: registerForm.username,
          password: registerForm.password
        }
        
        // Add kb_id if selected
        if (registerForm.kb_id) {
          payload.kb_id = registerForm.kb_id
        }

        await register(payload)
        
        ElMessage.success('Registration successful. Please login.')
        
        // Redirect to login page after successful registration
        router.push('/login')
      } catch (error) {
        // Error is already handled by the HTTP interceptor
        // but we log here just in case
        console.error('Registration failed:', error)
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
  right: -70px;
  width: 320px;
  height: 320px;
  background: rgba(20, 184, 166, 0.14);
}

.auth-background-secondary {
  left: -80px;
  bottom: -110px;
  width: 360px;
  height: 360px;
  background: rgba(125, 211, 252, 0.18);
}

.auth-layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 490px);
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
  font-size: clamp(2.1rem, 3.8vw, 3.7rem);
  line-height: 1.05;
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
}
</style>
