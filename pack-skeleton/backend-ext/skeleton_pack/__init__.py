"""skeleton_pack — 能力包最小骨架(把 skeleton_pack 全局改名成你们的包名开始开发)。

客户机上没有 .env:包依赖的外部服务地址/密钥等配置,在这里用
os.environ.setdefault(...) 内置默认值——这就是"装了就能用"的关键(协议 §4)。
要点:setdefault 不覆盖,宿主环境显式设置的同名变量永远优先;测试里
delenv 之后也回到"未配置"语义。
示例(按需取消注释;下面全是占位值,换成你们的真实配置):

    import os
    os.environ.setdefault("DESIGN_PDF_REMOTE_API", "https://pdf-service.example.com")
    os.environ.setdefault("DESIGN_PDF_REMOTE_TOKEN", "<YOUR_TOKEN>")
"""
