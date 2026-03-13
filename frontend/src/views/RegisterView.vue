<template>
  <div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
        Register an account
      </h2>
      <p class="mt-2 text-center text-sm text-gray-600">
        Already have an account?
        <router-link to="/login" class="font-medium text-indigo-600 hover:text-indigo-500">
          Sign in here
        </router-link>
      </p>
    </div>
    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
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

          <el-form-item label="Knowledge Base ID" prop="kb_id">
            <el-input 
              v-model="registerForm.kb_id" 
              placeholder="Enter your KB ID (optional)"
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
              Register
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
import { register } from '../api/auth'

const router = useRouter()

const registerFormRef = ref(null)
const isLoading = ref(false)

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
        
        // Add kb_id if provided
        if (registerForm.kb_id.trim()) {
          payload.kb_id = registerForm.kb_id.trim()
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
