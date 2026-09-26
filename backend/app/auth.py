"""请求账号与操作权限。

演示项目没有登录服务，调用方通过请求头传入当前账号；后端仍必须以这里的
依赖作为保存动作的最终权限边界，不能依赖前端是否禁用按钮。
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

from fastapi import Depends, Header, HTTPException

ROLE_ADMIN = "admin"
ROLE_VIEWER = "viewer"
VALID_ROLES = {ROLE_ADMIN, ROLE_VIEWER}


@dataclass(frozen=True)
class Operator:
    operator_id: str
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def current_operator(
    x_operator_id: str | None = Header(default=None, alias="X-Operator-Id"),
    x_operator_name: str | None = Header(default=None, alias="X-Operator-Name"),
    x_operator_role: str | None = Header(default=None, alias="X-Operator-Role"),
) -> Operator:
    operator_id = (x_operator_id or "").strip()
    role = (x_operator_role or "").strip().lower()
    if not operator_id or role not in VALID_ROLES:
        raise HTTPException(status_code=401, detail="未识别当前账号，请重新切换账号后再操作")
    return Operator(
        operator_id=operator_id,
        name=unquote((x_operator_name or "").strip()) or operator_id,
        role=role,
    )


def require_reagent_manager(operator: Operator = Depends(current_operator)) -> Operator:
    """FastAPI 依赖：仅管理员能保存试剂耗材状态。"""
    if not operator.is_admin:
        raise HTTPException(status_code=403, detail="当前账号无权领用、登记用完或标记过期试剂耗材")
    return operator
