"""示例路由。硬规则:所有路由的实际 path 必须落在 pack_backend.json 的
mountPrefix 之下——最简单的守法方式就是像这样把前缀写进 APIRouter(prefix=...)。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

# 允许 import 的基座面之一:鉴权依赖。桌面模式下它直接返回本地上下文
# (调试时 curl 不需要带任何凭据),写法与将来多租户环境完全兼容。
from app.gateway.auth import AuthContext, get_auth_context

from skeleton_pack.services.demo_service import build_greeting

router = APIRouter(prefix="/api/skeleton-demo", tags=["skeleton-demo"])


@router.get("/ping")
async def ping() -> dict[str, Any]:
    """旁加载成功的第一信号:curl http://127.0.0.1:8001/api/skeleton-demo/ping"""
    return {"ok": True, "pack": "skeleton_demo"}


@router.get("/greet")
async def greet(name: str = "world", _auth: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    """演示:带鉴权依赖的路由 + 调用 services 层(业务逻辑不要写在路由里)。"""
    return {"message": build_greeting(name)}
