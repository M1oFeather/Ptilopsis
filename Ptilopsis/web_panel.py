# Ptilopsis/web_panel.py
import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import jwt

SECRET_KEY = "ptilopsis_secure_key_for_jwt_256bits_v1"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


class ConnectionManager:
    """WebSocket 连接管理器，用于实时推送日志"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


class WebSocketLogHandler(logging.Handler):
    """自定义日志处理器，将日志实时通过 WebSocket 推送给前端"""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop

    def emit(self, record):
        msg = self.format(record)
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(msg), self.loop)


# ==================== 数据模型 ====================
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PluginConfigRequest(BaseModel):
    config: Dict[str, Any]


# ==================== 核心面板管理器 ====================
class WebPanelManager:
    def __init__(self, core, host: str = "127.0.0.1", port: int = 8088):
        self.core = core
        self.host = host
        self.port = port

        self.app = FastAPI(title="Ptilopsis Web Panel", version="1.0.0")

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.server: Optional[uvicorn.Server] = None
        self._setup_routes()

    def _setup_routes(self):
        router = APIRouter(prefix="/api")

        def verify_token(token: str):
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                if payload.get("sub") != "admin":
                    raise HTTPException(status_code=401, detail="无效的凭证")
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token已过期")
            except jwt.PyJWTError:
                raise HTTPException(status_code=401, detail="鉴权失败")
            return True

        # --- 前端页面挂载 ---
        @self.app.get("/")
        async def serve_frontend():
            frontend_path = os.path.join(os.getcwd(), "web", "index.html")
            if not os.path.exists(frontend_path):
                return {"error": "Frontend web/index.html not found"}
            return FileResponse(frontend_path)

        # --- 1. 认证接口 ---
        @router.post("/auth/login", response_model=TokenResponse)
        async def login(req: LoginRequest):
            if req.username == "admin" and req.password == "admin":
                expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                token = jwt.encode({"sub": req.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
                return {"access_token": token}
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        @router.get("/auth/verify")
        async def verify(token: str):
            verify_token(token)
            return {"status": "ok"}

        # --- 2. 状态接口 ---
        @router.get("/system/status")
        async def get_status(token: str):
            verify_token(token)
            return {
                "running": self.core._running,
                "plugin_count": len(self.core.plugin_manager._plugins),
                "adapter_count": len(self.core.adapter_manager._adapters)
            }

        # --- 3. 插件管理接口 ---
        @router.get("/plugins")
        async def list_plugins(token: str):
            verify_token(token)
            result = []
            for plugin_id, meta in self.core.plugin_manager._plugin_meta.items():
                plugin = self.core.plugin_manager._plugins[plugin_id]
                base_path = meta.get("base_path", "")

                is_blockly = False
                if base_path and os.path.exists(os.path.join(base_path, "blockly_workspace.json")):
                    is_blockly = True

                result.append({
                    "plugin_id": plugin_id,
                    "name": plugin.plugin_info.get("name", plugin_id),
                    "version": plugin.plugin_info.get("version", "unknown"),
                    "priority": plugin.plugin_priority,
                    "type": meta["type"],
                    "is_blockly": is_blockly,
                    "config": plugin.config
                })
            return result

        @router.post("/plugins/{plugin_id}/reload")
        async def reload_plugin(plugin_id: str, token: str):
            verify_token(token)
            try:
                success = await self.core.plugin_manager.reload_plugin(plugin_id)
                if success:
                    return {"message": f"插件 {plugin_id} 已热重载"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            raise HTTPException(status_code=404, detail="插件重载失败")

        @router.post("/plugins/{plugin_id}/unload")
        async def unload_plugin(plugin_id: str, token: str):
            verify_token(token)
            try:
                success = await self.core.plugin_manager.unload_plugin(plugin_id)
                if success:
                    return {"message": f"插件 {plugin_id} 已卸载"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            raise HTTPException(status_code=404, detail="插件卸载失败")

        # --- 4. 适配器管理接口 ---
        @router.get("/adapters")
        async def list_adapters(token: str):
            verify_token(token)
            result = []
            for adp_id, adp in self.core.adapter_manager._adapters.items():
                result.append({
                    "adapter_id": adp_id,
                    "platform": adp.platform,
                    "running": getattr(adp, "_running", False)
                })
            return result

        @router.post("/adapters/{adapter_id}/toggle")
        async def toggle_adapter(adapter_id: str, action: str, token: str):
            verify_token(token)
            adp = self.core.adapter_manager.get_adapter(adapter_id)
            if not adp:
                raise HTTPException(status_code=404, detail="适配器不存在")

            try:
                if action == "start":
                    await adp.start()
                    return {"message": f"适配器 {adapter_id} 已启动"}
                elif action == "stop":
                    await adp.stop()
                    return {"message": f"适配器 {adapter_id} 已停止"}
                else:
                    raise HTTPException(status_code=400, detail="无效操作")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        self.app.include_router(router)

        # --- 5. 实时日志 WebSocket 接口 ---
        @self.app.websocket("/api/logs/ws")
        async def websocket_logs(websocket: WebSocket):
            await ws_manager.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                ws_manager.disconnect(websocket)

    async def start(self):
        loop = asyncio.get_running_loop()
        log_handler = WebSocketLogHandler(loop)
        log_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))

        # 将根日志和内建print统一转发
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="error",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        asyncio.create_task(self.server.serve())
        print(f"[Web后端] 服务已启动，桌面/网页访问地址: http://{self.host}:{self.port}")

    async def stop(self):
        if self.server:
            self.server.should_exit = True
            print(f"[Web后端] 服务已安全关闭")