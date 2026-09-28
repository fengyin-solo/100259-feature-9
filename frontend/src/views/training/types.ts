/** 技能培训完成情况视图的接口类型，与后端 services/training.py 的汇总口径保持一致。 */

export interface TrainingSummary {
  total: number
  passed: number
  failed: number
  pending: number
  assessed: number
  gap: number
  missingInfo: number
  /** 分母为 0（无培训记录）时为 null，前端显示“暂无”而不是 0% */
  completionRate: number | null
}

export interface TrainingMember {
  id: number
  培训编号: string
  培训对象: string
  所属班组: string
  培训主题: string | null
  培训日期: string | null
  培训讲师: string | null
  考核方式: string | null
  考核结果: '合格' | '不合格' | '未考核'
  培训状态: string | null
  missingInfo: string[]
  排序权重: number
}

export interface TrainingTeam extends TrainingSummary {
  班组: string
  missingInstructor: number
  missingMethod: number
  members: TrainingMember[]
}

export interface CompletionResponse {
  period: string | null
  periods: string[]
  summary: TrainingSummary
  teams: TrainingTeam[]
}
