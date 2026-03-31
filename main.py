# main.py 启动示例
import asyncio
from Ptilopsis.core import Core
from Ptilopsis.adapter.console_adapter import ConsoleAdapter

async def main():
    # 初始化核心，配置插件系统
    core = Core(config={
        "plugin": {
            "plugin_dir": "plugins",          # 插件存放目录
            "cache_dir": ".cache/plugins",    # 压缩包插件缓存目录
            "user_config_dir": "config/plugins",  # 用户自定义配置目录
            # 允许的插件后缀，可自定义，比如把.pts改成.myplugin
            "allowed_suffixes": [".py", ".pts", ".zip"]
        }
    })
    # 注册适配器
    core.adapter_manager.add_adapter(ConsoleAdapter(core))
    # 启动框架
    await core.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止框架...")