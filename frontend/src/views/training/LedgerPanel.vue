<template>
  <div class="ledger-panel">
    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">未考核人数{{ periodSuffix }}</span>
        <strong class="stat-value stat-warn">{{ summary.pending }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">已考核人数{{ periodSuffix }}</span>
        <strong class="stat-value">{{ summary.assessed }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">完成率{{ periodSuffix }}</span>
        <strong class="stat-value">{{ rateText(summary.completionRate) }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">不合格人数{{ periodSuffix }}</span>
        <strong class="stat-value" :class="summary.failed > 0 ? 'stat-danger' : ''">{{ summary.failed }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>培训编号</span>
        <input v-model="keyword" placeholder="按培训编号检索" />
      </label>
      <label class="filter-item">
        <span>培训状态</span>
        <select v-model="status">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">
            <template v-if="column === '考核结果'">
              <span class="tag" :class="resultClass(row[column])">{{ displayResult(row[column]) }}</span>
            </template>
            <template v-else-if="column === '培训讲师' || column === '考核方式'">
              <span :class="{ 'cell-missing': isBlank(row[column]) }">
                {{ isBlank(row[column]) ? '未填写' : row[column] }}
              </span>
            </template>
            <template v-else>{{ row[column] ?? '—' }}</template>
          </td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无技能培训数据，可先登记培训记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条技能培训记录（完成率与「完成情况」页签同口径计算）</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { fetchJson, request } from '@/api/client'
import { useTrainingViewStore } from '@/stores/trainingView'

import type { TrainingSummary } from './types'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/training'
const columns = [
  '培训编号', '培训主题', '培训对象', '所属班组', '培训日期',
  '培训讲师', '考核方式', '考核结果', '培训状态',
]
const actions = ['组织培训', '组织考核', '归档']
const statuses = ['待培训', '培训中', '已考核', '已归档']

const props = defineProps<{ period: string; periodLabel: string }>()

const store = useTrainingViewStore()
const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref(store.ledgerKeyword)
const status = ref(store.ledgerStatus)

const summary = ref<TrainingSummary>({
  total: 0,
  passed: 0,
  failed: 0,
  pending: 0,
  assessed: 0,
  gap: 0,
  missingInfo: 0,
  completionRate: null,
})

const periodSuffix = computed(() => (props.periodLabel ? `（${props.periodLabel}）` : ''))

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || String(value).trim() === ''
}

function displayResult(value: unknown): string {
  const text = String(value ?? '').trim()
  return text === '合格' || text === '不合格' ? text : '未考核'
}

function resultClass(value: unknown): string {
  const text = displayResult(value)
  if (text === '不合格') {
    return 'tag-fail'
  }
  if (text === '未考核') {
    return 'tag-pending'
  }
  return 'tag-pass'
}

function rateText(rate: number | null): string {
  if (rate === null || rate === undefined) {
    return '暂无'
  }
  return `${(rate * 100).toFixed(1)}%`
}

function resetFilters() {
  keyword.value = ''
  status.value = ''
  store.setLedgerFilter('', '')
  void reload()
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('技能培训动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '技能培训操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  store.setLedgerFilter(keyword.value, status.value)
  const params = new URLSearchParams()
  if (props.period === 'all') {
    params.set('period', 'all')
  } else {
    params.set('period', props.period)
  }
  if (keyword.value) {
    params.set('keyword', keyword.value)
  }
  if (status.value) {
    params.set('status', status.value)
  }
  try {
    const payload = await fetchJson<{
      items: Row[]
      total: number
      summary: TrainingSummary
    }>(`${ENDPOINT}?${params.toString()}`)
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    if (payload.summary) {
      summary.value = payload.summary
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '技能培训列表读取失败'
  }
}

watch(() => props.period, () => void reload())

onMounted(reload)
</script>
