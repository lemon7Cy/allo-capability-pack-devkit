"""skeleton_pack — 能力包最小骨架(把 skeleton_pack 全局改名成你们的包名开始开发)。

客户机上没有 .env:包依赖的外部服务地址/密钥等配置,在这里用
os.environ.setdefault(...) 内置默认值——宿主环境显式设置的同名变量永远优先。
示例(按需取消注释并改成你们的真实配置):

    import os
    os.environ.setdefault("ALLO_DESIGN_RENDER_API", "http://your-service:8080")
"""
