from Ptilopsis import *


class TestPlugin(BasePlugin):
    plugin_id = "test"
    async def load(self):
        # 测试pre阶段
        @self.on(MessageEvent, phase="pre")
        async def pre_check(event: MessageEvent):
            if event.content == "阻断":
                event.stop_propagation()
                await event.reply("事件已被阻断")

        # 测试normal阶段，自动继承优先级
        @self.on(MessageEvent)
        async def reply(event: MessageEvent):
            if event.content == "你好":
                await event.reply(self.config.get("reply_text", "你好呀"))

        # 测试post阶段
        @self.on(MessageEvent, phase="post", ignore_cancelled=True)
        async def log(event: MessageEvent):
            print(f"[日志] 收到消息：{event.content}")

    async def unload(self):
        pass