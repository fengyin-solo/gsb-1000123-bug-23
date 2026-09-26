"""试剂耗材业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.auth import Account
from app.store import store

MODULE = "reagent"
REQUIRED_FIELDS = ["试剂编号", "试剂名称", "规格等级"]
STATUS_ORDER = ["在库", "已领用", "已用完", "已过期"]
ACTION_RULES = {"领用试剂": "已领用", "登记用完": "已用完", "标记过期": "已过期"}
NEGATIVE_ACTIONS = []

# 受控记录的归属字段；归属一律由后端在动作成功时落定，前端无法伪造或覆盖。
OWNER_FIELDS = ("归属账号", "归属人", "最后动作")


class StaleStateError(Exception):
    """客户端提交时携带的版本与服务端不一致（请求冲突），不能按旧数据继续流转。"""

    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__(f"记录已被其他操作更新，请刷新后重试（当前版本 {current_version}）")


def _int_value(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


class ReagentService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("试剂编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
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
        entry["version"] = 0
        entry["归属账号"] = None
        entry["归属人"] = None
        entry["最后动作"] = None
        rows.append(entry)
        return entry, []

    def run_action(
        self,
        entry_id: int,
        action: str,
        *,
        operator: Account,
        client_version: Any = None,
    ) -> tuple[dict[str, Any], str]:
        """执行状态流转。

        所有校验（存在性、动作合法性、版本冲突）都在任何写入之前完成，
        被拒绝时记录保持原样，归属也不会留下半截结论。
        """
        entry = store.find(MODULE, entry_id)
        if entry is None:
            raise KeyError(entry_id)
        if action not in ACTION_RULES:
            raise ValueError(f"动作「{action}」不属于试剂耗材可执行范围")
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            raise ValueError(f"目标状态「{target}」不在允许的状态序列里")

        # 请求冲突：按旧详情页/旧列表页提交时版本已落后，直接拒绝且不落任何字段。
        current_version = _int_value(entry.get("version"), 0)
        if client_version is not None and _int_value(client_version, -1) != current_version:
            raise StaleStateError(current_version)

        # 校验全部通过后才允许写入；归属只在成功时落定为当前操作账号。
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        entry["version"] = current_version + 1
        entry["归属账号"] = operator.id
        entry["归属人"] = operator.name
        entry["最后动作"] = action
        return entry, f"试剂耗材已{action}"
