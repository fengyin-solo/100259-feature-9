<template>
  <section class="page" data-module="training">
    <header class="page-head">
      <div>
        <h2>技能培训管理</h2>
        <p class="page-desc">按班组查看培训完成情况与考核结果分布，可下钻到人；台账与完成视图共用同一套完成率口径。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记培训记录</button>
        <button class="btn" type="button" @click="exportRows">导出技能培训清单</button>
      </div>
    </header>

    <div class="tab-bar" role="tablist">
      <button
        class="tab-btn"
        :class="{ active: store.tab === 'completion' }"
        type="button"
        role="tab"
        @click="store.setTab('completion')"
      >
        完成情况
      </button>
      <button
        class="tab-btn"
        :class="{ active: store.tab === 'ledger' }"
        type="button"
        role="tab"
        @click="store.setTab('ledger')"
      >
        培训台账
      </button>

      <label class="period-picker">
        <span>统计周期</span>
        <select :value="store.period" @change="onPeriodChange">
          <option value="latest">最新周期</option>
          <option v-for="item in periods" :key="item" :value="item">{{ item }}</option>
          <option value="all">全部周期</option>
        </select>
      </label>
    </div>

    <CompletionPanel
      v-if="store.tab === 'completion'"
      :period="store.period"
      @periods="onPeriods"
      @period-label="onPeriodLabel"
    />
    <LedgerPanel v-else :period="store.period" :period-label="periodLabel" />

    <p v-if="errorMessage" class="page-foot error-text">{{ errorMessage }}</p>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

import { fetchJson } from '@/api/client'
import { useTrainingViewStore } from '@/stores/trainingView'

import CompletionPanel from './CompletionPanel.vue'
import LedgerPanel from './LedgerPanel.vue'

const store = useTrainingViewStore()
const errorMessage = ref('')
const periods = ref<string[]>([])
const periodLabel = ref(store.period === 'all' ? '全部周期' : '')

function saveScroll() {
  store.saveScroll(window.scrollY)
}

function syncPeriodLabel() {
  if (store.period === 'all') {
    periodLabel.value = '全部周期'
  } else if (store.period === 'latest') {
    periodLabel.value = periods.value[0] ?? ''
  } else {
    periodLabel.value = store.period
  }
}

function onPeriods(items: string[]) {
  periods.value = items
  if (!periodLabel.value || store.period === 'latest') {
    syncPeriodLabel()
  }
}

function onPeriodLabel(label: string) {
  periodLabel.value = label
}

function onPeriodChange(event: Event) {
  store.setPeriod((event.target as HTMLSelectElement).value)
  syncPeriodLabel()
}

function openCreate() {
  errorMessage.value = '培训记录登记入口尚未接入审批流'
}

function exportRows() {
  const query = store.period === 'all' ? 'period=all' : `period=${encodeURIComponent(store.period)}`
  window.open(`/api/training/export?${query}`, '_blank')
}

onMounted(async () => {
  if (store.scrollY) {
    window.scrollTo(0, store.scrollY)
  }
  window.addEventListener('scroll', saveScroll, { passive: true })
  try {
    const data = await fetchJson<{ periods: string[] }>('/api/training/periods')
    onPeriods(data.periods ?? [])
  } catch {
    // 周期选项只是辅助，拉取失败不阻塞两个面板各自的数据请求
  }
})

onUnmounted(() => {
  saveScroll()
  window.removeEventListener('scroll', saveScroll)
})
</script>
