# main.py
import asyncio
import os
import sys
import multiprocessing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from Ptilopsis import Core
from Ptilopsis.adapter.console_adapter import ConsoleAdapter
from Ptilopsis.tray import PtilopsisTray
from Ptilopsis.web_panel import WebPanelManager
from Ptilopsis.desktop_panel import open_desktop_panel

core_instance = None
tray_instance = None
web_panel_instance = None
main_loop = None

async def main():
    global core_instance, tray_instance, main_loop, web_panel_instance

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

    # 1. 启动 Web 后端
    web_panel_instance = WebPanelManager(core_instance, host="127.0.0.1", port=8088)
    await web_panel_instance.start()

    # 2. 启动托盘图标，并绑定桌面面板唤起动作
    icon_path = str(Path(__file__).parent / "assets" / "ptilopsis_icon.png")
    tray_instance = PtilopsisTray(
        icon_path=icon_path,
        on_quit=on_quit,
        on_open_panel=open_desktop_panel
    )
    tray_instance.start()
    tray_instance.notify("白面鸮已启动", "核心模块加载完成，双击托盘可打开控制面板。")

    # 3. 启动 Bot 核心
    await core_instance.start()

def on_quit():
    """线程安全的优雅退出"""
    global core_instance, tray_instance, main_loop, web_panel_instance
    print("\n[系统] 正在停止白面鸮...")

    if core_instance and main_loop:
        async def shutdown_all():
            if web_panel_instance:
                await web_panel_instance.stop()
            await core_instance.stop()

        asyncio.run_coroutine_threadsafe(shutdown_all(), main_loop)

    if tray_instance:
        tray_instance.stop()

    print("[系统] 白面鸮已停止，博士再见。")
    os._exit(0)

if __name__ == "__main__":
    # Windows 下 multiprocessing 必须包含 freeze_support
    multiprocessing.freeze_support()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        on_quit()
    except Exception as e:
        print(f"\n[错误] 程序异常退出: {e}")
        on_quit()