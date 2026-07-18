# 商业代码保护示例:编译型 wheel(源码不出门)

把商业逻辑用 Cython 编成原生扩展(mac `.so` / win `.pyd`),打成平台专属 wheel,
放进包目录的 `wheels-local/`,走能力包现成的 wheels 分发通道交付。
`backend-ext/` 里只留一层薄路由 shim,明文交付的部分零商业逻辑。

## 工程结构(照抄改名即可)

```
protected-wheel-example/
  pyproject.toml            # setuptools + Cython 构建后端;name/version 改成你们的
  setup.py                  # COMPILED_MODULES 列出要编译的模块;custom build_py 把 .py 源码挡在 wheel 外
  build_wheel.py            # 一键构建 + 审计(cp312 校验/源码泄漏检查/纯 py wheel 拒收)
  src/demo_biz_core/
    __init__.py             # 唯一入 wheel 的源码:三行 re-export,禁止放逻辑
    engine.py               # 商业逻辑本体 → 编译后源码不进 wheel
```

## 构建(必须在目标平台上跑)

```bash
python3 build_wheel.py     # 有 uv 用 uv build(自动拉 3.12),没有则要求当前解释器就是 3.12
# 产出 dist/<name>-<ver>-cp312-cp312-<平台>.whl,并自动审计
```

**原生扩展不能跨平台编译**:mac 上编出 mac wheel,Windows 上编出 win wheel
(这点和 `--fetch-wheels` 拉 PyPI 现成 wheel"一台机器出双平台包"不同)。
双平台交付 = 在两台机器(或 CI)各跑一次本脚本。

审计规则(`build_wheel.py` 内置,失败即退出):
- wheel 必须带 `cp312` 标签(Allo 基座 runtime 是 Python 3.12;基座升级解释器会提前公告,届时需重编);
- 不许是 `any` 纯 python wheel(说明什么都没编译);
- 除白名单里的 `__init__.py` 外,任何 `.py/.pyx/.pyc/.c` 入包即失败。

## 接入能力包

1. wheel 复制到你们包目录的 `wheels-local/`(mac、win 两个 wheel 可以共存,构建时按平台自动过滤);
2. `pack_backend.json` 里 **`"pydeps": true`**(否则依赖目录不进 sys.path,import 直接炸);
3. `backend-ext/<你们的包>/routers/` 里写薄 shim:

```python
from demo_biz_core import evaluate_bid   # 来自编译 wheel(客户端装进 pydeps)

@router.post("/evaluate")
async def evaluate_api(req: EvaluateRequest) -> dict:
    return evaluate_bid(req.bid, req.base, req.tech, req.credit)
```

4. 正常打包:`python3 build_pack.py <包目录> --version ... --platform darwin --arch arm64 --fetch-wheels`。
   构建脚本会把 `wheels-local/` 里匹配目标平台的 wheel 合并进 `wheels/` 并追加到 requirements;
   **目标平台缺私有 wheel 会直接构建失败**(防止发出缺商业逻辑的残包),这是特性不是 bug。

## 命名与遮蔽

pydeps 是 append 进 sys.path 的:**和基座同名的库会被基座版本遮蔽**。
业务包名用 `<公司>_<产品>_core` 这类不可能撞车的名字,别叫 `utils`/`core`/`engine`。

## 保护强度(诚实版)

- 编译后:源码、注释、数值常量、控制流不可还原;`strings` 只能看到函数名/字符串字面量等符号。
- 对比:`.pyc` 可被 decompyle 近乎完美还原(≈零保护);Cython 编译强一个量级。
- 上限:机器码理论上可逆向(成本高)。**真·核心机密建议留在你们自己的服务器上以 API 形式提供**,包里只放调用方。
- Nuitka 也能产出等价的原生扩展 wheel;协议只约束交付形态(cp312 平台 wheel、无源码泄漏),不锁编译工具。
