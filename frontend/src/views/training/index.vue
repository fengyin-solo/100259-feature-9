<template>
  <section class="page" data-module="training">
    <header class="page-head">
      <div>
        <h2>技能培训管理</h2>
        <p class="page-desc">维护培训记录，围绕培训编号、培训主题、所属班组、培训对象做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记培训记录</button>
        <RouterLink class="btn" to="/training/completion">培训完成情况（按班组下钻）</RouterLink>
        <button class="btn" type="button" @click="exportRows">导出技能培训清单</button>
      </div>
    </header>

    <!-- 统计卡与下钻视图取同一个汇总接口、同一套完成率口径，不会出现两个结论 -->
    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="period-bar">
      <label>
        <span>统计周期</span>
        <select v-model="completionStore.period" @change="reload">
          <option value="">全部周期</option>
          <option v-for="item in periods" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <span class="legend">统计卡按当前周期汇总；完成情况视图与本页保持同一周期。</span>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
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
          <td>{{ row['培训编号'] ?? '—' }}</td>
          <td>{{ row['培训主题'] ?? '—' }}</td>
          <td>{{ row['所属班组'] ?? '未划分班组' }}</td>
          <td>{{ row['培训对象'] ?? '—' }}</td>
          <td>{{ row['培训日期'] ?? '—' }}</td>
          <td>
            <span v-if="isBlank(row['培训讲师'])"><span class="tag tag-missing">讲师缺失</span></span>
            <template v-else>{{ row['培训讲师'] }}</template>
          </td>
          <td>
            <span v-if="isBlank(row['考核方式'])"><span class="tag tag-missing">考核方式缺失</span></span>
            <template v-else>{{ row['考核方式'] }}</template>
          </td>
          <td>
            <span :class="['tag', resultTagClass(row['考核结果'])]">{{ resultLabel(row['考核结果']) }}</span>
            <template v-if="!isBlank(row['考核结果'])">（{{ row['考核结果'] }}）</template>
          </td>
          <td>{{ row['培训状态'] ?? row['status'] ?? '—' }}</td>
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
          <td :colspan="columns.length + 1" class="empty-state">当前周期暂无技能培训数据，可切换统计周期或先登记培训记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条技能培训记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'
import { useTrainingCompletionStore } from '@/stores/trainingCompletion'

type Row = Record<string, string | number | null>
type ResultKind = '合格' | '不合格' | '未考核'

interface PeriodOption {
  value: string
  label: string
}

interface Summary {
  total: number
  pass: number
  fail: number
  pending: number
  completionRate: number | null
}

const ENDPOINT = '/api/training'
const columns = ["培训编号", "培训主题", "所属班组", "培训对象", "培训日期", "培训讲师", "考核方式", "考核结果", "培训状态"]
const actions = ["组织培训", "组织考核", "归档"]
const filterFields = ["培训编号", "培训主题", "培训对象"]

const completionStore = useTrainingCompletionStore()
const rows = ref<Row[]>([])
const total = ref(0)
const summary = ref<Summary | null>(null)
const periods = ref<PeriodOption[]>([])
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})

const stats = computed(() => {
  const data = summary.value
  const rate = data?.completionRate
  return [
    { label: '台账人数', value: data ? String(data.total) : '—' },
    { label: '未考核人数', value: data ? String(data.pending) : '—' },
    { label: '不合格人数', value: data ? String(data.fail) : '—' },
    { label: '培训完成率', value: rate === null || rate === undefined ? '暂无' : `${rate}%` },
  ]
})

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || String(value).trim() === ''
}

// 与后端 classify_result 同口径的展示映射；数字本身以后端汇总为准，这里只负责标签样式。
function classify(value: unknown): ResultKind {
  if (isBlank(value)) return '未考核'
  return String(value).trim() === '合格' ? '合格' : '不合格'
}

function resultTagClass(value: unknown): string {
  const kind = classify(value)
  return kind === '合格' ? 'tag-success' : kind === '不合格' ? 'tag-danger' : 'tag-warning'
}

function resultLabel(value: unknown): string {
  return classify(value)
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '培训记录登记入口尚未接入审批流'
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

async function loadPeriods() {
  try {
    const response = await request(`${ENDPOINT}/completion/periods`)
    if (!response.ok) return
    const payload = await response.json()
    periods.value = payload.periods ?? []
  } catch {
    // 周期清单加载失败不阻断台账，下拉框退化为只有「全部周期」
  }
}

async function loadSummary() {
  const query = new URLSearchParams()
  if (completionStore.period) query.set('period', completionStore.period)
  try {
    const response = await request(`${ENDPOINT}/completion/summary?${query.toString()}`)
    if (!response.ok) return
    summary.value = await response.json()
  } catch {
    summary.value = null
  }
}

async function reload() {
  errorMessage.value = ''
  const queryMap: Record<string, string> = { ...filters.value }
  if (completionStore.period) queryMap.period = completionStore.period
  const query = new URLSearchParams(queryMap).toString()
  try {
    const [listResponse] = await Promise.all([
      request(`${ENDPOINT}?${query}`),
      loadSummary(),
    ])
    if (!listResponse.ok) {
      throw new Error('培训记录列表读取失败')
    }
    const payload = await listResponse.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '技能培训列表读取失败'
  }
}

onMounted(() => {
  void loadPeriods()
  void reload()
})
</script>
