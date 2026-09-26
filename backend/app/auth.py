"""账号与权限判定。

账号清单保存在服务端，前端请求只能携带账号 id（X-Operator-Id 头），
角色与权限一律由后端解析，杜绝前端伪造角色越权提交。
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

REAGENT_OPERATE = "reagent:operate"


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can(self, permission: str) -> bool:
        if self.is_admin:
            return True
        return permission in ROLE_PERMISSIONS.get(self.role, ())


# 角色 -> 允许的权限点。viewer 是无权限账号：只能查看列表/详情，不能做任何写操作。
ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "viewer": (),
}

ACCOUNTS: dict[str, Account] = {
    "admin": Account(id="admin", name="值班管理员", role="admin"),
    "viewer": Account(id="viewer", name="只读账号", role="viewer"),
}


def account_public(account: Account) -> dict[str, str]:
    return {"id": account.id, "name": account.name, "role": account.role}


def current_account(
    x_operator_id: str | None = Header(default=None, alias="X-Operator-Id"),
) -> Account:
    """从请求头解析当前操作账号；识别不出来一律按无权限处理，而不是默认放行。"""
    account = ACCOUNTS.get((x_operator_id or "").strip())
    if account is None:
        raise HTTPException(status_code=403, detail="未识别的操作账号，禁止执行该操作")
    return account


def require_permission(permission: str):
    """依赖工厂：保存类接口在入口处必须通过对应的权限点。"""

    def checker(account: Account = Depends(current_account)) -> Account:
        if not account.can(permission):
            raise HTTPException(
                status_code=403,
                detail=f"当前账号「{account.name}」无权限执行该操作",
            )
        return account

    return checker
