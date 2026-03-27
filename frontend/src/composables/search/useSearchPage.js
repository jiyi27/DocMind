import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { searchDocuments } from '@/api/search'

const TOP_K_OPTIONS = [5, 10, 20, 30, 50]
const DEFAULT_SUGGESTIONS = [
  'What are the latest onboarding steps?',
  'Find documents about SQLite optimization',
  'Where is the API error handling logic?',
]

export function useSearchPage() {
  const kbStore = useKbStore()
  const authStore = useAuthStore()

  const query = ref('')
  const lastQuery = ref('')
  const selectedKbName = ref('')
  const topK = ref(10)
  const state = ref('idle')
  const allResults = ref([])

  const isLoading = computed(() => state.value === 'loading')
  const selectedKbLabel = computed(() => {
    const selectedKb = kbStore.kbList.find((kb) => kb.name === selectedKbName.value)
    return selectedKb ? selectedKb.display_name || selectedKb.name : ''
  })

  function toPercent(score) {
    return `${Math.round(score * 100)}%`
  }

  function scoreColor(score) {
    if (score >= 0.75) return '#2563eb'
    if (score >= 0.5) return '#059669'
    return '#6b7280'
  }

  function pickDefaultKb() {
    if (selectedKbName.value || kbStore.kbList.length === 0) return

    const ownedKb = kbStore.kbList.find((kb) => String(kb.id) === String(authStore.kbId))
    selectedKbName.value = ownedKb?.name || kbStore.kbList[0]?.name || ''
  }

  function applySuggestion(suggestion) {
    query.value = suggestion
  }

  async function doSearch() {
    const normalizedQuery = query.value.trim()
    if (!normalizedQuery || !selectedKbName.value) return

    state.value = 'loading'
    lastQuery.value = normalizedQuery

    try {
      const data = await searchDocuments({
        query: normalizedQuery,
        kbName: selectedKbName.value,
        topK: topK.value,
      })
      allResults.value = data.results ?? []
      state.value = allResults.value.length > 0 ? 'results' : 'empty'
    } catch {
      allResults.value = []
      state.value = 'idle'
    }
  }

  function handleTopKChange() {
    if (state.value === 'results' || state.value === 'empty') {
      doSearch()
    }
  }

  watch(
    () => kbStore.kbList,
    () => {
      pickDefaultKb()
    },
    { deep: true },
  )

  onMounted(async () => {
    if (kbStore.kbList.length === 0) {
      await kbStore.fetchKbs()
    }
    pickDefaultKb()
  })

  return {
    query,
    lastQuery,
    selectedKbName,
    topK,
    topKOptions: TOP_K_OPTIONS,
    state,
    allResults,
    suggestions: DEFAULT_SUGGESTIONS,
    isLoading,
    selectedKbLabel,
    toPercent,
    scoreColor,
    applySuggestion,
    handleTopKChange,
    doSearch,
  }
}
