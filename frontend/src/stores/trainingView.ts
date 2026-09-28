import { defineStore } from 'pinia'

/**
 * 技能培训页的交互状态：页签、统计周期、已展开班组与台账筛选条件。
 * 用 sessionStorage 持久化，路由离开再回来（“从视图返回”）时不重置已看过的范围；
 * 已展开的班组按班组名保存，切换统计周期只改数据排序，不会把它们重新折叠。
 */
const STORAGE_KEY = 'training-view-state'

export type TrainingTab = 'completion' | 'ledger'

interface PersistedState {
  tab: TrainingTab
  period: string
  expandedTeams: string[]
  ledgerKeyword: string
  ledgerStatus: string
  scrollY: number
}

function loadState(): Partial<PersistedState> {
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Partial<PersistedState>) : {}
  } catch {
    return {}
  }
}

export const useTrainingViewStore = defineStore('trainingView', {
  state: () => {
    const saved = loadState()
    return {
      tab: (saved.tab ?? 'completion') as TrainingTab,
      period: saved.period ?? 'latest',
      expandedTeams: saved.expandedTeams ?? [],
      ledgerKeyword: saved.ledgerKeyword ?? '',
      ledgerStatus: saved.ledgerStatus ?? '',
      scrollY: saved.scrollY ?? 0,
    }
  },
  actions: {
    persist() {
      const payload: PersistedState = {
        tab: this.tab,
        period: this.period,
        expandedTeams: this.expandedTeams,
        ledgerKeyword: this.ledgerKeyword,
        ledgerStatus: this.ledgerStatus,
        scrollY: this.scrollY,
      }
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    },
    setTab(tab: TrainingTab) {
      this.tab = tab
      this.persist()
    },
    setPeriod(period: string) {
      this.period = period
      this.persist()
    },
    toggleTeam(team: string) {
      const index = this.expandedTeams.indexOf(team)
      if (index >= 0) {
        this.expandedTeams.splice(index, 1)
      } else {
        this.expandedTeams.push(team)
      }
      this.persist()
    },
    setLedgerFilter(keyword: string, status: string) {
      this.ledgerKeyword = keyword
      this.ledgerStatus = status
      this.persist()
    },
    saveScroll(scrollY: number) {
      this.scrollY = scrollY
      this.persist()
    },
  },
})
