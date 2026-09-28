import { defineStore } from 'pinia'

/**
 * 培训完成情况视图的临时状态。
 *
 * 只放在内存 store 里、不进 localStorage：从下钻视图返回台账（或跳到别的页面再回来）
 * 后，统计周期、已展开的班组范围与上次滚动位置都要保留；切换统计周期时只重新拉数、
 * 重新排序，已经展开的班组仍然保持展开——这些都靠 expanded 集合跨周期不清空来保证。
 */
export const useTrainingCompletionStore = defineStore('training-completion', {
  state: () => ({
    /** 当前统计周期 YYYY-MM，空串表示全部周期；台账页与下钻视图共用同一个值。 */
    period: '2026-09',
    /** 已展开的班组名集合：换周期只重排，不清这个集合。 */
    expanded: [] as string[],
    /** 上次浏览到的滚动位置，从台账返回后恢复到原来看的班组范围。 */
    scrollTop: 0,
  }),
  actions: {
    setPeriod(value: string) {
      // 周期变化会让班组顺序跟着变，但展开集合刻意保留，不重新折叠。
      this.period = value
    },
    toggle(team: string) {
      if (this.expanded.includes(team)) {
        this.expanded = this.expanded.filter((item) => item !== team)
      } else {
        this.expanded = [...this.expanded, team]
      }
    },
    isExpanded(team: string) {
      return this.expanded.includes(team)
    },
    saveScroll(top: number) {
      this.scrollTop = top
    },
  },
})
