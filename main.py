import asyncio
from Ptilopsis.core import Core
from Ptilopsis.adapters.console_adapter import ConsoleAdapter

async def main():
    # 初始化核心
    core = Core(config={"plugin_dir": "plugins"})
    # 注册适配器（可添加多个平台的适配器）
    core.adapter_manager.add_adapter(ConsoleAdapter(core))
    # 启动框架
    await core.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止框架...")