<template>
  <div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
        Sign in to your account
      </h2>
      <p class="mt-2 text-center text-sm text-gray-600">
        Or
        <router-link to="/register" class="font-medium text-indigo-600 hover:text-indigo-500">
          register a new account
        </router-link>
      </p>
    </div>
    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
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
              class="w-full" 
              native-type="submit" 
              :loading="isLoading"
              style="width: 100%; height: 2.5rem;"
            >
              Sign in
            </el-button>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
        
        // Save the token to Pinia store (which also persists to localStorage)
        authStore.setAuth(response.access_token)
        
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
