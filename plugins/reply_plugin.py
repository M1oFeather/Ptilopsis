# plugins/reply_plugin.py
from Ptilopsis import BasePlugin, Core, MessageEvent

class ReplyPlugin(BasePlugin):
    plugin_id = "reply_plugin"

    async def load(self, core: Core):
        self.core = core
        # 注册事件监听器，Mod式挂载
        @core.event_bus.listen(MessageEvent, plugin_id=self.plugin_id)
        async def on_message(event: MessageEvent):
            if event.content == "你好":
                await event.reply(f"你好呀！来自{event.adapter.platform}的用户")
            elif event.content == "重载":
                # 测试热重载，无需重启Bot
                await self.core.plugin_manager.reload_plugin(self.plugin_id)
                await event.reply("✅ 插件热重载完成")

    async def unload(self):
        # 清理资源（如异步任务、数据库连接等）
        print(f"reply_plugin 已卸载，资源已清理")