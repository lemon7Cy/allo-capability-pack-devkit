"""静态路由:用包自己的路由服务 backend-ext/skeleton_pack/frontend_dist/(协议 §7.2)。

硬规则:本路由是 catch-all,必须放在 pack_backend.json routers[] 的**最后**
(放前面会遮住 API 路由);/ui 之下不得再挂任何 API 路由。

加固点(照抄改前缀即可,五条一条都别删):
- 点文件防护:路径段以 "." 开头一律 404(防 .git/.env 类文件外泄);
- 路径穿越防护:resolve 后必须仍在 frontend_dist 之内(防 ../../ 读任意文件);
- 缓存分级:assets/ 长缓存 immutable(构建产物带内容 hash),
  index.html no-store(包更新后刷新即生效,不吃旧缓存);
- SPA fallback 只对"无扩展名"路径生效——丢失的 .js/.css 明确 404,
  不会拿 index.html 冒充脚本(那种"200 但白屏"极难排查);
- 显式 MIME 表:绝不依赖 mimetypes.guess_type——它读操作系统表,Windows
  注册表默认没有 .mjs,pdf.js 之类的 module worker 会被当 text/plain 下发,
  Chromium 直接拒绝 module 导入(真机事故,精确症状:PDF 预览挂、其余全好)。
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/skeleton-demo/ui", tags=["skeleton-ui"])

DIST = Path(__file__).resolve().parents[1] / "frontend_dist"
_ASSET_EXT = re.compile(r"\.[A-Za-z0-9]{1,8}$")
_NO_STORE = {"Cache-Control": "no-store"}
_IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}

_MEDIA_TYPES = {
    ".html": "text/html",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".map": "application/json",
    ".wasm": "application/wasm",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".txt": "text/plain",
}


def _media_type(target: Path) -> str:
    return _MEDIA_TYPES.get(target.suffix.lower(), "application/octet-stream")


@router.get("/{path:path}")
async def serve_ui(path: str = "") -> FileResponse:
    if not DIST.is_dir():
        raise HTTPException(404, "frontend_dist missing (pack built without UI?)")
    if any(seg.startswith(".") for seg in path.split("/") if seg):
        raise HTTPException(404)
    target = (DIST / path).resolve() if path else DIST / "index.html"
    if not target.is_relative_to(DIST):
        raise HTTPException(404)
    if target.is_file():
        headers = _IMMUTABLE if "assets/" in path else _NO_STORE
        return FileResponse(target, media_type=_media_type(target), headers=headers)
    if _ASSET_EXT.search(path):
        raise HTTPException(404)
    return FileResponse(DIST / "index.html", media_type="text/html", headers=_NO_STORE)
