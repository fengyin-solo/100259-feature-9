<template>
  <div class="completion-panel">
    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">应考核人数</span>
        <strong class="stat-value">{{ summary.total }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">合格 / 不合格</span>
        <strong class="stat-value">{{ summary.passed }} / {{ summary.failed }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">未考核</span>
        <strong class="stat-value stat-warn">{{ summary.pending }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">完成率{{ periodLabel ? `（${periodLabel}）` : '' }}</span>
        <strong class="stat-value">{{ rateText(summary.completionRate) }}</strong>
      </article>
    </div>

    <p v-if="loading" class="page-foot">完成情况加载中…</p>

    <table v-else class="data-table completion-table">
      <thead>
        <tr>
          <th class="col-drill"></th>
          <th>班组</th>
          <th>应考核</th>
          <th>合格</th>
          <th>不合格</th>
          <th>未考核</th>
          <th>缺口人数</th>
          <th>完成率</th>
          <th>信息缺失</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="team in teams" :key="team.班组">
          <tr
            class="team-row"
            :class="{ 'is-expanded': isExpanded(team) }"
            @click="toggle(team)"
          >
            <td class="col-drill">
              <span class="drill-arrow" :class="{ open: isExpanded(team) }">▶</span>
            </td>
            <td class="team-name">
              {{ team.班组 }}
              <span v-if="team.total === 0" class="tag tag-muted">本期无台账</span>
            </td>
            <td>{{ team.total }}</td>
            <td class="num-pass">{{ team.passed }}</td>
            <td>
              <span :class="team.failed > 0 ? 'num-fail' : ''">{{ team.failed }}</span>
            </td>
            <td>
              <span :class="team.pending > 0 ? 'num-pending' : ''">{{ team.pending }}</span>
            </td>
            <td>
              <strong :class="team.gap > 0 ? 'num-fail' : ''">{{ team.gap }}</strong>
            </td>
            <td>{{ rateText(team.completionRate) }}</td>
            <td class="missing-cell">
              <span v-if="team.missingInstructor > 0" class="tag tag-missing">
                缺讲师 {{ team.missingInstructor }}
              </span>
              <span v-if="team.missingMethod > 0" class="tag tag-missing">
                缺考核方式 {{ team.missingMethod }}
              </span>
              <span v-if="team.missingInstructor === 0 && team.missingMethod === 0" class="tag tag-ok">
                齐全
              </span>
            </td>
          </tr>
          <tr v-if="isExpanded(team)" class="member-row">
            <td></td>
            <td colspan="8">
              <table class="member-table">
                <thead>
                  <tr>
                    <th>姓名</th>
                    <th>培训编号</th>
                    <th>培训主题</th>
                    <th>培训日期</th>
                    <th>培训讲师</th>
                    <th>考核方式</th>
                    <th>考核结果</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="member in team.members" :key="member.id">
                    <td>{{ member.培训对象 }}</td>
                    <td>{{ member.培训编号 }}</td>
                    <td>{{ member.培训主题 ?? '—' }}</td>
                    <td>{{ member.培训日期 ?? '—' }}</td>
                    <td :class="{ 'cell-missing': isMissing(member, '培训讲师') }">
                      {{ member.培训讲师 || '未填写' }}
                    </td>
                    <td :class="{ 'cell-missing': isMissing(member, '考核方式') }">
                      {{ member.考核方式 || '未填写' }}
                    </td>
                    <td>
                      <span class="tag" :class="resultClass(member.考核结果)">
                        {{ member.考核结果 }}
                      </span>
                      <span
                        v-for="field in member.missingInfo"
                        :key="field"
                        class="tag tag-missing"
                      >缺{{ field }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
        </template>
        <tr v-if="!teams.length">
          <td colspan="9" class="empty-state">该统计周期暂无技能培训记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>
        排序口径：不合格 + 未考核缺口大的班组排在前面；展开后不合格与未考核的人排在前面。
      </span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { fetchJson } from '@/api/client'
import { useTrainingViewStore } from '@/stores/trainingView'

import type { CompletionResponse, TrainingMember, TrainingTeam } from './types'

const props = defineProps<{ period: string }>()
const emit = defineEmits<{
  periods: [items: string[]]
  periodLabel: [label: string]
}>()

const store = useTrainingViewStore()
const teams = ref<TrainingTeam[]>([])
const loading = ref(false)
const errorMessage = ref('')

const summary = ref({
  total: 0,
  passed: 0,
  failed: 0,
  pending: 0,
  assessed: 0,
  gap: 0,
  missingInfo: 0,
  completionRate: null as number | null,
})
const periodLabel = ref('')

function rateText(rate: number | null): string {
  // null 表示该范围没有任何培训/考核记录，必须显示“暂无”，不能清成 0%
  if (rate === null || rate === undefined) {
    return '暂无'
  }
  return `${(rate * 100).toFixed(1)}%`
}

function isExpanded(team: TrainingTeam): boolean {
  return store.expandedTeams.includes(team.班组)
}

function toggle(team: TrainingTeam) {
  store.toggleTeam(team.班组)
}

function isMissing(member: TrainingMember, field: string): boolean {
  return member.missingInfo.includes(field)
}

function resultClass(result: TrainingMember['考核结果']): string {
  if (result === '不合格') {
    return 'tag-fail'
  }
  if (result === '未考核') {
    return 'tag-pending'
  }
  return 'tag-pass'
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const query = props.period === 'all' ? 'period=all' : `period=${encodeURIComponent(props.period)}`
    const data = await fetchJson<CompletionResponse>(`/api/training/completion?${query}`)
    teams.value = data.teams ?? []
    summary.value = data.summary
    periodLabel.value = data.period ?? '全部周期'
    emit('periods', data.periods ?? [])
    emit('periodLabel', periodLabel.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '完成情况读取失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.period, load)

onMounted(load)
</script>
