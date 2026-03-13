import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getKbs, getKbDetail, createKb, deleteKb } from '@/api/kb'
import { ElMessage } from 'element-plus'

export const useKbStore = defineStore('kb', () => {
    // State
    const kbList = ref([])
    const currentKb = ref(null)
    const loading = ref(false)

    // Getters
    const kbCount = computed(() => kbList.value.length)

    // Actions
    async function fetchKbs() {
        loading.value = true
        try {
            const data = await getKbs()
            kbList.value = data
        } catch (err) {
            // Error already handled by http interceptor
        } finally {
            loading.value = false
        }
    }

    async function fetchKbDetail(kbId) {
        loading.value = true
        try {
            const data = await getKbDetail(kbId)
            currentKb.value = data
            return data
        } catch (err) {
            // Error already handled by http interceptor
        } finally {
            loading.value = false
        }
    }

    async function addKb(formData) {
        const data = await createKb(formData)
        kbList.value.unshift(data)
        ElMessage.success('知识库创建成功')
        return data
    }

    async function removeKb(kbId) {
        await deleteKb(kbId)
        kbList.value = kbList.value.filter((kb) => kb.id !== kbId)
        if (currentKb.value?.id === kbId) {
            currentKb.value = null
        }
        ElMessage.success('知识库已删除')
    }

    function setCurrentKb(kb) {
        currentKb.value = kb
    }

    function clearKbs() {
        kbList.value = []
        currentKb.value = null
    }

    return {
        kbList,
        currentKb,
        loading,
        kbCount,
        fetchKbs,
        fetchKbDetail,
        addKb,
        removeKb,
        setCurrentKb,
        clearKbs,
    }
})
