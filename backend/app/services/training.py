"""技能培训业务规则：状态流转、字段校验、筛选口径与完成情况聚合都收在这里。

完成率只有一套口径（见 classify_result / aggregate）：台账列表上方的统计卡
和「培训完成情况」下钻视图都从同一个聚合结果取数，保证两个页面不会算出两套结论。
"""
from __future__ import annotations

import re
from typing import Any

from app.store import store

MODULE = "training"
REQUIRED_FIELDS = ["培训编号", "培训主题", "培训对象", "所属班组"]
STATUS_ORDER = ["待培训", "培训中", "已考核", "已归档"]
ACTION_RULES = {"组织培训": "培训中", "组织考核": "已考核", "归档": "已归档"}
NEGATIVE_ACTIONS = []

# 考核结果的三档分类口径：合格、不合格、未考核（缺记录或空值都归到未考核）。
RESULT_PASS = "合格"
RESULT_FAIL = "不合格"
RESULT_PENDING = "未考核"
RESULT_ORDER = [RESULT_FAIL, RESULT_PENDING, RESULT_PASS]
# 除「合格」以外的已填写结果统一视为不合格（例如「不合格」「未参加」等）。
FAIL_MARKS = {"不合格", "未参加", "缺考"}

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _is_blank(value: Any) -> bool:
    return value is None or not str(value).strip()


def classify_result(value: Any) -> str:
    """把单条台账的考核结果归到合格 / 不合格 / 未考核三档。

    空值（没有考核记录）算未考核，不算不合格，也不算合格；
    已填写但非合格的结果（含「未参加」）算不合格，保证分母口径一致。
    """
    if _is_blank(value):
        return RESULT_PENDING
    text = str(value).strip()
    if text == RESULT_PASS:
        return RESULT_PASS
    if text in FAIL_MARKS:
        return RESULT_FAIL
    return RESULT_FAIL


def in_period(date_value: Any, period: str | None) -> bool:
    """判断培训日期是否落在统计周期（YYYY-MM）内；period 为空表示全部周期。"""
    if not period:
        return True
    return str(date_value or "")[:7] == period


def available_periods(rows: list[dict[str, Any]]) -> list[str]:
    """从台账里提取出现过的统计周期（年月），近的在前；脏日期不参与统计。"""
    months = {
        str(row.get("培训日期", ""))[:7]
        for row in rows
        if MONTH_PATTERN.match(str(row.get("培训日期", ""))[:7])
    }
    return sorted(months, reverse=True)


def _member_payload(row: dict[str, Any]) -> dict[str, Any]:
    result_kind = classify_result(row.get("考核结果"))
    return {
        "id": row.get("id"),
        "name": str(row.get("培训对象") or "").strip() or "未登记姓名",
        "trainingNo": row.get("培训编号"),
        "topic": row.get("培训主题"),
        "date": row.get("培训日期"),
        "lecturer": None if _is_blank(row.get("培训讲师")) else row.get("培训讲师"),
        "examMethod": None if _is_blank(row.get("考核方式")) else row.get("考核方式"),
        "examResultRaw": None if _is_blank(row.get("考核结果")) else row.get("考核结果"),
        "result": result_kind,
        "status": row.get("status"),
        # 讲师 / 考核方式缺失单独标出来，列表和班组行都靠这两个标记提示。
        "missingLecturer": _is_blank(row.get("培训讲师")),
        "missingExamMethod": _is_blank(row.get("考核方式")),
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """对给定台账行做唯一一次分档计数与完成率计算。

    完成率 = 合格人数 / 考核结果非空（有考核记录）的人数；
    没有任何考核记录时返回 None，由前端显示「暂无」，而不是清成 0%。
    """
    counts = {RESULT_PASS: 0, RESULT_FAIL: 0, RESULT_PENDING: 0}
    missing_lecturer = 0
    missing_exam_method = 0
    for row in rows:
        counts[classify_result(row.get("考核结果"))] += 1
        if _is_blank(row.get("培训讲师")):
            missing_lecturer += 1
        if _is_blank(row.get("考核方式")):
            missing_exam_method += 1
    examined = counts[RESULT_PASS] + counts[RESULT_FAIL]
    total = len(rows)
    completion_rate = round(counts[RESULT_PASS] * 100 / examined, 1) if examined else None
    return {
        "total": total,
        "pass": counts[RESULT_PASS],
        "fail": counts[RESULT_FAIL],
        "pending": counts[RESULT_PENDING],
        "examined": examined,
        "gap": counts[RESULT_FAIL] + counts[RESULT_PENDING],
        "completionRate": completion_rate,
        "missingLecturer": missing_lecturer,
        "missingExamMethod": missing_exam_method,
    }


def _team_sort_key(summary: dict[str, Any]) -> tuple[int, int, float, str]:
    """缺口（不合格+未考核）大的班组排前面；缺口相同看完成率（暂无视为最低），再看名称。

    本周期没有台账记录的班组一律沉底，避免把「暂无」误当成最大缺口排到最前。
    """
    if summary["total"] == 0:
        return (1, 0, 0.0, summary["team"])
    rate = summary["completionRate"]
    return (0, -int(summary["gap"]), rate if rate is not None else -1.0, summary["team"])


class TrainingService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        period: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("培训编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if period:
            rows = [row for row in rows if in_period(row.get("培训日期"), period)]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"培训记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于技能培训可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"培训记录已{action}"

    # ------------------------------------------------------------------
    # 完成情况视图：周期清单、总体汇总、班组下钻，全部共用 _aggregate 口径
    # ------------------------------------------------------------------
    def list_periods(self) -> list[dict[str, str]]:
        return [{"value": month, "label": f"{month[:4]}年{int(month[5:7])}月"}
                for month in available_periods(store.rows(MODULE))]

    def completion_overview(self, period: str | None = None) -> dict[str, Any]:
        """培训台账与下钻视图共用的总体完成情况（同一份聚合，不做第二套算法）。"""
        rows = store.rows(MODULE)
        if period:
            rows = [row for row in rows if in_period(row.get("培训日期"), period)]
        return {"period": period or "", **_aggregate(rows)}

    def completion_teams(self, period: str | None = None) -> dict[str, Any]:
        """按班组汇总完成情况，并带上每个班的成员明细供前端就地展开。"""
        all_rows = store.rows(MODULE)
        periods = available_periods(all_rows)
        if period and not MONTH_PATTERN.match(period):
            raise ValueError(f"统计周期「{period}」格式应为 YYYY-MM")
        rows = [row for row in all_rows if in_period(row.get("培训日期"), period)]

        team_rows: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            team = str(row.get("所属班组") or "").strip() or "未划分班组"
            team_rows.setdefault(team, []).append(row)

        # 全员花名册里出现过的班组都要列出：本周期零记录的班组显示「暂无」而不是消失。
        roster = {
            str(row.get("所属班组") or "").strip() or "未划分班组"
            for row in all_rows
        }
        teams: list[dict[str, Any]] = []
        for team in roster:
            member_rows = team_rows.get(team, [])
            members = [_member_payload(row) for row in member_rows]
            # 不合格与未考核的人排在成员列表前面，合格沉底；同档按培训日期、姓名。
            members.sort(key=lambda item: (
                RESULT_ORDER.index(item["result"]),
                str(item["date"] or ""),
                item["name"],
            ))
            summary = {"team": team, **_aggregate(member_rows)}
            summary["members"] = members
            teams.append(summary)

        teams.sort(key=_team_sort_key)
        return {
            "period": period or "",
            "periods": [{"value": month, "label": f"{month[:4]}年{int(month[5:7])}月"}
                        for month in periods],
            "summary": {"period": period or "", **_aggregate(rows)},
            "teams": teams,
        }
