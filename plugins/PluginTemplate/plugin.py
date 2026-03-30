# plugins/hello_plugin/plugin.py
from Ptilopsis import BasePlugin, MessageEvent


class HelloPlugin(BasePlugin):
    plugin_id = "hello_plugin"

    async def load(self):
        # 注册事件监听器，绑定当前插件ID
        @self.core.event_bus.listen(MessageEvent, plugin_id=self.plugin_id)
        async def on_message(event: MessageEvent):
            # 用配置项控制开关
            if event.is_group and not self.config["enable_group"]:
                return
            if not event.is_group and not self.config["enable_private"]:
                return

            # 匹配关键词
            if event.content.strip() == "你好":
                # 直接使用配置里的回复文本
                await event.reply(self.config["reply_text"])

            # 测试热重载
            elif event.content.strip() == "重载你好插件":
                await self.core.plugin_manager.reload_plugin(self.plugin_id)
                await event.reply("✅ 你好插件热重载完成")

    async def unload(self):
        # 清理资源，这里没有额外资源，只需打印日志即可
        print(f"[{self.plugin_id}] 已卸载，所有监听器已自动清理")