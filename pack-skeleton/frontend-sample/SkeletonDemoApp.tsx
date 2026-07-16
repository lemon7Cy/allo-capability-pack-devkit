"use client";

/**
 * 前端入口组件样例(v0:由 Allo 方编译进基座,不随包分发)。
 *
 * 契约(守住 = 你们的组件可长期免维护地跟基座走):
 * - 只依赖稳定原语:`@/lib/utils`(cn)与 `@/components/ui/*`;
 *   不 import 基座其他内部模块。
 * - 入口组件签名:接收 `onExit`(用户退出工作台的回调)。
 * - 数据请求:相对路径打本地网关(生产环境同源),开发期你们自己的
 *   dev server 直接 fetch http://127.0.0.1:8001(CORS 已放行 localhost:3000)。
 * - 技术栈:React 19 / TypeScript / Tailwind 4。
 */

import { useEffect, useState } from "react";

export interface SkeletonDemoAppProps {
  onExit: () => void;
}

export function SkeletonDemoApp({ onExit }: SkeletonDemoAppProps) {
  const [message, setMessage] = useState<string>("loading…");

  useEffect(() => {
    // 开发期改成 http://127.0.0.1:8001/api/skeleton-demo/greet
    fetch("/api/skeleton-demo/greet?name=partner")
      .then((res) => res.json())
      .then((data: { message: string }) => setMessage(data.message))
      .catch((error: unknown) => setMessage(`request failed: ${String(error)}`));
  }, []);

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-lg font-semibold">骨架示例工作台</h1>
      <p className="text-sm text-muted-foreground">{message}</p>
      <button className="rounded-md border px-3 py-1 text-sm" onClick={onExit}>
        退出
      </button>
    </div>
  );
}
