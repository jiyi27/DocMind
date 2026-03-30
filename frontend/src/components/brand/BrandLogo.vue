<template>
  <div class="brand-logo" :class="[layoutClass, toneClass]">
    <div class="mark-shell" :class="sizeClass" aria-hidden="true">
      <img
        v-if="resolvedLogoPath"
        :src="resolvedLogoPath"
        :alt="`${brandName} logo`"
        class="brand-mark brand-mark-image"
      />
      <svg
        v-else
        viewBox="0 0 88 88"
        class="brand-mark"
        role="img"
        :aria-label="`${brandName} logo`"
      >
        <defs>
          <linearGradient id="brand-mark-gradient" x1="12%" y1="10%" x2="86%" y2="90%">
            <stop offset="0%" stop-color="#0f3d56" />
            <stop offset="52%" stop-color="#14b8a6" />
            <stop offset="100%" stop-color="#7dd3fc" />
          </linearGradient>
        </defs>
        <rect x="8" y="8" width="72" height="72" rx="22" fill="url(#brand-mark-gradient)" />
        <path
          d="M61 25c-8.8-3.9-19.7-2.5-27.2 3.5-5.4 4.4-8.8 11.2-8.8 18.1 0 9.3 6.1 16.1 15.5 16.1 8.2 0 14.4-4.6 18.5-10.9 1.3-2 3.1-3.2 5.8-3.2h3.5"
          fill="none"
          stroke="#ffffff"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="6.5"
        />
        <path
          d="M26 43.8c2.7-4.9 8.1-8.2 14.4-8.2 5.7 0 10.3 2.2 13.8 6"
          fill="none"
          stroke="rgba(255,255,255,0.78)"
          stroke-linecap="round"
          stroke-width="4.4"
        />
        <circle cx="58.5" cy="33" r="4.6" fill="#dffcff" />
        <circle cx="65.4" cy="49.1" r="3.8" fill="#dffcff" />
        <circle cx="45.2" cy="56.5" r="3.6" fill="#dffcff" />
      </svg>
    </div>

    <div v-if="showWordmark" class="wordmark">
      <div class="brand-name">
        <span class="brand-name-text">{{ brandName }}</span>
      </div>
      <p v-if="tagline" class="brand-tagline">{{ tagline }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { branding } from '@/config/branding'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
  },
  stacked: {
    type: Boolean,
    default: false,
  },
  showWordmark: {
    type: Boolean,
    default: true,
  },
  tagline: {
    type: String,
    default: '',
  },
  tone: {
    type: String,
    default: 'default',
  },
})

const sizeClass = computed(() => `is-${props.size}`)
const layoutClass = computed(() => (props.stacked ? 'is-stacked' : 'is-inline'))
const toneClass = computed(() => `tone-${props.tone}`)
const brandName = computed(() => branding.name)
const resolvedLogoPath = computed(() => branding.logoPath)
</script>

<style scoped>
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  color: var(--dm-text);
}

.brand-logo.is-stacked {
  flex-direction: column;
  text-align: center;
}

.mark-shell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 24px;
  box-shadow: 0 18px 36px rgba(15, 61, 86, 0.16);
}

.brand-mark {
  display: block;
  width: 100%;
  height: 100%;
}

.brand-mark-image {
  object-fit: contain;
  padding: 3px;
}

.is-sm {
  width: 38px;
  height: 38px;
  border-radius: 12px;
}

.is-md {
  width: 56px;
  height: 56px;
}

.is-lg {
  width: 80px;
  height: 80px;
}

.wordmark {
  min-width: 0;
}

.brand-name {
  font-size: 28px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.brand-name-text {
  color: #0f3d56;
}

.brand-tagline {
  margin: 8px 0 0;
  color: var(--dm-text-soft);
  font-size: 13px;
  line-height: 1.5;
  max-width: 28ch;
}

.tone-muted .mark-shell {
  box-shadow: 0 12px 24px rgba(15, 61, 86, 0.12);
}

.tone-muted .brand-name {
  font-size: 20px;
}

.tone-muted .brand-tagline {
  margin-top: 4px;
  font-size: 12px;
}
</style>
