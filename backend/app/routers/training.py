"""技能培训接口：维护培训记录，并提供按班组下钻的完成情况视图。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.training import training_service

router = APIRouter(prefix="/api/training", tags=["技能培训"])

service = training_service

LIST_FIELDS = ["培训编号", "培训主题", "培训对象", "所属班组", "培训日期", "培训讲师", "考核方式", "考核结果", "培训状态"]
STATUSES = ["待培训", "培训中", "已考核", "已归档"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按培训编号检索"),
    status: str | None = Query(default=None, description="待培训、培训中、已考核、已归档"),
    period: str | None = Query(default=None, description="统计周期 YYYY-MM；latest 默认最新，all 为全部周期"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按周期、培训编号与状态过滤台账；summary 与完成视图同源，保证完成率结论一致。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total, summary = service.list_entries(
        keyword=keyword, status=status, period=period, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size, summary=summary)


@router.get("/completion")
def completion_view(
    period: str | None = Query(default=None, description="统计周期 YYYY-MM；默认取台账最新周期"),
) -> dict[str, Any]:
    """按班组列出培训完成情况与考核结果分布，成员明细随班组一起返回供前端下钻。"""
    return service.completion(period)


@router.get("/periods")
def list_periods() -> dict[str, Any]:
    """列出可选统计周期（倒序），供前端周期切换使用。"""
    return {"periods": service.periods()}


@router.get("/export")
def export_entries(
    period: str | None = Query(default=None, description="统计周期；默认全部周期"),
) -> dict[str, Any]:
    """导出技能培训清单：全量数据外带同一口径的汇总，避免导出结果与页面结论不一致。"""
    export_period = None if period in (None, "all") else period
    items, total, summary = service.list_entries(period=export_period, page=1, size=10000)
    return {"module": "training", "total": total, "summary": summary, "items": items}


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
