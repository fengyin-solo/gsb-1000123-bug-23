"""试剂耗材业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "reagent"
REQUIRED_FIELDS = ["试剂编号", "试剂名称", "规格等级"]
STATUS_ORDER = ["在库", "已领用", "已用完", "已过期"]
ACTION_RULES = {"领用试剂": "已领用", "登记用完": "已用完", "标记过期": "已过期"}
NEGATIVE_ACTIONS = ["标记过期"]


class ReagentStateConflict(Exception):
    """请求基于过期版本，继续保存会覆盖其他请求的状态或归属。"""


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
        entry["使用状态"] = STATUS_ORDER[0]
        entry["version"] = 1
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(
        self,
        entry_id: int,
        action: str,
        *,
        operator_id: str = "",
        operator_name: str = "",
        expected_version: int | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"试剂耗材 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于试剂耗材可执行范围"

        current_version = int(entry.get("version") or 1)
        if expected_version is not None and expected_version != current_version:
            raise ReagentStateConflict(
                f"试剂耗材已被其他账号更新（当前版本 {current_version}），请刷新后再提交"
            )

        current_status = str(entry.get("status") or STATUS_ORDER[0])
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        if not self._transition_allowed(current_status, target):
            raise ReagentStateConflict(
                f"试剂耗材当前为{current_status}，不能重复执行「{action}」；请刷新确认归属后再操作"
            )

        # 先完成状态和版本校验，再写归属；被拒绝或冲突时不会留下半截归属。
        entry["status"] = target
        entry["使用状态"] = target
        if action == "领用试剂":
            entry["领用人员"] = operator_name
            entry["owner_id"] = operator_id
            entry["owner_name"] = operator_name
        entry["version"] = current_version + 1
        entry["pending"] = target not in {"已用完", "已过期"}
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"试剂耗材已{action}"

    @staticmethod
    def _transition_allowed(current_status: str, target_status: str) -> bool:
        allowed: dict[str, set[str]] = {
            "在库": {"已领用", "已过期"},
            "已领用": {"已用完", "已过期"},
            "已用完": set(),
            "已过期": set(),
        }
        return target_status in allowed.get(current_status, set())
