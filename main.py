# main.py
import asyncio
import os
import sys
import multiprocessing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 首先初始化日志系统
from Ptilopsis.logger import log_manager, info, error

from Ptilopsis import Core
from Ptilopsis.adapter.console_adapter import ConsoleAdapter
from Ptilopsis.tray import PtilopsisTray
from Ptilopsis.web_panel import WebPanelManager

# 延迟导入 GUI，避免在异步环境中初始化 Qt
gui_module = None
ModernGUIPanel = None

core_instance = None
tray_instance = None
web_panel_instance = None
gui_panel_instance = None
main_loop = None

async def main():
    global core_instance, tray_instance, main_loop, web_panel_instance, gui_panel_instance

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
    web_panel_instance.start()

    # 2. 启动托盘图标，绑定 GUI 面板唤起动作
    icon_path = str(Path(__file__).parent / "assets" / "ptilopsis_icon.png")
    # 检查图标文件是否存在
    if not os.path.exists(icon_path):
        log_manager.warning(f"托盘图标文件不存在: {icon_path}", "框架", "托盘")
        log_manager.info("白面鸮已启动，核心模块加载完成。", "框架", "核心")
    else:
        tray_instance = PtilopsisTray(
            icon_path=icon_path,
            on_quit=on_quit,
            on_open_panel=open_gui_panel
        )
        tray_instance.start()
        tray_instance.notify("白面鸮已启动", "核心模块加载完成，双击托盘可打开控制面板。")

    # 3. 启动 Bot 核心
    await core_instance.start()

def open_gui_panel():
    """打开 GUI 控制面板 - 在新线程中运行 Qt 应用"""
    global gui_panel_instance, core_instance
    
    if gui_panel_instance is not None:
        # 如果已存在，直接显示
        gui_panel_instance.start()
        return
    
    # 延迟导入并创建 GUI
    import threading
    
    def run_gui():
        global gui_panel_instance
        from PyQt5.QtWidgets import QApplication
        from Ptilopsis.gui_panel import ModernGUIPanel
        
        # 创建 QApplication（必须在主线程中）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            app.setStyle('Fusion')
        
        # 创建 GUI 面板
        gui_panel_instance = ModernGUIPanel(core_instance, on_quit=on_quit)
        gui_panel_instance.show()
        
        # 运行事件循环
        app.exec_()
    
    # 在新线程中启动 GUI
    gui_thread = threading.Thread(target=run_gui, daemon=True)
    gui_thread.start()

def on_quit():
    """线程安全的优雅退出"""
    global core_instance, tray_instance, main_loop, web_panel_instance, gui_panel_instance
    info("正在停止白面鸮...", "System")

    if core_instance and main_loop:
        async def shutdown_all():
            if web_panel_instance:
                web_panel_instance.stop()
            if gui_panel_instance:
                gui_panel_instance.stop()
            await core_instance.stop()

        asyncio.run_coroutine_threadsafe(shutdown_all(), main_loop)

    if tray_instance:
        tray_instance.stop()

    info("白面鸮已停止，博士再见。", "System")
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
        import traceback
        traceback.print_exc()
        on_quit()
