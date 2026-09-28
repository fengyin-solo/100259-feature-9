"""技能培训接口：维护培训记录，覆盖组织培训、组织考核、归档等动作，
并提供培训完成情况的班组下钻视图数据。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.training import MONTH_PATTERN, TrainingService

router = APIRouter(prefix="/api/training", tags=["技能培训"])

service = TrainingService()

LIST_FIELDS = ["培训编号", "培训主题", "所属班组", "培训对象", "培训日期", "培训讲师", "考核方式", "考核结果", "培训状态"]
STATUSES = ["待培训", "培训中", "已考核", "已归档"]


def _validate_period(period: str | None) -> str | None:
    if period and not MONTH_PATTERN.match(period):
        raise HTTPException(status_code=400, detail="统计周期格式应为 YYYY-MM，例如 2026-09")
    return period


@router.get("/completion/periods")
def completion_periods() -> dict[str, Any]:
    """培训台账里实际出现过的统计周期，给台账页和完成情况视图共用同一个下拉框。"""
    return {"periods": service.list_periods()}


@router.get("/completion/summary")
def completion_summary(
    period: str | None = Query(default=None, description="YYYY-MM；不传表示全部周期"),
) -> dict[str, Any]:
    """总体完成情况。台账列表统计卡也取这个接口，完成率只有这一套口径。"""
    return service.completion_overview(_validate_period(period))


@router.get("/completion/teams")
def completion_teams(
    period: str | None = Query(default=None, description="YYYY-MM；不传表示全部周期"),
) -> dict[str, Any]:
    """按班组列出培训完成情况与考核结果分布（含成员明细，供就地展开下钻）。"""
    try:
        return service.completion_teams(_validate_period(period))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按培训编号检索"),
    status: str | None = Query(default=None, description="待培训、培训中、已考核、已归档"),
    period: str | None = Query(default=None, description="统计周期 YYYY-MM，与完成情况视图同口径"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按培训编号、状态与统计周期过滤技能培训列表；没有数据时返回空页，不报错。"""
    _validate_period(period)
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, period=period, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条培训记录明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"培训记录 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条培训记录，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="培训记录已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条培训记录执行组织培训、组织考核、归档；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出技能培训清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "training", "total": total, "items": items}
