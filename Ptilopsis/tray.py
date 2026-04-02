# Ptilopsis/tray.py
import os
import threading
import pystray
from PIL import Image
from typing import Optional, Callable

class PtilopsisTray:
    def __init__(
            self,
            icon_path: str,
            on_quit: Optional[Callable] = None,
            on_toggle_console: Optional[Callable] = None,
            on_open_panel: Optional[Callable] = None  # 【新增】回调
    ):
        self.icon_path = icon_path
        self.on_quit = on_quit
        self.on_toggle_console = on_toggle_console
        self.on_open_panel = on_open_panel
        self.icon: Optional[pystray.Icon] = None
        self.thread: Optional[threading.Thread] = None
        self._console_visible = True

    def _load_image(self) -> Image.Image:
        if os.path.exists(self.icon_path):
            return Image.open(self.icon_path)
        else:
            return self._create_default_icon()

    def _create_default_icon(self) -> Image.Image:
        from PIL import ImageDraw, ImageFont
        img = Image.new('RGB', (64, 64), color='#409eff')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        draw.text((18, 10), "P", fill="white", font=font)
        return img

    def _quit_action(self, icon, item):
        icon.stop()
        if self.on_quit:
            self.on_quit()

    def _toggle_console_action(self, icon, item):
        self._console_visible = not self._console_visible
        if self.on_toggle_console:
            self.on_toggle_console(self._console_visible)
        else:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5 if self._console_visible else 0)

    def _open_panel_action(self, icon, item):
        """【新增】菜单点击：打开桌面控制面板"""
        if self.on_open_panel:
            self.on_open_panel()

    def _create_menu(self) -> pystray.Menu:
        """【修改】添加控制面板菜单项"""
        return pystray.Menu(
            pystray.MenuItem("打开 Web 控制面板", self._open_panel_action, default=True),
            pystray.MenuItem(
                "显示/隐藏控制台",
                self._toggle_console_action,
                checked=lambda item: self._console_visible
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出 Ptilopsis", self._quit_action)
        )

    def start(self):
        image = self._load_image()
        menu = self._create_menu()
        self.icon = pystray.Icon(name="Ptilopsis", icon=image, title="白面鸮 Bot 框架", menu=menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()
        print("[托盘] 白面鸮任务栏角标已启动")

    def stop(self):
        if self.icon:
            self.icon.stop()
        print("[托盘] 白面鸮任务栏角标已停止")

    def notify(self, title: str, message: str):
        if self.icon:
            self.icon.notify(message, title)