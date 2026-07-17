# Allo 能力包开发协议(合作方版 v1.1)

> 面向:为 Allo 桌面端开发「设计图助手」等大工作流工作台的合作团队。**本仓库即完整开发工具箱**:本文档(协议)+ [`docs/本地调试方案.md`](docs/本地调试方案.md)(拿到安装版客户端后如何本地跑通、排错)+ [`pack-skeleton/`](pack-skeleton/)(可直接旁加载跑通的最小骨架,建议从它的 README 开始)+ [`build_pack.py`](build_pack.py)(交付打包脚本)。
> **本版为 v1.1**:在 v1.0 冻结面(§2/§3 文件格式、§4 开发契约、§6 版本与交付)之上**新增 §7 iframe 前端形态并纳入冻结面**——Allo 方保证后续客户端更新向后兼容这套约定;确需变更时提前一个版本书面通知并附迁移说明。v1.0 的「组件源码编译进基座」前端约定自本版起**弃用**(已上线的编译型包继续兼容)。「标书助手」是跑在生产上的完整参照实现,本协议所有约定(含 iframe 形态与三条铁律)都经它验证(参照实现不随本仓分发)。变更历史见文末 [CHANGELOG](#11-changelog)。
> 结论先行:后端工作流可以**完全独立开发、独立交付、OTA 分发、装/更/卸全 UI 化,全程不需要 Allo 源码**;v1.1 起**前端同样自包含**——UI 构建产物随包分发,由包自己的静态路由服务,客户端 iframe 工作台直接打开,Allo 方零代码接入(§7)。v1.0 时代唯一的协作耦合点就此消失。

## 0. 五分钟上手路径

1. 装 Allo 客户端(Allo 方提供安装包,iframe 前端需 ≥ 0.1.21)→ 2. 进 [`pack-skeleton/`](pack-skeleton/) 按其 README 旁加载跑通 `ping` + iframe demo UI → 3. 读完本协议 §2–§7 → 4. 把骨架改名成你们的包开始开发 → 5. 调试全程照 [`docs/本地调试方案.md`](docs/本地调试方案.md)。
---

## 1. 一句话模型

能力包 = **一个 featureKey 三位一体**的 DLC:

```
featureKey(如 design_assistant)
  = 权益 key(功能组授权,进组即可用,纯鉴权无额度)
  = OTA 频道段(pack.design_assistant.beta,独立版本线)
  = 客户端安装目录(~/.allo/packs/design_assistant/)
```

员工在 Allo「智能体 → 能力包」里点安装:整包 zip 下载 → 依赖离线安装 → 路由挂进本地网关 → 应用自动重启 → 工作台出现。卸载即消失。更新有「可更新」徽章一键升级。

## 2. 包内布局(交付物结构)

```
design_assistant-<version>-<platform>-<arch>.zip
├── manifest.json                 # 构建脚本生成,勿手写
├── pack.json                     # 包元数据(featureKey/名称/iframe 前端声明,见 §7.1)
├── backend-ext/
│   ├── pack_backend.json         # 后端挂载声明(见 §4)
│   └── design_pack/              # 你们的 Python 包(路由+服务,全部业务逻辑)
│       ├── __init__.py
│       ├── routers/...           # FastAPI APIRouter(含 static.py 静态路由,见 §7.2)
│       ├── services/...
│       ├── frontend_dist/        # 构建好的 UI(iframe 形态,随包分发,见 §7)
│       └── startup.py            # 可选:启动钩子(如孤儿任务恢复)
└── wheels/                       # 仅「包独有」的 Python 依赖轮子
    ├── requirements.txt
    └── *.whl                     # 按平台预抓(darwin-arm64 / win_amd64 分别构建)
```

## 3. pack_backend.json(后端挂载声明)

标书的实际文件,照抄改名即可:

```json
{
  "schemaVersion": 1,
  "package": "design_pack",
  "routers": [
    { "module": "design_pack.routers.design_workbench", "attr": "router" },
    { "module": "design_pack.routers.static", "attr": "router" }
  ],
  "mountPrefix": "/api/design-workbench",
  "startupHooks": ["design_pack.startup:recover_orphan_jobs"],
  "pydeps": true
}
```

硬规则(装载器强制,违反=包被跳过并记日志,基座不受影响):
- `module` 必须都在你声明的 `package` 目录内(防跨包劫持)
- 所有路由的实际 path 必须落在 `mountPrefix` 之下,且前缀不得与基座或其他包冲突
- 需要 pip 依赖则 `pydeps: true`,轮子进 `wheels/`
- 服务 UI 的静态路由(§7.2)是 catch-all,**必须排在 `routers[]` 最后**——放前面会遮住后注册的 API 路由

## 4. 后端开发契约

- **框架**:FastAPI `APIRouter`。运行环境 = Allo 本地网关(Python 3.12),你们的代码在员工本机执行
- **可以 import 的基座面**:`app.gateway.auth`(鉴权依赖)与 `deerflow.*`(harness 公共层);**不得 import 基座其他 `app.*` 内部模块**(标书 150 个模块做到了零泄漏,可行性已证明)
- **依赖纪律(反投毒,重要)**:
  - 基座已有的库(fastapi、pydantic、pdfplumber、langgraph 等)**不准**再放进 wheels
  - 只带你们独有的依赖;版本尽量与生态主流对齐 —— 各包 pydeps 目录隔离,但最终同进程加载,**同库不同版本会冲突**
  - 拿不准的发依赖清单给 Allo 方对表
- **错误处理**:路由抛 `HTTPException`;工具函数返回错误字符串不抛异常(与基座风格一致)
- **测试**:你们的业务逻辑用标准 pytest 自测(纯 Python,不依赖 Allo);**挂载正确性**用 §5 的旁加载当冒烟闸——路由全量出现 + `/health` 正常 + 日志无跳包记录,即等价于我们内部的挂载测试
- **运行时默认值("装了就能用"模式)**:客户机没有 `.env`,包需要的外部服务地址/密钥等配置,在包的 `__init__.py` 里用 `os.environ.setdefault(...)` 内置默认值——标书包的远程解析服务就是这么接的,别指望装完再让员工配环境变量。要点:`setdefault` 不覆盖,**宿主显式设置的同名变量永远优先**;测试里 `delenv` 之后回到"未配置"语义。示例(占位值,换成你们的真实配置):

  ```python
  # design_pack/__init__.py
  import os
  os.environ.setdefault("DESIGN_PDF_REMOTE_API", "https://pdf-service.example.com")
  os.environ.setdefault("DESIGN_PDF_REMOTE_TOKEN", "<YOUR_TOKEN>")
  ```

## 5. 本地开发调试(不需要源码、不需要发布就能跑)

调试环境 = **Allo 安装版客户端本身**(不提供源码,mac / win 都支持)。原理:客户端启动时扫描 `~/.allo/packs-active-backend/`,把你们的 `backend-ext/` 链接进去即被真实网关挂载;桌面模式本地 API 无鉴权,curl 直打。四步概览:

macOS:
```bash
ln -s /你的仓库/backend-ext ~/.allo/packs-active-backend/design_assistant   # 旁加载
"/Applications/Allo Desktop.app/Contents/Resources/python/bin/python3" \
    -m pip install --target /你的仓库/backend-ext/pydeps -r requirements.txt # 装独有依赖(客户端自带 3.12)
# 完全退出并重开 Allo → 验证:
curl http://127.0.0.1:8001/api/design-workbench/...
curl -I http://127.0.0.1:8001/api/design-workbench/ui/index.html            # iframe UI(§7)也挂上了
tail -f ~/.allo/logs/desktop/gateway.log                                    # 排错唯一通道
```

Windows(cmd,junction 无需管理员;客户端后端为冻结 exe、**不带**独立 Python,依赖用你们自己的 Python 3.12 装):
```bat
mklink /J "%USERPROFILE%\.allo\packs-active-backend\design_assistant" "C:\你的仓库\backend-ext"
py -3.12 -m pip install --target C:\你的仓库\backend-ext\pydeps -r requirements.txt
rem 完全退出并重开 Allo(任务管理器确认无 Allo 进程)→ 验证:
curl http://127.0.0.1:8001/api/design-workbench/...
curl -I http://127.0.0.1:8001/api/design-workbench/ui/index.html
type "%USERPROFILE%\.allo\logs\desktop\gateway.log"
```

iframe 型包(§7)旁加载后,客户端「智能体 → 能力包」里**直接出现你们的卡片**,点开就是你们的 UI——界面调试不再依赖 Allo 方。完整步骤、跳包原因对照表、前端联调、Windows 说明:见配套的[`docs/本地调试方案.md`](docs/本地调试方案.md)。

## 6. 打包 / 版本 / 交付

- **打包工具**:`build_pack.py`(单文件脚本,随本指南一起交付,只依赖 Python3+pip):`python3 build_pack.py <你的包目录> --version 0.1.0-beta.1 --channel beta --platform darwin --arch arm64 --min-desktop-version 0.1.0 --fetch-wheels --out dist/`(win 版换 `--platform win32 --arch x64`;每个平台一个 zip)。依赖清单写在包目录根部的 `wheels-requirements.txt`(钉死版本 `==`),`--fetch-wheels` 会按目标平台自动抓对应 wheel——**在任一系统上都能同时产出 mac 和 win 两个平台的包**(wheels 是 PyPI 现成品,按目标平台下载,与构建机无关)
- **版本格式**:稳定版 `x.y.z` 或预发布 `x.y.z-beta.N`(构建脚本强制,v1.1 起放宽——此前只收 beta);常规迭代 +0.01
- **兼容声明(iframe 包强制)**:带 iframe 前端(§7)的包**必须**声明 `--min-desktop-version`,且不得低于 **`0.1.21`**(第一个支持 iframe 能力包宿主的基座版本;若你们用到更新的基座能力,以 Allo 发布说明为准取更高值)。防的坑:老基座装上 iframe 包只会挂后端路由、界面永远不出现,员工看到的是"装了没反应"——版本闸在安装前就把这种半残组合挡掉
- **交付流程 v0**:zip 交给 Allo 方 → 我们上传发布到 `pack.design_assistant.beta`(上传自动生成整包分发)→ 测试账号所在功能组授权 → 你们在 Allo 客户端里直接安装/调试/升级
- **灰度**:发布 ≠ 人人可见 —— 只有功能组里的员工能看到并安装,天然灰度

## 7. 前端(v1.1:iframe 自包含形态 —— 新包的标准路径)

> v1.0 的「组件源码交给 Allo 方编译进基座」自本版起**弃用**(已上线的编译型包继续兼容,不强迁)。新包一律走 iframe:**UI 随包分发、零基座代码**,前后端同一个 zip、同一条版本线、同一次发布——界面更新不再等 Allo 基座发版。骨架包就是完整的 iframe 参照实现,下面每条规则骨架里都有对应代码。

### 7.1 声明(pack.json)

```json
"frontend": {
  "kind": "iframe",
  "entry": "ui/index.html",
  "summary": "一句话简介(能力包卡片上显示,可选)",
  "icon": "ui/icon.svg"
}
```

- `kind: "iframe"` 与 `entry` 必填;`summary` / `icon` 可选(`icon` 是相对 `mountPrefix` 的路径,通常也放 frontend_dist 里)。
- 包挂载后,客户端「智能体 → 能力包」自动出现卡片,点开即在沙箱 iframe 里打开你们的 UI——Allo 方**不再为新包写任何前端代码**,激活门控(装了才显示、卸了消失)由基座通用宿主统一处理。

### 7.2 UI 放置与服务

- 构建产物放 **`backend-ext/<你们的包>/frontend_dist/`**(在包的路径白名单内,随 zip 一起分发与校验);
- 由**包自己的静态路由**在 `<mountPrefix>/ui` 下服务,该路由是 catch-all,**必须放在 pack_backend.json `routers[]` 的最后**(§3 硬规则;放前面会遮住 API 路由),且 `/ui` 之下不得再挂任何 API 路由;
- 骨架里的 [`routers/static.py`](pack-skeleton/backend-ext/skeleton_pack/routers/static.py) 是加固版实现,**照抄改前缀即可**,四个加固点别删:
  - 点文件防护:路径段以 `.` 开头一律 404(防 `.git`、`.env` 类文件被打包进去后外泄);
  - 路径穿越防护:`resolve()` 后必须仍在 `frontend_dist` 之内(`is_relative_to`),防 `../../` 读任意文件;
  - 缓存分级:`assets/` 长缓存 immutable(构建产物带内容 hash),`index.html` no-store(包更新后员工刷新即生效,不吃旧缓存);
  - SPA fallback 只对**无扩展名**路径生效——丢失的 `.js/.css` 明确 404,不会拿 index.html 冒充脚本(那种"200 但白屏"极难排查)。

### 7.3 铁律 1:entry 必须是具体文件

`entry` 写 `ui/index.html` 这样的**具体文件**,绝不能写目录(`ui/` 或 `ui`)。防的坑(真实故障):目录 URL 的尾斜杠会被中间层反复"纠正"——Next 代理 308 去掉尾斜杠、FastAPI 307 再加回来,**直接重定向死循环**;即便某一侧不循环,落在目录层级的文档 URL 也会让相对资源路径解析错一层,页面白屏。写死到 `index.html` 两个问题都不存在。

### 7.4 铁律 2:桥不得假设宿主源

宿主页面(Allo 桌面壳)与你们的 UI **不同源**,而且宿主源事先不可知——网关直出与打包应用两种形态下端口/前缀都不同。postMessage 桥的标准写法(骨架 `frontend_dist/index.html` 内联了完整实现):

- 首帧即向 `window.parent` post `{"type":"allo:ready","protocolVersion":1}`,targetOrigin 用 `"*"`——内容不敏感,且 postMessage 只会送达真实父窗口;
- 入站消息**只认 `event.source === window.parent`**(源帧钉死,防第三方帧注入);
- 从**第一条入站消息学习宿主 origin**,之后所有出站 post 固定钉到它;
- 消息类型(桥协议 v1):`allo:ready`(UI→宿主,就绪)/ `allo:init {featureKey, locale, theme}`(宿主→UI,初始化)/ `allo:exit`(UI→宿主,退出工作台)/ `allo:title`(UI→宿主,改工作台标题);
- 桥协议**只增不改**:收到未知类型必须静默忽略(前向兼容,宿主升级不炸旧包)。

防的坑(真实故障):把宿主源写成固定白名单(如 `localhost:3100`)——换个形态宿主源就变了,`allo:ready` 永远送不到,宿主 5 秒超时判"包 UI 未就绪"。

### 7.5 铁律 3:API 基址不得硬编码

你们的 UI 文档地址是 `{apiBase}<mountPrefix>/ui/index.html`,其中 `{apiBase}` 取决于宿主怎么装载:网关直出时是 `""`(与 API 同源同前缀),打包应用把 iframe 走前端代理时是一个**代理前缀**。所以所有 `fetch` / `EventSource` 的基址必须**从自身 location 推导**(骨架内联了这个助手):

```js
const UI_MARKER = "/api/design-workbench/ui/";   // 换成你们的 <mountPrefix>/ui/
function apiBase() {
  const i = window.location.pathname.indexOf(UI_MARKER);
  return i > 0 ? window.location.pathname.slice(0, i) : "";
}
fetch(apiBase() + "/api/design-workbench/your-endpoint");
```

防的坑(真实故障):写死 `/api/...` 绝对路径或 `http://127.0.0.1:8001`——网关直出世界正常,打包代理世界全部 404/跨源;只有自定位能在两个世界同时活。

### 7.6 构建要求

- 打包器随意(vite / webpack / rollup 均可),产物必须是**纯静态 SPA**(静态文件即全部,无 SSR、无服务端 rewrite);
- 资源 URL 必须**相对**(vite 配 `base: "./"`)——UI 挂在 `<mountPrefix>/ui/` 深层路径下,绝对 `/assets/...` 全部 404 白屏;
- 不强制用路由:纯状态驱动的界面完全合法;**要用路由必须 hash 路由**(静态路由没有 history rewrite,BrowserRouter 刷新即 404);
- 骨架的 demo UI 是零构建的裸 HTML(桥 shim + 基址推导内联);真实应用的 vite 配置要点见骨架 README。

## 8. Allo 方为每个新包做的事(你们提需求即可)

1. 注册 featureKey(design_assistant)+ 建功能组 + 加测试账号
2. 管理后台功能列表登记
3. 发布通道:接收 zip → 发布 → 通知可测

(v1.0 时代的「前端组件集成 + 基座发版」一步已随 iframe 形态取消——新包零基座代码,能力包卡片由通用宿主按 pack.json 自动生成。)

## 9. 验收清单(对齐标书的生产标准)

- [ ] 本地软链调试:路由全量挂载、/health 正常
- [ ] iframe UI(§7):`<mountPrefix>/ui/index.html` 返回 200、客户端卡片出现、`allo:ready`/`allo:exit` 桥通、直连与代理两个世界 API 都可达(自定位,铁律 3)
- [ ] 冒烟测试过(真实 pack_loader 挂载)
- [ ] 依赖清单评审过(无基座重复、无跨包冲突)
- [ ] darwin-arm64 + win32-x64 两个 zip 构建通过(含 `--min-desktop-version ≥ 0.1.21`,§6)
- [ ] 发布后:授权账号可安装 → 工作台可用 → 可升级 → 卸载即消失
- [ ] 未授权账号看不到/装不了(403)

## 10. 开发工具箱(Allo 方交付,合作方拿到的全部东西)

| 交付物 | 内容 |
|---|---|
| Allo 安装版客户端 | Mac DMG + Windows 安装包;即调试环境本体(iframe 前端需 ≥ 0.1.21,§6) |
| 本指南 v1.1 | 协议冻结面 + 交付契约 + iframe 前端形态(§7) |
| 《本地调试方案》 | 旁加载/依赖/排错/前端联调全流程 |
| `build_pack.py` | 单文件打包脚本(生成 manifest + 交付 zip) |
| 骨架包 [`pack-skeleton/`](pack-skeleton/) | 可直接旁加载跑通的最小样例:pack.json(iframe 声明)/ pack_backend.json / 示例 router / 加固版静态路由 / 零构建 demo UI(桥 shim + API 基址自定位内联)/ wheels-requirements.txt |
| 测试员工账号 | 已授权 featureKey 的功能组成员,登录后可调模型、装正式包 |

不提供:Allo 源码、基座内部模块文档。你们需要的基座交互面**只有** `mountPrefix` 下的自有路由、`app.gateway.auth` 鉴权依赖、`deerflow.*` 公共层(§4),外加 iframe 桥的四个消息类型(§7.4),超出这个面的需求提给 Allo 方评估,不要靠猜。

## 11. CHANGELOG

- **v1.1(2026-07-17)**:新增 **iframe 前端形态**并纳入冻结面(§7 全面改写):pack.json `frontend: {kind: "iframe", entry, summary, icon?}`,UI 随包分发(`backend-ext/<包>/frontend_dist/`)、由包自带的加固版静态路由在 `<mountPrefix>/ui` 服务(routers[] 必须排最后);**三条铁律**——entry 必须是具体文件(防 308/307 重定向死循环与相对路径错层)、桥不得假设宿主源(ready 用 `"*"` + 钉 `event.source` + 从首条入站消息学习宿主 origin)、API 基址不得硬编码(从自身 location 自定位);构建要求(纯静态 SPA + 相对资源 URL + 路由只许 hash)。版本格式放宽为稳定版 `x.y.z` 或 `x.y.z-beta.N`;iframe 包强制 `minDesktopVersion ≥ 0.1.21`。骨架升级为完整 iframe 演示(零构建 demo UI 内联桥 shim 与基址自定位);v1.0 的编译型前端约定弃用,`frontend-sample/` 移除(已上线的编译型包继续兼容)。
- **v1.0**:初版协议:后端挂载契约(§2–§5)、打包与交付(§6)、编译型前端 v0 约定(旧 §7)、可旁加载跑通的骨架包。
