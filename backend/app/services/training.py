"""技能培训业务规则：状态流转、字段校验、周期筛选与完成情况汇总口径都收在这里。

完成率只有一处计算实现（``_summarize``）：培训台账列表/导出的汇总与
``/api/training/completion`` 完成视图都调用它，避免台账与视图算出两套结论。
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from app.store import store

MODULE = "training"
REQUIRED_FIELDS = ["培训编号", "培训主题", "培训对象", "所属班组"]
OPTIONAL_FIELDS = ["培训日期", "培训讲师", "考核方式", "考核结果", "培训状态"]
STATUS_ORDER = ["待培训", "培训中", "已考核", "已归档"]
ACTION_RULES = {"组织培训": "培训中", "组织考核": "已考核", "归档": "已归档"}
NEGATIVE_ACTIONS = []

RESULT_PASS = "合格"
RESULT_FAIL = "不合格"
RESULT_PENDING = "未考核"
INFO_FIELDS = ["培训讲师", "考核方式"]
UNASSIGNED_TEAM = "未分配班组"


def _is_blank(value: Any) -> bool:
    """讲师/考核方式为空串或空值都视为缺失。"""
    return value is None or not str(value).strip()


def result_of(row: dict[str, Any]) -> str:
    """考核结果归一化：只认合格/不合格，其余（含空值）一律视为未考核。"""
    value = str(row.get("考核结果") or "").strip()
    if value == RESULT_PASS:
        return RESULT_PASS
    if value == RESULT_FAIL:
        return RESULT_FAIL
    return RESULT_PENDING


def period_of(row: dict[str, Any]) -> str:
    """培训日期截取到月，作为统计周期；无法解析的归入空周期。"""
    return str(row.get("培训日期") or "")[:7]


def available_periods() -> list[str]:
    """台账中出现过的统计周期，按时间倒序排列。"""
    periods = {period_of(row) for row in store.rows(MODULE) if period_of(row)}
    return sorted(periods, reverse=True)


def resolve_period(period: str | None) -> tuple[str | None, list[str]]:
    """把入参周期归一化：空或 latest 取台账最新周期；all 表示不按周期过滤。

    传入不存在的周期时回落到最新周期，并把可选周期一并返回给调用方。
    """
    periods = available_periods()
    latest = periods[0] if periods else None
    if period in (None, "", "latest"):
        return latest, periods
    if period == "all":
        return None, periods
    if period not in periods:
        return latest, periods
    return period, periods


def _rows_for_period(period: str | None) -> list[dict[str, Any]]:
    rows = store.rows(MODULE)
    if period is not None:
        rows = [row for row in rows if period_of(row) == period]
    return rows


def _missing_info(row: dict[str, Any]) -> list[str]:
    return [field for field in INFO_FIELDS if _is_blank(row.get(field))]


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """完成情况唯一口径：合格、不合格、未考核、完成率、缺口与信息缺失人数。

    分母为 0（该周期没有任何培训记录）时完成率返回 None，由前端显示“暂无”，
    不能把没有考核记录的情况直接清成 0%。
    """
    total = len(rows)
    passed = sum(1 for row in rows if result_of(row) == RESULT_PASS)
    failed = sum(1 for row in rows if result_of(row) == RESULT_FAIL)
    pending = sum(1 for row in rows if result_of(row) == RESULT_PENDING)
    assessed = passed + failed
    gap = failed + pending
    missing_info = sum(1 for row in rows if _missing_info(row))
    completion_rate = round(assessed / total, 4) if total else None
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "assessed": assessed,
        "gap": gap,
        "missingInfo": missing_info,
        "completionRate": completion_rate,
    }


def _member_view(row: dict[str, Any]) -> dict[str, Any]:
    """成员（人）明细：考核结果归一化，并单独标出讲师与考核方式缺失。"""
    result = result_of(row)
    missing = _missing_info(row)
    return {
        "id": row.get("id"),
        "培训编号": row.get("培训编号"),
        "培训对象": row.get("培训对象"),
        "所属班组": row.get("所属班组") or UNASSIGNED_TEAM,
        "培训主题": row.get("培训主题"),
        "培训日期": row.get("培训日期"),
        "培训讲师": row.get("培训讲师"),
        "考核方式": row.get("考核方式"),
        "考核结果": result,
        "培训状态": row.get("培训状态") or row.get("status"),
        "missingInfo": missing,
        "排序权重": 0 if result == RESULT_FAIL else (1 if result == RESULT_PENDING else 2),
    }


def completion_overview(period: str | None) -> dict[str, Any]:
    """按班组汇总完成情况，并带上每个成员的明细，供前端直接下钻。

    班组排序：缺口（不合格+未考核）多的在前，其次不合格人数，最后班组名。
    成员排序：不合格在前、未考核其次、合格在后，同级按姓名与培训编号稳定排列。
    """
    resolved, periods = resolve_period(period)
    rows = _rows_for_period(resolved)

    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        team_name = str(row.get("所属班组") or "").strip() or UNASSIGNED_TEAM
        grouped.setdefault(team_name, []).append(row)

    teams: list[dict[str, Any]] = []
    for team_name, team_rows in grouped.items():
        members = [_member_view(row) for row in team_rows]
        members.sort(key=lambda item: (item["排序权重"], str(item["培训对象"]), str(item["培训编号"])))
        summary = _summarize(team_rows)
        teams.append({
            "班组": team_name,
            **summary,
            "missingInstructor": sum(1 for row in team_rows if _is_blank(row.get("培训讲师"))),
            "missingMethod": sum(1 for row in team_rows if _is_blank(row.get("考核方式"))),
            "members": members,
        })
    teams.sort(key=lambda team: (-int(team["gap"]), -int(team["failed"]), str(team["班组"])))

    return {
        "period": resolved,
        "periods": periods,
        "summary": _summarize(rows),
        "teams": teams,
    }


class TrainingService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        period: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
        """台账列表：周期筛选与完成视图共用同一批数据、同一套汇总口径。"""
        resolved, _periods = resolve_period(period)
        rows = _rows_for_period(resolved)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("培训编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        summary = _summarize(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total, summary

    def completion(self, period: str | None) -> dict[str, Any]:
        return completion_overview(period)

    def periods(self) -> list[str]:
        return available_periods()

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
            entry[field] = values.get(field)
        entry["考核结果"] = entry.get("考核结果") or None
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


training_service = TrainingService()
