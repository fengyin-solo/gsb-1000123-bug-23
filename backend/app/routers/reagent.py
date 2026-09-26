"""试剂耗材接口：维护试剂耗材，覆盖领用试剂、登记用完、标记过期等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import REAGENT_OPERATE, Account, require_permission
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.reagent import StaleStateError, ReagentService

router = APIRouter(prefix="/api/reagent", tags=["试剂耗材"])

service = ReagentService()

LIST_FIELDS = ["试剂编号", "试剂名称", "规格等级", "生产厂家", "有效期至", "存放位置", "领用人员", "使用状态"]
STATUSES = ["在库", "已领用", "已用完", "已过期"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按试剂编号检索"),
    status: str | None = Query(default=None, description="在库、已领用、已用完、已过期"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按试剂编号与状态过滤试剂耗材列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出试剂耗材清单：返回当前过滤条件下的全量数据。

    必须排在 ``/{entry_id}`` 之前注册，否则 export 会被当成编号去转 int。
    """
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "reagent", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条试剂耗材明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"试剂耗材 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult, status_code=201)
def create_entry(
    payload: EntryPayload,
    operator: Account = Depends(require_permission(REAGENT_OPERATE)),
) -> ActionResult:
    """登记一条试剂耗材，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="试剂耗材已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(
    entry_id: int,
    payload: EntryPayload,
    operator: Account = Depends(require_permission(REAGENT_OPERATE)),
) -> ActionResult:
    """对单条试剂耗材执行领用试剂、登记用完、标记过期；不允许的动作会被拦下并说明原因。

    权限在入口处由依赖强制校验；业务冲突（版本过期）由服务层抛出，
    两种拒绝都不会改动记录。
    """
    action = str(payload.values.get("action") or "").strip()
    client_version = payload.values.get("version")
    try:
        entry, message = service.run_action(
            entry_id, action, operator=operator, client_version=client_version
        )
    except KeyError:
        # 不存在同样不允许写入，返回失败结果而非 500。
        return ActionResult(ok=False, message=f"试剂耗材 {entry_id} 不存在或已归档")
    except ValueError as exc:
        return ActionResult(ok=False, message=str(exc))
    except StaleStateError as exc:
        # 409：列表/详情页看到的是旧版本，让前端拿服务器数据重绘而不是覆盖归属。
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ActionResult(ok=True, message=message, entry=entry)
