# pack-skeleton — Allo 能力包最小骨架

一个**能直接旁加载跑通**的能力包 demo:不含任何业务代码,演示"一个合法的能力包长什么样"。配套文档:《Allo能力包开发指南(合作方版)》(协议契约)、《Allo能力包本地调试方案(合作方无源码版)》(调试全流程)。

## 5 分钟跑通(先别改任何东西)

macOS:
```bash
# 1. 旁加载:链接名必须等于 featureKey
ln -s "$(pwd)/backend-ext" ~/.allo/packs-active-backend/skeleton_demo
# 2. 完全退出并重新打开 Allo(菜单栏退出,不是关窗口)
# 3. 验证
curl http://127.0.0.1:8001/api/skeleton-demo/ping
#   → {"ok":true,"pack":"skeleton_demo"}
curl "http://127.0.0.1:8001/api/skeleton-demo/greet?name=你的名字"
```

Windows(cmd,在本目录下执行;junction 无需管理员):
```bat
rem 1. 旁加载
mklink /J "%USERPROFILE%\.allo\packs-active-backend\skeleton_demo" "%CD%\backend-ext"
rem 2. 完全退出并重新打开 Allo(任务管理器确认无 Allo 进程)
rem 3. 验证
curl http://127.0.0.1:8001/api/skeleton-demo/ping
curl "http://127.0.0.1:8001/api/skeleton-demo/greet?name=你的名字"
```

骨架零 Python 依赖,两个系统都**不需要**装任何东西就能跑通这一步。

看到 ping 返回 = 你的调试环境完全就绪。出问题看 `~/.allo/logs/desktop/gateway.log`(调试方案 §6 有原因对照表)。

## 目录说明

```
pack.json                          包元数据:featureKey / 名称 / 前端能力位
wheels-requirements.txt            独有 Python 依赖清单(骨架为空;版本必须钉死)
backend-ext/
  pack_backend.json                后端挂载声明:package / routers / mountPrefix / 启动钩子
  skeleton_pack/
    __init__.py                    内置默认配置的写法(setdefault)
    routers/demo.py                示例路由:mountPrefix 纪律 + 鉴权依赖用法
    services/demo_service.py       业务层示例(路由薄、服务厚)
    startup.py                     启动钩子示例(异常恢复类逻辑放这)
frontend-sample/
  SkeletonDemoApp.tsx              前端入口组件样例(v0 由 Allo 方编译进基座)
```

## 开始开发你们自己的包

1. 全局替换三个名字:`skeleton_demo` → 你们的 featureKey(小写字母/数字/下划线,与 Allo 方确认后定死)、`skeleton_pack` → 你们的 Python 包名、`/api/skeleton-demo` → 你们的 mountPrefix;
2. 在 `routers/` `services/` 里写业务,独有依赖进 `wheels-requirements.txt` 并按调试方案 §4 装进 `backend-ext/pydeps/`(记得把 `pack_backend.json` 的 `pydeps` 改为 `true`);
3. 迭代循环:改代码 → 重启 Allo → curl;
4. 交付:用 Allo 方提供的 `build_pack.py` 打 zip(指南 §6),发给 Allo 方发布。

## 三条最容易踩的红线

- 所有代码必须在你们声明的 package 目录内,所有路由必须落在 mountPrefix 下——违反 = 整包被跳过(看日志);
- 基座已有的库不进 wheels(反投毒规则,指南 §4);
- 旁加载只是调试通道:客户端界面里**不会**出现你们的工作台卡片(前端 v0 由 Allo 方编入基座后才可见),开发期用 curl / 你们自己的 dev server 联调。
