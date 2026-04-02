# -*- coding: utf-8 -*-
"""
OneBot 适配器基类 - OneBot 11/12 共用
包含 4 种连接方式的通用实现
"""
import asyncio
import json
from typing import Dict, Any, Optional, List
from aiohttp import web, ClientSession

from .base import BaseAdapter, AdapterFeature, ConfigSchemaItem
from ..logger import info, warning, error, debug


class OneBotAdapter(BaseAdapter):
    """OneBot 协议适配器基类 - 11/12 共用"""
    
    # 连接模式
    CONNECTION_MODES = [
        "websocket_reverse",
        "websocket_forward", 
        "webhook",
        "http"
    ]
    
    def __init__(self, core, config: Dict[str, Any] = None):
        super().__init__(core, config)
        
        # 连接模式配置
        self.connection_mode = self.config.get("connection_mode", "websocket_reverse")
        
        # 通用配置 - 支持 host/port 或 ws_host/ws_port
        self.host = self.config.get("host", self.config.get("ws_host", "0.0.0.0"))
        self.port = self.config.get("port", self.config.get("ws_port", 8080))
        self.access_token = self.config.get("access_token", "")
        
        # HTTP/WebSocket 服务和客户端
        self._web_app: Optional[web.Application] = None
        self._web_runner: Optional[web.AppRunner] = None
        self._web_site: Optional[web.TCPSite] = None
        self._ws_client: Optional[ClientSession] = None
        self._ws_connection: Optional[web.WebSocketResponse] = None
        self._forward_ws: Optional[Any] = None
        
        # API 请求队列，用于同步响应
        self._api_requests: Dict[str, asyncio.Future] = {}
        self._next_echo = 1
    
    @classmethod
    def get_config_schema(cls) -> List[ConfigSchemaItem]:
        """获取配置项定义"""
        return [
            ConfigSchemaItem(
                key="connection_mode",
                type=str,
                required=False,
                default="websocket_reverse",
                description="连接模式",
                choices=cls.CONNECTION_MODES
            ),
            ConfigSchemaItem(
                key="host",
                type=str,
                required=False,
                default="0.0.0.0",
                description="监听/连接地址"
            ),
            ConfigSchemaItem(
                key="port",
                type=int,
                required=False,
                default=8080,
                description="监听/连接端口"
            ),
            ConfigSchemaItem(
                key="access_token",
                type=str,
                required=False,
                default="",
                description="访问令牌"
            ),
            ConfigSchemaItem(
                key="adapter_id",
                type=str,
                required=False,
                default="",
                description="适配器唯一ID"
            )
        ]
    
    async def start(self):
        """启动适配器"""
        if self.connection_mode == "websocket_reverse":
            await self._start_reverse_websocket()
        elif self.connection_mode == "websocket_forward":
            await self._start_forward_websocket()
        elif self.connection_mode == "webhook":
            await self._start_webhook()
        elif self.connection_mode == "http":
            await self._start_http()
        else:
            raise ValueError(f"不支持的连接模式: {self.connection_mode}")
        
        self.running = True
        info(f"{self.NAME} 适配器启动成功，模式: {self.connection_mode}", "适配器", self.adapter_id)
    
    async def stop(self):
        """停止适配器"""
        self.running = False
        
        try:
            # 关闭正向 WebSocket
            if self._forward_ws:
                await self._forward_ws.close()
            if self._ws_client:
                await self._ws_client.close()
            
            # 关闭 Web 服务
            if self._web_runner:
                await self._web_runner.cleanup()
            
            # 取消所有待处理的请求
            for future in self._api_requests.values():
                if not future.done():
                    future.cancel()
            self._api_requests.clear()
            
        except Exception as e:
            error(f"停止 {self.NAME} 适配器时出错: {e}", "适配器", self.adapter_id)
        
        info(f"{self.NAME} 适配器已停止", "适配器", self.adapter_id)
    
    # ========== 反向 WebSocket 模式 ==========
    async def _start_reverse_websocket(self):
        """启动反向 WebSocket 服务"""
        self._web_app = web.Application()
        self._web_app.router.add_get("/", self._handle_reverse_ws)
        
        self._web_runner = web.AppRunner(self._web_app)
        await self._web_runner.setup()
        self._web_site = web.TCPSite(self._web_runner, self.host, self.port)
        await self._web_site.start()
        
        info(f"反向 WebSocket 服务已启动: ws://{self.host}:{self.port}", "适配器", self.adapter_id)
    
    async def _handle_reverse_ws(self, request):
        """处理反向 WebSocket 连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_connection = ws
        
        info(f"{self.NAME} Bot 已连接", "适配器", self.adapter_id)
        
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._handle_message(json.loads(msg.data))
                elif msg.type == web.WSMsgType.ERROR:
                    error(f"WebSocket 错误: {ws.exception()}", "适配器", self.adapter_id)
        finally:
            self._ws_connection = None
            info(f"{self.NAME} Bot 已断开", "适配器", self.adapter_id)
        
        return ws
    
    # ========== 正向 WebSocket 模式 ==========
    async def _start_forward_websocket(self):
        """启动正向 WebSocket"""
        self._ws_client = ClientSession()
        url = f"ws://{self.host}:{self.port}"
        if self.access_token:
            url += f"?access_token={self.access_token}"
        
        # 持续尝试重连
        asyncio.create_task(self._forward_ws_loop(url))
    
    async def _forward_ws_loop(self, url: str):
        """正向 WebSocket 连接循环"""
        while self.running:
            try:
                info(f"正在连接到 {self.NAME} Bot: {url}", "适配器", self.adapter_id)
                self._forward_ws = await self._ws_client.ws_connect(url)
                info(f"已连接到 {self.NAME} Bot", "适配器", self.adapter_id)
                
                async for msg in self._forward_ws:
                    if msg.type == web.WSMsgType.TEXT:
                        await self._handle_message(json.loads(msg.data))
                    elif msg.type == web.WSMsgType.ERROR:
                        error(f"WebSocket 错误", "适配器", self.adapter_id)
                
            except Exception as e:
                error(f"正向 WebSocket 连接失败: {e}", "适配器", self.adapter_id)
                if self.running:
                    await asyncio.sleep(3)
    
    # ========== WebHook 模式 ==========
    async def _start_webhook(self):
        """启动 WebHook 服务"""
        self._web_app = web.Application()
        self._web_app.router.add_post("/", self._handle_webhook)
        
        self._web_runner = web.AppRunner(self._web_app)
        await self._web_runner.setup()
        self._web_site = web.TCPSite(self._web_runner, self.host, self.port)
        await self._web_site.start()
        
        info(f"WebHook 服务已启动: http://{self.host}:{self.port}", "适配器", self.adapter_id)
    
    async def _handle_webhook(self, request):
        """处理 WebHook 上报"""
        try:
            data = await request.json()
            await self._handle_message(data)
            return web.json_response({"status": "ok"})
        except Exception as e:
            error(f"处理 WebHook 失败: {e}", "适配器", self.adapter_id)
            return web.json_response({"status": "error"}, status=500)
    
    # ========== HTTP API 模式 ==========
    async def _start_http(self):
        """启动 HTTP API 模式"""
        self._ws_client = ClientSession()
        info(f"HTTP API 模式已就绪: http://{self.host}:{self.port}", "适配器", self.adapter_id)
    
    # ========== 消息处理和 API 调用 ==========
    async def _handle_message(self, data: Dict[str, Any]):
        """处理收到的消息 - 子类应重写"""
        debug(f"收到 {self.NAME} 消息: {data}", "适配器", self.adapter_id)
    
    async def call_action(self, action: str, **params) -> Dict[str, Any]:
        """调用 OneBot API"""
        echo = str(self._next_echo)
        self._next_echo += 1
        
        payload = {
            "action": action,
            "params": params,
            "echo": echo
        }
        
        future = asyncio.get_event_loop().create_future()
        self._api_requests[echo] = future
        
        try:
            if self.connection_mode in ["websocket_reverse", "websocket_forward"]:
                await self._send_websocket(payload)
                return await asyncio.wait_for(future, timeout=30)
            else:
                return await self._send_http(payload)
        except asyncio.TimeoutError:
            self._api_requests.pop(echo, None)
            raise TimeoutError(f"API 调用超时: {action}")
        except Exception as e:
            self._api_requests.pop(echo, None)
            raise
    
    async def _send_websocket(self, payload: Dict[str, Any]):
        """通过 WebSocket 发送请求"""
        ws = self._ws_connection if self.connection_mode == "websocket_reverse" else self._forward_ws
        if ws is None:
            raise RuntimeError("WebSocket 未连接")
        
        await ws.send_json(payload)
    
    async def _send_http(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """通过 HTTP 发送请求"""
        url = f"http://{self.host}:{self.port}/{payload['action']}"
        headers = {"Content-Type": "application/json"}
        
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        async with self._ws_client.post(url, json=payload["params"], headers=headers) as resp:
            return await resp.json()
    
    # ========== OneBot 通用能力 ==========
    def _init_capabilities(self) -> set:
        """初始化 OneBot 通用能力"""
        return {
            AdapterFeature.SEND_PRIVATE_MESSAGE,
            AdapterFeature.SEND_GROUP_MESSAGE,
            AdapterFeature.DELETE_MESSAGE,
            AdapterFeature.GET_MESSAGE,
            AdapterFeature.GET_USER_INFO,
            AdapterFeature.GET_FRIEND_LIST,
            AdapterFeature.GET_GROUP_INFO,
            AdapterFeature.GET_GROUP_LIST,
            AdapterFeature.GET_GROUP_MEMBER_INFO,
            AdapterFeature.GET_GROUP_MEMBER_LIST,
            AdapterFeature.SET_GROUP_KICK,
            AdapterFeature.SET_GROUP_BAN,
            AdapterFeature.SET_GROUP_WHOLE_BAN,
            AdapterFeature.SET_GROUP_ADMIN,
            AdapterFeature.SET_GROUP_CARD,
            AdapterFeature.SET_GROUP_NAME,
            AdapterFeature.SET_GROUP_LEAVE,
            AdapterFeature.HANDLE_FRIEND_REQUEST,
            AdapterFeature.HANDLE_GROUP_REQUEST,
            AdapterFeature.GET_STATUS,
            AdapterFeature.GET_VERSION,
            AdapterFeature.GET_SUPPORTED_ACTIONS,
        }
