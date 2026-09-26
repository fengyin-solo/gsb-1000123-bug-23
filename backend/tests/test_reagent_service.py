"""试剂耗材状态流转与并发保护测试。"""
from __future__ import annotations

import copy

from app.services.reagent import ReagentService, ReagentStateConflict
from app.store import store


def reagent_row(entry_id: int) -> dict:
    return store.find("reagent", entry_id)  # type: ignore[return-value]


def test_admin_can_move_stock_to_used_and_keeps_owner() -> None:
    service = ReagentService()
    stock = reagent_row(1)
    original = copy.deepcopy(stock)
    try:
        entry, _ = service.run_action(
            1,
            "领用试剂",
            operator_id="admin-001",
            operator_name="值班管理员",
            expected_version=1,
        )
        assert entry is not None
        assert entry["status"] == "已领用"
        assert entry["owner_id"] == "admin-001"
        assert entry["领用人员"] == "值班管理员"
        assert entry["version"] == 2

        entry, _ = service.run_action(
            1,
            "登记用完",
            operator_id="admin-001",
            operator_name="值班管理员",
            expected_version=2,
        )
        assert entry is not None
        assert entry["status"] == "已用完"
        assert entry["owner_id"] == "admin-001"
        assert entry["version"] == 3
    finally:
        stock.clear()
        stock.update(original)


def test_stale_request_conflicts_and_leaves_owner_unchanged() -> None:
    service = ReagentService()
    used = reagent_row(3)
    original = copy.deepcopy(used)
    try:
        try:
            service.run_action(
                3,
                "标记过期",
                operator_id="intruder",
                operator_name="越权账号",
                expected_version=2,
            )
        except ReagentStateConflict:
            pass
        else:
            raise AssertionError("过期版本请求必须被拒绝")

        current = reagent_row(3)
        assert current["status"] == "已用完"
        assert current["owner_id"] == "admin-001"
        assert current["领用人员"] == "值班管理员"
        assert current["version"] == 3
    finally:
        used.clear()
        used.update(original)
