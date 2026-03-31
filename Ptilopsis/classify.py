# -*- encoding:utf-8 -*-

from Ptilopsis.event.base import Event, MessageData, NoticeData
from Ptilopsis.util import log_output

class Classify:
    type: str = None

    def __init__(self, data: dict):
        self.data = data
        self.bot_id = data["self_id"]
        # print(data)

        # 消息分类
        if data['post_type'] == "message":
            if data['message_type'] == "private":
                self.private_message()
                self.type = "private_message"
            elif data['message_type'] == "group":
                self.group_message()
                self.type = "group_message"
        # 通知分类
        elif data['post_type'] == "notice":
            if data['notice_type'] == "notify":
                if data['sub_type'] == "poke":
                    if data['target_id'] == data['self_id']:
                        if 'group_id' in data:
                            self.group_poke()
                            self.type = "group_poke"
                        else:
                            self.private_poke()
                            self.type = "private_poke"
                elif data['sub_type'] == "sign":
                    self.type = "group_sign"

            elif data['notice_type'] == "group_admin":
                self.type = "group_poke"
            elif data['notice_type'] == "group_decrease":
                if data['sub_type'] == "leave":
                    self.type = "group_poke"

        # 请求分类
        elif data['post_type'] == "request":
            if data['request_type'] == "friend":
                self.type = "group_poke"

        else:
            print("未解析的事件")

    def private_message(self):
        data = MessageData()
        data.user_id = self.data["user_id"]
        data.user_nick = self.data["sender"]["nickname"]
        data.sub_type = self.data["sub_type"]
        data.type = self.data["message"][0]["type"]
        data.message = self.data["raw_message"]
        self.data = data
        log_output("私聊消息 QQ：{} 昵称：{} 内容：{}".format(data.user_id, data.user_nick, data.message))

    def group_message(self):
        data = MessageData()
        data.user_id = self.data["user_id"]
        data.user_nick = self.data["sender"]["nickname"]
        data.group_id = self.data["group_id"]
        data.sub_type = self.data["sub_type"]
        data.type = self.data["message"][0]["type"]
        data.message = self.data["raw_message"]
        self.data = data
        log_output("群聊消息 群号：{} QQ：{} 内容：{}".format(data.group_id, data.user_id, data.message))

    def private_poke(self):
        pass

    def group_poke(self):
        data = NoticeData()
        data.user_id = self.data["user_id"]
        data.group_id = self.data["group_id"]
        self.data = data
        log_output("群戳一戳消息 群号：{} QQ：{} ".format(data.group_id, data.user_id))
        pass

    def result(self):
        result = {
            "bot_id": self.bot_id,
            "type": self.type,
            "data": self.data
        }
        # print(result)
        return result
