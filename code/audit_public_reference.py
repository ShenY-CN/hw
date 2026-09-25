"""兼容启动入口；具体实现位于 ``mountain_flood.experiments.audit_public_reference``。"""
if __name__ == "__main__":
    import runpy
    runpy.run_module("mountain_flood.experiments.audit_public_reference", run_name="__main__")
else:
    from mountain_flood.experiments.audit_public_reference import *  # noqa: F401,F403  # 静态检查指令：此处用于兼容重导出
