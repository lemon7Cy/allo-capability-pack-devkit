"""启动钩子:网关 lifespan 里、内嵌 LangGraph 运行时就绪后运行一次。

典型用途:恢复上次异常退出留下的半截任务(参照标书包的孤儿任务恢复)。
钩子可以是同步或异步函数;声明一个必填位置参数则会收到 FastAPI app。
钩子失败只降级本包(路由仍在),永远不会拖垮网关。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def on_boot() -> None:
    logger.info("[skeleton_pack] startup hook ran — replace with real recovery logic")
