<template>
  <section class="page" data-module="training-completion">
    <header class="page-head">
      <div>
        <h2>培训完成情况 · 按班组下钻</h2>
        <p class="page-desc">
          不合格与未考核缺口大的班组排在前面；点开班组可展开到每个人，不合格与未考核的成员排在前面。
          完成率与台账统计卡同源，均按「合格 / 有考核记录人数」计算。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/training">返回培训台账</RouterLink>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in statCards" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="period-bar">
      <label>
        <span>统计周期</span>
        <select :value="completionStore.period" @change="onPeriodChange">
          <option value="">全部周期</option>
          <option v-for="item in payload?.periods ?? []" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <span class="legend">
        <span class="tag tag-danger">不合格</span>
        <span class="tag tag-warning">未考核</span>
        <span class="tag tag-success">合格</span>
        <span class="tag tag-missing">讲师/考核方式缺失</span>
        <span>无考核记录的班组完成率显示「暂无」，不计 0%</span>
      </span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </div>

    <table class="drill-table">
      <thead>
        <tr>
          <th style="width: 190px;">班组</th>
          <th style="width: 80px;">台账人数</th>
          <th style="width: 200px;">考核结果分布</th>
          <th style="width: 190px;">培训完成率</th>
          <th style="width: 110px;">缺口(不合格+未考核)</th>
          <th>资料缺失</th>
        </tr>
      </thead>
      <tbody v-if="payload">
        <template v-for="team in payload.teams" :key="team.team">
          <tr class="team-row" @click="toggleTeam(team.team)">
            <td>
              <span :class="['expand-icon', { 'is-open': completionStore.isExpanded(team.team) }]">▶</span>
              <strong>{{ team.team }}</strong>
              <span v-if="team.total === 0" class="tag tag-muted" style="margin-left:6px;">本周期暂无记录</span>
            </td>
            <td>{{ team.total }}</td>
            <td>
              <span v-if="team.examined === 0 && team.total > 0" class="na-text">暂无考核记录</span>
              <span v-else-if="team.total === 0" class="na-text">暂无</span>
              <span v-else class="cell-counts">
                <span class="count-pill count-fail">不合格 {{ team.fail }}</span>
                <span class="count-pill count-pending">未考核 {{ team.pending }}</span>
                <span class="count-pill count-pass">合格 {{ team.pass }}</span>
              </span>
            </td>
            <td>
              <span v-if="team.completionRate === null" class="na-text">暂无</span>
              <span v-else class="rate-bar">
                <span class="rate-track">
                  <span
                    :class="['rate-fill', { 'is-low': team.completionRate < 60 }]"
                    :style="{ width: `${Math.max(team.completionRate, 2)}%` }"
                  ></span>
                </span>
                <span>{{ team.completionRate }}%</span>
              </span>
            </td>
            <td>
              <span :class="['tag', team.gap > 0 ? 'tag-danger' : 'tag-success']">{{ team.gap }} 人</span>
            </td>
            <td>
              <span v-if="team.missingLecturer" class="tag tag-missing">讲师缺失 {{ team.missingLecturer }} 人</span>
              <span v-if="team.missingExamMethod" class="tag tag-missing" style="margin-left:4px;">考核方式缺失 {{ team.missingExamMethod }} 人</span>
              <span v-if="!team.missingLecturer && !team.missingExamMethod && team.total > 0">—</span>
              <span v-else-if="team.total === 0" class="na-text">—</span>
            </td>
          </tr>
          <template v-if="completionStore.isExpanded(team.team)">
            <tr v-if="team.total === 0" class="member-row">
              <td colspan="6" class="empty-state">
                {{ team.team }}在{{ periodLabel }}没有培训台账记录，无法展开到人员
              </td>
            </tr>
            <tr v-for="member in team.members" :key="String(member.id)" class="member-row">
              <td style="padding-left: 32px;">
                <span class="expand-icon" style="visibility:hidden;">▶</span>
                {{ member.name }}
                <span class="na-text" style="margin-left:6px;">{{ member.trainingNo }}</span>
              </td>
              <td class="na-text">{{ member.date }}</td>
              <td>
                <span :class="['tag', memberResultClass(member.result)]">{{ member.result }}</span>
                <span v-if="member.examResultRaw" class="na-text" style="margin-left:6px;">原始：{{ member.examResultRaw }}</span>
              </td>
              <td>
                <span class="na-text">讲师：</span>
                <template v-if="member.lecturer">{{ member.lecturer }}</template>
                <span v-else class="tag tag-missing">讲师缺失</span>
              </td>
              <td>
                <span class="na-text">考核方式：</span>
                <template v-if="member.examMethod">{{ member.examMethod }}</template>
                <span v-else class="tag tag-missing">考核方式缺失</span>
              </td>
              <td class="na-text">内容：{{ member.topic }}</td>
            </tr>
          </template>
        </template>
        <tr v-if="!payload.teams.length">
          <td colspan="6" class="empty-state">暂无任何班组的培训数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>
        {{ periodLabel }}共 {{ payload?.summary.total ?? 0 }} 人，
        已考核 {{ payload?.summary.examined ?? 0 }} 人，
        缺口 {{ payload?.summary.gap ?? 0 }} 人
      </span>
      <span class="legend">展开的班组在切换周期与返回台账后仍然保留</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { request } from '@/api/client'
import { useTrainingCompletionStore } from '@/stores/trainingCompletion'

type ResultKind = '合格' | '不合格' | '未考核'

interface Member {
  id: number
  name: string
  trainingNo: string
  topic: string
  date: string
  lecturer: string | null
  examMethod: string | null
  examResultRaw: string | null
  result: ResultKind
  status: string
  missingLecturer: boolean
  missingExamMethod: boolean
}

interface TeamSummary {
  team: string
  total: number
  pass: number
  fail: number
  pending: number
  examined: number
  gap: number
  completionRate: number | null
  missingLecturer: number
  missingExamMethod: number
  members: Member[]
}

interface PeriodOption {
  value: string
  label: string
}

interface CompletionPayload {
  period: string
  periods: PeriodOption[]
  summary: Omit<TeamSummary, 'team' | 'members'>
  teams: TeamSummary[]
}

const ENDPOINT = '/api/training/completion/teams'
const completionStore = useTrainingCompletionStore()
const payload = ref<CompletionPayload | null>(null)
const errorMessage = ref('')

const periodLabel = computed(() => {
  const current = completionStore.period
  if (!current) return '全部周期'
  const found = payload.value?.periods.find((item) => item.value === current)
  return found ? found.label : current
})

const statCards = computed(() => {
  const summary = payload.value?.summary
  const rate = summary?.completionRate
  return [
    { label: '台账人数', value: summary ? String(summary.total) : '—' },
    { label: '合格人数', value: summary ? String(summary.pass) : '—' },
    { label: '未考核人数', value: summary ? String(summary.pending) : '—' },
    {
      label: '培训完成率',
      value: rate === null || rate === undefined ? '暂无' : `${rate}%`,
    },
  ]
})

function memberResultClass(result: ResultKind): string {
  if (result === '合格') return 'tag-success'
  if (result === '不合格') return 'tag-danger'
  return 'tag-warning'
}

function toggleTeam(team: string) {
  completionStore.toggle(team)
  persistScroll()
}

function onPeriodChange(event: Event) {
  // 只改周期：后端按新周期重排班组顺序，但 expanded 集合不动，展开过的班组不折叠。
  completionStore.setPeriod((event.target as HTMLSelectElement).value)
  void reload()
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (completionStore.period) query.set('period', completionStore.period)
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) {
      throw new Error('培训完成情况读取失败')
    }
    payload.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '培训完成情况读取失败'
  }
}

function persistScroll() {
  completionStore.saveScroll(window.scrollY)
}

function restoreScroll() {
  // 返回本页时恢复到之前看的班组范围；DOM 更新后再滚动，避免定位失效。
  const top = completionStore.scrollTop
  if (top > 0) {
    window.requestAnimationFrame(() => window.scrollTo({ top }))
  }
}

onMounted(() => {
  window.addEventListener('scroll', persistScroll, { passive: true })
  void reload().then(restoreScroll)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', persistScroll)
})
</script>
