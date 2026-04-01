import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from Ptilopsis import Core
from Ptilopsis.adapter.console_adapter import ConsoleAdapter
from Ptilopsis.tray import PtilopsisTray

core_instance = None
tray_instance = None
# 【新增】保存主事件循环引用
main_loop = None


async def main():
    global core_instance, tray_instance, main_loop

    # 【新增】保存主事件循环
    main_loop = asyncio.get_running_loop()

    core_instance = Core(config={
        "plugin": {
            "plugin_dir": "plugins",
            "cache_dir": ".cache/plugins",
            "user_config_dir": "config/plugins",
            "allowed_suffixes": [".py", ".pts", ".zip"]
        }
    })

    core_instance.adapter_manager.add_adapter(ConsoleAdapter(core_instance))

    icon_path = str(Path(__file__).parent / "assets" / "ptilopsis_icon.png")
    tray_instance = PtilopsisTray(
        icon_path=icon_path,
        on_quit=on_quit
    )
    tray_instance.start()

    tray_instance.notify("白面鸮已启动", "核心模块加载完成，随时为您服务，博士。")

    await core_instance.start()


def on_quit():
    """【修改】线程安全的优雅退出"""
    global core_instance, tray_instance, main_loop
    print("\n[系统] 正在停止白面鸮...")

    if core_instance and main_loop:
        # 【关键修改】使用线程安全的方式在主事件循环中运行协程
        asyncio.run_coroutine_threadsafe(core_instance.stop(), main_loop)

    if tray_instance:
        tray_instance.stop()

    print("[系统] 白面鸮已停止，博士再见。")
    # 强制退出，避免事件循环问题
    os._exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[系统] 检测到中断信号，正在停止...")
        if tray_instance:
            tray_instance.stop()
        os._exit(0)
    except Exception as e:
        print(f"\n[错误] 程序异常退出: {e}")
        if tray_instance:
            tray_instance.stop()
        os._exit(1)