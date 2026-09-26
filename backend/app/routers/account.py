"""账号接口：前端切换账号时从服务端取账号清单与当前身份，角色以后端为准。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import ACCOUNTS, Account, account_public, current_account

router = APIRouter(prefix="/api/accounts", tags=["会话"])


@router.get("")
def list_accounts() -> dict[str, object]:
    """返回可切换的账号清单（只暴露 id/名称/角色，不暴露任何凭证）。"""
    return {"items": [account_public(account) for account in ACCOUNTS.values()]}


@router.get("/me")
def get_me(account: Account = Depends(current_account)) -> dict[str, object]:
    """按请求头解析当前账号及其在试剂耗材模块的操作权限。"""
    return {
        "account": account_public(account),
        "permissions": {"reagent:operate": account.can("reagent:operate")},
    }
