"""业务逻辑层示例。约定:路由薄、服务厚;工具函数返回错误字符串而不是抛异常,
需要给客户端报错时在路由层抛 HTTPException。"""

from __future__ import annotations


def build_greeting(name: str) -> str:
    return f"hello, {name} — from skeleton_pack services layer"
