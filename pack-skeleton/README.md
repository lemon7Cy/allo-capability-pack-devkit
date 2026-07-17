# pack-skeleton — Allo 能力包最小骨架(iframe 形态)

一个**能直接旁加载跑通**的能力包 demo:不含任何业务代码,演示"一个合法的能力包长什么样"——包括 v1.1 的 iframe 前端(UI 随包分发、零基座代码,协议 §7)。配套文档:《Allo能力包开发指南(合作方版)》(协议契约)、《Allo能力包本地调试方案(合作方无源码版)》(调试全流程)。

## 5 分钟跑通(先别改任何东西)

macOS:
```bash
# 1. 旁加载:链接名必须等于 featureKey
ln -s "$(pwd)/backend-ext" ~/.allo/packs-active-backend/skeleton_demo
# 2. 完全退出并重新打开 Allo(菜单栏退出,不是关窗口)
# 3. 验证后端
curl http://127.0.0.1:8001/api/skeleton-demo/ping
#   → {"ok":true,"pack":"skeleton_demo"}
curl "http://127.0.0.1:8001/api/skeleton-demo/greet?name=你的名字"
# 4. 验证 iframe UI(v1.1;浏览器直接打开这个地址也行)
curl -I http://127.0.0.1:8001/api/skeleton-demo/ui/index.html
#   → HTTP 200
```

Windows(cmd,在本目录下执行;junction 无需管理员):
```bat
rem 1. 旁加载
mklink /J "%USERPROFILE%\.allo\packs-active-backend\skeleton_demo" "%CD%\backend-ext"
rem 2. 完全退出并重新打开 Allo(任务管理器确认无 Allo 进程)
rem 3. 验证
curl http://127.0.0.1:8001/api/skeleton-demo/ping
curl "http://127.0.0.1:8001/api/skeleton-demo/greet?name=你的名字"
curl -I http://127.0.0.1:8001/api/skeleton-demo/ui/index.html
```

骨架零 Python 依赖、零前端构建,两个系统都**不需要**装任何东西就能跑通这一步。

**第 5 步——到客户端里看真界面**:打开 Allo「智能体 → 能力包」,会出现「骨架示例」卡片(iframe 包旁加载即可见,调试方案 §1.1),点开就是 demo 工作台:bridge 状态行显示 `init received` = 桥通了;问候语出现 = 包 API 经自定位基址打通了;「退出」按钮能回到列表 = `allo:exit` 通了。

看到 ping 返回 + 卡片可开 = 你的调试环境完全就绪。出问题看 `~/.allo/logs/desktop/gateway.log`(调试方案 §6 有原因对照表)。

## 目录说明

```
pack.json                          包元数据:featureKey / 名称 / iframe 前端声明
                                   (entry 必须写到具体文件 ui/index.html,铁律 1)
wheels-requirements.txt            独有 Python 依赖清单(骨架为空;版本必须钉死)
backend-ext/
  pack_backend.json                后端挂载声明:package / routers / mountPrefix / 启动钩子
                                   (静态路由是 catch-all,必须排在 routers[] 最后)
  skeleton_pack/
    __init__.py                    内置默认配置的写法(setdefault,"装了就能用",占位值示范)
    routers/demo.py                示例路由:mountPrefix 纪律 + 鉴权依赖用法
    routers/static.py              加固版静态路由:服务 frontend_dist(照抄改前缀即可,协议 §7.2)
    services/demo_service.py       业务层示例(路由薄、服务厚)
    startup.py                     启动钩子示例(异常恢复类逻辑放这)
    frontend_dist/index.html       零构建 demo UI:桥 shim + API 基址自定位内联
                                   (协议三条铁律的参照实现,真实应用照搬这两段逻辑)
```

## 开始开发你们自己的包

1. 全局替换三个名字:`skeleton_demo` → 你们的 featureKey(小写字母/数字/下划线,与 Allo 方确认后定死)、`skeleton_pack` → 你们的 Python 包名、`/api/skeleton-demo` → 你们的 mountPrefix(注意 `routers/static.py` 的 prefix 和 `frontend_dist/index.html` 的 `UI_MARKER` 里也各有一处);
2. 在 `routers/` `services/` 里写业务,独有依赖进 `wheels-requirements.txt` 并按调试方案 §4 装进 `backend-ext/pydeps/`(记得把 `pack_backend.json` 的 `pydeps` 改为 `true`);
3. 迭代循环:后端改代码 → 重启 Allo → curl;UI 改 `frontend_dist` → **刷新即可**(index.html no-store,不用重启);
4. 交付:用 Allo 方提供的 `build_pack.py` 打 zip(指南 §6,iframe 包必须带 `--min-desktop-version 0.1.21` 起),发给 Allo 方发布。

## 真实应用用 vite(可选,demo 用不上)

骨架的 demo UI 是零构建裸 HTML;真实工作台建议 vite + React,四个要点:

- `vite.config.ts` 必须 `base: "./"`——UI 挂在 `<mountPrefix>/ui/` 深层路径下,资源 URL 必须相对(绝对 `/assets/...` 全部 404 白屏,协议 §7.6);
- 构建直接输出进包:`vite build --outDir ../backend-ext/<你们的包>/frontend_dist --emptyOutDir`(前端源码目录放 `frontend/`,不进交付 zip);
- 把 demo `index.html` 里"桥 shim"和"API 基址自定位"两段逻辑原样搬进你们的入口模块(只改 `UI_MARKER` 前缀,别自由发挥);
- 路由可用可不用(纯状态驱动完全合法);要用必须 **hash 路由**(静态托管没有 history rewrite)。

## 最容易踩的红线

- 所有代码必须在你们声明的 package 目录内,所有路由必须落在 mountPrefix 下——违反 = 整包被跳过(看日志);
- 基座已有的库不进 wheels(反投毒规则,指南 §4);
- iframe 三条铁律(指南 §7.3–§7.5):entry 必须是具体文件 / 桥不得假设宿主源 / API 基址不得硬编码——违反的结果都是白屏或"包 UI 未就绪",demo UI 就是参照实现;
- 静态路由必须排 `routers[]` 最后,`/ui` 下不挂 API;
- 旁加载只是调试通道,不是分发通道:正式装包必须走 OTA + 功能组授权。
