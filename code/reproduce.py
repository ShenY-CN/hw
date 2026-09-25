"""兼容启动入口；具体实现位于 ``mountain_flood.workflow.reproduce``。"""
if __name__ == "__main__":
    import runpy
    runpy.run_module("mountain_flood.workflow.reproduce", run_name="__main__")
else:
    from mountain_flood.workflow.reproduce import *  # noqa: F401,F403  # 静态检查指令：此处用于兼容重导出
