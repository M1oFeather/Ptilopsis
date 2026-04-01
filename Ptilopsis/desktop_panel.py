# Ptilopsis/desktop_panel.py
import subprocess
import sys

_process = None


def open_desktop_panel(url: str = "http://127.0.0.1:8088"):
    """
    打开桌面控制面板（单例模式）
    使用 subprocess 隔离启动，彻底解决 Windows 下 stdin 阻塞导致窗口卡死的问题
    """
    global _process

    # 检查进程是否存在且尚未退出
    if _process is not None and _process.poll() is None:
        print("\n[桌面端] 窗口已存在，请在任务栏查找。")
        print("[输入消息]: ", end="", flush=True)
        return

    script_code = f"""
import webview
webview.create_window(
    title='Ptilopsis 控制面板', 
    url='{url}', 
    width=1024, 
    height=720,
    resizable=True,
    text_select=True
)
webview.start(private_mode=False)
"""

    # 彻底阻断与父进程（控制台）的句柄继承
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    # 仅在 Windows 系统下隐藏后台的黑色 cmd 窗口
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    _process = subprocess.Popen([sys.executable, "-c", script_code], **kwargs)

    print("\n[桌面端] 已成功唤起桌面控制面板。")
    print("[输入消息]: ", end="", flush=True)