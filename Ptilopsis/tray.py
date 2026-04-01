import os
import sys
import threading
import pystray
from PIL import Image
from typing import Optional, Callable


class PtilopsisTray:
    """
    白面鸮任务栏角标管理类
    """

    def __init__(
            self,
            icon_path: str,
            on_quit: Optional[Callable] = None,
            on_toggle_console: Optional[Callable] = None
    ):
        self.icon_path = icon_path
        self.on_quit = on_quit
        self.on_toggle_console = on_toggle_console
        self.icon: Optional[pystray.Icon] = None
        self.thread: Optional[threading.Thread] = None
        self._console_visible = True

    def _load_image(self) -> Image.Image:
        """加载图标文件"""
        if os.path.exists(self.icon_path):
            return Image.open(self.icon_path)
        else:
            # 如果图标文件不存在，生成一个简单的占位图标
            return self._create_default_icon()

    def _create_default_icon(self) -> Image.Image:
        """生成默认占位图标（蓝色背景+白色P字母）"""
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
        """退出程序"""
        icon.stop()
        if self.on_quit:
            self.on_quit()

    def _toggle_console_action(self, icon, item):
        """显示/隐藏控制台"""
        self._console_visible = not self._console_visible
        if self.on_toggle_console:
            self.on_toggle_console(self._console_visible)
        else:
            # 默认实现：Windows下显示/隐藏控制台
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5 if self._console_visible else 0)

    def _create_menu(self) -> pystray.Menu:
        """创建右键菜单"""
        return pystray.Menu(
            pystray.MenuItem(
                "显示/隐藏控制台",
                self._toggle_console_action,
                checked=lambda item: self._console_visible
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出 Ptilopsis", self._quit_action)
        )

    def start(self):
        """启动托盘图标（在新线程中运行）"""
        image = self._load_image()
        menu = self._create_menu()

        self.icon = pystray.Icon(
            name="Ptilopsis",
            icon=image,
            title="白面鸮 Bot 框架",
            menu=menu
        )

        # 在新线程中运行托盘图标，避免阻塞主线程
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()
        print("[托盘] 白面鸮任务栏角标已启动")

    def stop(self):
        """停止托盘图标"""
        if self.icon:
            self.icon.stop()
        print("[托盘] 白面鸮任务栏角标已停止")

    def notify(self, title: str, message: str):
        """发送系统通知（Windows 10+）"""
        if self.icon:
            self.icon.notify(message, title)