# Allo 能力包开发协议(合作方版 v1.0)

> 面向:为 Allo 桌面端开发「设计图助手」等大工作流工作台的合作团队。**本仓库即完整开发工具箱**:本文档(协议)+ [`docs/本地调试方案.md`](docs/本地调试方案.md)(拿到安装版客户端后如何本地跑通、排错)+ [`pack-skeleton/`](pack-skeleton/)(可直接旁加载跑通的最小骨架,建议从它的 README 开始)+ [`build_pack.py`](build_pack.py)(交付打包脚本)。
> **本版为协议定稿(v1.0)**:§2/§3 的文件格式、§4 的开发契约、§6 的版本与交付规则为**冻结面**——Allo 方保证后续客户端更新向后兼容这套约定;确需变更时提前一个版本书面通知并附迁移说明。「标书助手」是跑在生产上的完整参照实现,本协议所有约定都经它验证(参照实现不随本仓分发)。
> 结论先行:后端工作流可以**完全独立开发、独立交付、OTA 分发、装/更/卸全 UI 化,全程不需要 Allo 源码**;前端界面 v0 阶段按约定交付组件源码由 Allo 方编译进基座(见 §7,这是当前唯一的协作耦合点)。

## 0. 五分钟上手路径

1. 装 Allo 客户端(Allo 方提供安装包)→ 2. 进 [`pack-skeleton/`](pack-skeleton/) 按其 README 旁加载跑通 `ping` → 3. 读完本协议 §2–§6 → 4. 把骨架改名成你们的包开始开发 → 5. 调试全程照 [`docs/本地调试方案.md`](docs/本地调试方案.md)。
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
├── pack.json                     # 包元数据(featureKey/名称/前端能力位)
├── backend-ext/
│   ├── pack_backend.json         # 后端挂载声明(见 §4)
│   └── design_pack/              # 你们的 Python 包(路由+服务,全部业务逻辑)
│       ├── __init__.py
│       ├── routers/...           # FastAPI APIRouter
│       ├── services/...
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
    { "module": "design_pack.routers.design_workbench", "attr": "router" }
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

## 4. 后端开发契约

- **框架**:FastAPI `APIRouter`。运行环境 = Allo 本地网关(Python 3.12),你们的代码在员工本机执行
- **可以 import 的基座面**:`app.gateway.auth`(鉴权依赖)与 `deerflow.*`(harness 公共层);**不得 import 基座其他 `app.*` 内部模块**(标书 150 个模块做到了零泄漏,可行性已证明)
- **依赖纪律(反投毒,重要)**:
  - 基座已有的库(fastapi、pydantic、pdfplumber、langgraph 等)**不准**再放进 wheels
  - 只带你们独有的依赖;版本尽量与生态主流对齐 —— 各包 pydeps 目录隔离,但最终同进程加载,**同库不同版本会冲突**
  - 拿不准的发依赖清单给 Allo 方对表
- **错误处理**:路由抛 `HTTPException`;工具函数返回错误字符串不抛异常(与基座风格一致)
- **测试**:你们的业务逻辑用标准 pytest 自测(纯 Python,不依赖 Allo);**挂载正确性**用 §5 的旁加载当冒烟闸——路由全量出现 + `/health` 正常 + 日志无跳包记录,即等价于我们内部的挂载测试
- **运行时默认值**:客户机没有 `.env`,包需要的外部服务地址/密钥等配置,在包的 `__init__.py` 里用 `os.environ.setdefault(...)` 内置默认值(宿主显式配置仍优先)——标书包的远程解析服务就是这么接的,别指望装完再让员工配环境变量

## 5. 本地开发调试(不需要源码、不需要发布就能跑)

调试环境 = **Allo 安装版客户端本身**(不提供源码)。原理:客户端启动时扫描 `~/.allo/packs-active-backend/`,把你们的 `backend-ext/` 软链进去即被真实网关挂载;桌面模式本地 API 无鉴权,curl 直打;依赖用客户端自带的 Python 3.12 装。四步概览:

macOS:
```bash
ln -s /你的仓库/backend-ext ~/.allo/packs-active-backend/design_assistant   # 旁加载
"/Applications/Allo Desktop.app/Contents/Resources/python/bin/python3" \
    -m pip install --target /你的仓库/backend-ext/pydeps -r requirements.txt # 装独有依赖(客户端自带 3.12)
# 完全退出并重开 Allo → 验证:
curl http://127.0.0.1:8001/api/design-workbench/...
tail -f ~/.allo/logs/desktop/gateway.log                                    # 排错唯一通道
```

Windows(cmd,junction 无需管理员;客户端后端为冻结 exe、**不带**独立 Python,依赖用你们自己的 Python 3.12 装):
```bat
mklink /J "%USERPROFILE%\.allo\packs-active-backend\design_assistant" "C:\你的仓库\backend-ext"
py -3.12 -m pip install --target C:\你的仓库\backend-ext\pydeps -r requirements.txt
rem 完全退出并重开 Allo(任务管理器确认无 Allo 进程)→ 验证:
curl http://127.0.0.1:8001/api/design-workbench/...
type "%USERPROFILE%\.allo\logs\desktop\gateway.log"
```

完整步骤、跳包原因对照表、前端联调、Windows 说明:见配套的[`docs/本地调试方案.md`](docs/本地调试方案.md)。

## 6. 打包 / 版本 / 交付

- **打包工具**:`build_pack.py`(单文件脚本,随本指南一起交付,只依赖 Python3+pip):`python3 build_pack.py <你的包目录> --version 0.1.0-beta.1 --channel beta --platform darwin --arch arm64 --min-desktop-version 0.1.0 --fetch-wheels --out dist/`(win 版换 `--platform win32 --arch x64`;每个平台一个 zip)。依赖清单写在包目录根部的 `wheels-requirements.txt`(钉死版本 `==`),`--fetch-wheels` 会按目标平台自动抓对应 wheel——**在任一系统上都能同时产出 mac 和 win 两个平台的包**(wheels 是 PyPI 现成品,按目标平台下载,与构建机无关)
- **版本格式**:`x.y.z-beta.N`(构建脚本强制);常规迭代 +0.01
- **交付流程 v0**:zip 交给 Allo 方 → 我们上传发布到 `pack.design_assistant.beta`(上传自动生成整包分发)→ 测试账号所在功能组授权 → 你们在 Allo 客户端里直接安装/调试/升级
- **灰度**:发布 ≠ 人人可见 —— 只有功能组里的员工能看到并安装,天然灰度

## 7. 前端(v0 的诚实约定 —— 唯一的协作耦合点)

v0 阶段包的界面**编译进 Allo 基座**(协议 §5/§9),动态加载 UI 在后续版本:

- 你们交付 React 组件源码,目录约定 `frontend/src/components/desktop/design/`(参照 `desktop/tender/` 47 个组件的组织)
- **只依赖稳定原语**:`@/lib/utils`(cn)、`@/components/ui/*`;标书实证:跨 700 个 commit 分叉零适配成本,守住这条线你们的组件可以长期免维护地跟基座走
- 技术栈:Next.js 16 / React 19 / TypeScript / Tailwind 4;入口组件形如 `DesignProjectsApp({ onExit })`
- Allo 方负责:接入能力包卡片目录、右侧工作台面板、按 featureKey 的激活门控(装了才显示,卸了消失)—— 每接一个新包约半天
- 界面更新走 Allo 基座 OTA(我们发版);后端更新走你们的包版本(独立发)

## 8. Allo 方为每个新包做的事(你们提需求即可)

1. 注册 featureKey(design_assistant)+ 建功能组 + 加测试账号
2. 客户端目录接入(能力包卡片 + 管理后台功能列表)
3. 前端组件集成 + 基座发版
4. 发布通道:接收 zip → 发布 → 通知可测

## 9. 验收清单(对齐标书的生产标准)

- [ ] 本地软链调试:路由全量挂载、/health 正常
- [ ] 冒烟测试过(真实 pack_loader 挂载)
- [ ] 依赖清单评审过(无基座重复、无跨包冲突)
- [ ] darwin-arm64 + win32-x64 两个 zip 构建通过
- [ ] 发布后:授权账号可安装 → 工作台可用 → 可升级 → 卸载即消失
- [ ] 未授权账号看不到/装不了(403)

## 10. 开发工具箱(Allo 方交付,合作方拿到的全部东西)

| 交付物 | 内容 |
|---|---|
| Allo 安装版客户端 | Mac DMG(+ 后续 Win 安装包);即调试环境本体 |
| 本指南 v1.0 | 协议冻结面 + 交付契约 |
| 《本地调试方案》 | 旁加载/依赖/排错/前端联调全流程 |
| `build_pack.py` | 单文件打包脚本(生成 manifest + 交付 zip) |
| 骨架包 [`pack-skeleton/`](pack-skeleton/) | 可直接旁加载跑通的最小样例:pack.json / pack_backend.json / 一个示例 router / wheels-requirements.txt / 前端入口组件样例 |
| 测试员工账号 | 已授权 featureKey 的功能组成员,登录后可调模型、装正式包 |

不提供:Allo 源码、基座内部模块文档。你们需要的基座交互面**只有** `mountPrefix` 下的自有路由、`app.gateway.auth` 鉴权依赖、`deerflow.*` 公共层(§4),超出这个面的需求提给 Allo 方评估,不要靠猜。
