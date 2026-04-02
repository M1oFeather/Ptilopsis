# -*- coding: utf-8 -*-
"""
Ptilopsis Web Panel - Flask Version
使用 Flask + Jinja2 实现管理后台
"""
import os
import json
import time
import asyncio
import psutil
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS
import threading

from .logger import log_manager

# 屏蔽 werkzeug 的日志输出
logging.getLogger('werkzeug').setLevel(logging.ERROR)


class WebPanelManager:
    """Flask Web 面板管理器"""

    def __init__(self, core, host: str = "127.0.0.1", port: int = 8088, debug: bool = False):
        self.core = core
        self.host = host
        self.port = port
        self.debug = debug
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), '..', 'web', 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'web', 'static')
        )
        self.app.secret_key = 'ptilopsis_secret_key_for_session'
        CORS(self.app)
        
        self._setup_routes()
        self._running = False
        self._thread = None

    def _login_required(self, f):
        """登录验证装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def _setup_routes(self):
        """设置路由"""
        
        @self.app.route('/')
        def index():
            """主页"""
            if 'logged_in' not in session:
                return redirect(url_for('login'))
            return render_template('index.html', 
                                   system_status=self._get_system_status(),
                                   plugins=self._get_plugins(),
                                   adapters=self._get_adapters())

        @self.app.route('/login')
        def login():
            """登录页面"""
            return render_template('login.html')

        @self.app.route('/api/login', methods=['POST'])
        def api_login():
            """登录 API"""
            data = request.get_json()
            username = data.get('username', '')
            password = data.get('password', '')
            
            if username == 'admin' and password == 'admin':
                session['logged_in'] = True
                return jsonify({'success': True})
            return jsonify({'success': False, 'message': '账号或密码错误'}), 401

        @self.app.route('/api/logout', methods=['POST'])
        def api_logout():
            """登出 API"""
            session.pop('logged_in', None)
            return jsonify({'success': True})

        @self.app.route('/api/status')
        @self._login_required
        def get_status():
            """获取系统状态"""
            return jsonify(self._get_system_status())

        @self.app.route('/api/plugins')
        @self._login_required
        def get_plugins():
            """获取插件列表"""
            return jsonify({'plugins': self._get_plugins()})

        @self.app.route('/api/plugins/<plugin_id>/toggle', methods=['POST'])
        @self._login_required
        def toggle_plugin(plugin_id):
            """切换插件状态"""
            try:
                if hasattr(self.core, 'plugin_manager'):
                    if plugin_id in self.core.plugin_manager._plugins:
                        return jsonify({'success': True, 'message': '插件状态已切换'})
                return jsonify({'success': False, 'message': '插件不存在'}), 404
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/plugins/<plugin_id>/reload', methods=['POST'])
        @self._login_required
        def reload_plugin(plugin_id):
            """重载插件"""
            try:
                if hasattr(self.core, 'plugin_manager') and hasattr(self.core, 'loop'):
                    self.core.loop.create_task(self.core.plugin_manager.reload_plugin(plugin_id))
                    return jsonify({'success': True, 'message': '插件重载中'})
                return jsonify({'success': False, 'message': '插件管理器不可用'}), 500
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/adapters')
        @self._login_required
        def get_adapters():
            """获取适配器列表"""
            return jsonify({'adapters': self._get_adapters()})

        @self.app.route('/api/adapters/types')
        @self._login_required
        def get_adapter_types():
            """获取可用的适配器类型列表"""
            adapter_types = [
                {
                    'type': 'onebot11',
                    'name': 'OneBot 11',
                    'description': 'OneBot 11 协议适配器，支持QQ机器人'
                },
                {
                    'type': 'onebot12',
                    'name': 'OneBot 12',
                    'description': 'OneBot 12 协议适配器，支持多平台'
                },
                {
                    'type': 'console',
                    'name': '控制台',
                    'description': '控制台适配器，用于测试和调试'
                }
            ]
            return jsonify({'types': adapter_types})

        @self.app.route('/api/adapters/types/<adapter_type>/schema')
        @self._login_required
        def get_adapter_schema(adapter_type):
            """获取指定适配器类型的配置 schema"""
            try:
                if adapter_type == 'onebot11':
                    try:
                        from Ptilopsis.adapter.onebot11 import OneBot11Adapter
                        schema = OneBot11Adapter.get_config_schema()
                    except Exception:
                        schema = []
                elif adapter_type == 'onebot12':
                    try:
                        from Ptilopsis.adapter.onebot12 import OneBot12Adapter
                        schema = OneBot12Adapter.get_config_schema()
                    except Exception:
                        schema = []
                elif adapter_type == 'console':
                    try:
                        from Ptilopsis.adapter.console_adapter import ConsoleAdapter
                        if hasattr(ConsoleAdapter, 'get_config_schema'):
                            schema = ConsoleAdapter.get_config_schema()
                        else:
                            schema = []
                    except Exception:
                        schema = []
                else:
                    return jsonify({'success': False, 'message': '不支持的适配器类型'}), 400
                
                # 将 schema 转换为可序列化的格式
                serializable_schema = []
                for item in schema:
                    item_dict = {
                        'key': item.key,
                        'type': item.type.__name__,
                        'required': item.required,
                        'default': item.default,
                        'description': item.description
                    }
                    if item.choices:
                        item_dict['choices'] = item.choices
                    serializable_schema.append(item_dict)
                
                return jsonify({'success': True, 'schema': serializable_schema})
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/adapters/<adapter_id>/toggle', methods=['POST'])
        @self._login_required
        def toggle_adapter(adapter_id):
            """切换适配器状态"""
            try:
                if hasattr(self.core, 'adapter_manager') and hasattr(self.core, 'loop'):
                    adapter = self.core.adapter_manager.get_adapter(adapter_id)
                    if adapter:
                        if getattr(adapter, 'running', False):
                            self.core.loop.create_task(adapter.stop())
                        else:
                            self.core.loop.create_task(adapter.start())
                        return jsonify({'success': True, 'message': '适配器状态已切换'})
                return jsonify({'success': False, 'message': '适配器不存在'}), 404
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/adapters/<adapter_id>/restart', methods=['POST'])
        @self._login_required
        def restart_adapter(adapter_id):
            """重启适配器"""
            try:
                if hasattr(self.core, 'adapter_manager') and hasattr(self.core, 'loop'):
                    adapter = self.core.adapter_manager.get_adapter(adapter_id)
                    if adapter:
                        async def do_restart():
                            await adapter.stop()
                            await asyncio.sleep(0.5)
                            await adapter.start()
                        self.core.loop.create_task(do_restart())
                        return jsonify({'success': True, 'message': '适配器重启中'})
                return jsonify({'success': False, 'message': '适配器不存在'}), 404
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/adapters/create', methods=['POST'])
        @self._login_required
        def create_adapter():
            """创建新适配器"""
            try:
                data = request.get_json()
                adapter_type = data.get('type')
                adapter_id = data.get('id')
                config = data.get('config', {})

                if not adapter_type or not adapter_id:
                    return jsonify({'success': False, 'message': '类型和ID不能为空'}), 400

                if hasattr(self.core, 'adapter_manager') and hasattr(self.core, 'loop'):
                    adapter = self.core.adapter_manager.create_adapter(
                        adapter_type, adapter_id, config
                    )
                    self.core.loop.create_task(adapter.start())
                    return jsonify({'success': True, 'message': f'适配器 {adapter_id} 已创建并启动'})

                return jsonify({'success': False, 'message': '适配器管理器不可用'}), 500
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/adapters/<adapter_id>/remove', methods=['POST'])
        @self._login_required
        def remove_adapter(adapter_id):
            """移除适配器"""
            try:
                if hasattr(self.core, 'adapter_manager') and hasattr(self.core, 'loop'):
                    adapter = self.core.adapter_manager.get_adapter(adapter_id)
                    if adapter:
                        self.core.loop.create_task(adapter.stop())
                        self.core.adapter_manager.remove_adapter(adapter_id)
                        return jsonify({'success': True, 'message': f'适配器 {adapter_id} 已移除'})
                return jsonify({'success': False, 'message': '适配器不存在'}), 404
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500

        @self.app.route('/api/logs')
        @self._login_required
        def get_logs():
            """获取日志"""
            level = request.args.get('level', '')
            source = request.args.get('source', '')
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            
            result = log_manager.get_logs(level=level, limit=limit, offset=offset)
            return jsonify(result)

        @self.app.route('/api/settings', methods=['GET', 'POST'])
        @self._login_required
        def settings():
            """设置"""
            if request.method == 'GET':
                return jsonify({
                    'web_host': self.host,
                    'web_port': self.port,
                    'log_level': log_manager.get_level()
                })
            else:
                data = request.get_json()
                if 'log_level' in data:
                    log_manager.set_level(data['log_level'])
                return jsonify({'success': True})

    def _get_system_status(self):
        """获取系统状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
        except Exception:
            cpu_percent = 0
            memory = type('', (), {})()
            memory.used = 0
            memory.total = 0
            memory.percent = 0
            disk = type('', (), {})()
            disk.used = 0
            disk.total = 0
            disk.percent = 0
        
        # 计算运行时间
        uptime = time.time() - self.core.start_time if hasattr(self.core, 'start_time') else 0
        
        return {
            'running': True,
            'plugin_count': len(self.core.plugin_manager._plugins) if hasattr(self.core, 'plugin_manager') else 0,
            'adapter_count': len(self.core.adapter_manager._adapters) if hasattr(self.core, 'adapter_manager') else 0,
            'uptime': uptime,
            'uptime_str': self._format_uptime(uptime),
            'version': '2.0.0',
            'system_info': {
                'cpu_percent': cpu_percent,
                'memory_used': memory.used,
                'memory_total': memory.total,
                'memory_percent': memory.percent,
                'disk_used': disk.used,
                'disk_total': disk.total,
                'disk_percent': disk.percent
            }
        }

    def _get_plugins(self):
        """获取插件列表"""
        plugins = []
        if hasattr(self.core, 'plugin_manager'):
            for plugin_id, plugin in self.core.plugin_manager._plugins.items():
                plugins.append({
                    'plugin_id': plugin_id,
                    'name': plugin.plugin_info.get('name', plugin_id),
                    'version': plugin.plugin_info.get('version', '1.0.0'),
                    'description': plugin.plugin_info.get('description', ''),
                    'author': plugin.plugin_info.get('author', 'Unknown'),
                    'enabled': True
                })
        return plugins

    def _get_adapters(self):
        """获取适配器列表"""
        adapters = []
        if hasattr(self.core, 'adapter_manager'):
            for adapter_id, adapter in self.core.adapter_manager._adapters.items():
                # 获取适配器基本信息
                adapter_info = {
                    'adapter_id': adapter_id,
                    'platform': getattr(adapter, 'platform', adapter_id),
                    'name': getattr(adapter, 'NAME', getattr(adapter, 'platform', adapter_id)),
                    'version': getattr(adapter, 'VERSION', '1.0.0'),
                    'running': getattr(adapter, 'running', False),
                    'connection_mode': getattr(adapter, 'connection_mode', 'unknown'),
                    'host': getattr(adapter, 'host', '0.0.0.0'),
                    'port': getattr(adapter, 'port', 0),
                    'config': getattr(adapter, 'config', {})
                }
                
                # 获取适配器能力信息（如果有）
                if hasattr(adapter, 'get_capabilities_summary'):
                    try:
                        adapter_info['capabilities'] = adapter.get_capabilities_summary()
                    except Exception:
                        adapter_info['capabilities'] = {}
                
                # 获取适配器完整信息（如果有）
                if hasattr(adapter, 'get_info'):
                    try:
                        info = adapter.get_info()
                        adapter_info['full_info'] = info
                    except Exception:
                        pass
                
                adapters.append(adapter_info)
        return adapters

    @staticmethod
    def _format_uptime(seconds):
        """格式化运行时间"""
        if not seconds:
            return '0秒'
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if days > 0:
            return f'{days}天{hours}时{minutes}分'
        elif hours > 0:
            return f'{hours}时{minutes}分{secs}秒'
        return f'{minutes}分{secs}秒'

    def start(self):
        """启动 Web 服务"""
        if self._running:
            return
        
        self._running = True
        
        # 临时重定向输出，屏蔽 Flask 启动信息
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        def run_flask():
            try:
                self.app.run(
                    host=self.host,
                    port=self.port,
                    debug=self.debug,
                    use_reloader=False,
                    threaded=True
                )
            finally:
                # 恢复输出
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        
        self._thread = threading.Thread(target=run_flask)
        self._thread.daemon = True
        self._thread.start()
        
        # 短暂等待后恢复输出，确保我们的日志能正常显示
        import time
        time.sleep(0.1)
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        log_manager.info(f"服务已启动，访问地址: http://{self.host}:{self.port}", "框架", "Web后端")

    def stop(self):
        """停止 Web 服务"""
        self._running = False
        log_manager.info("服务已停止", "框架", "Web后端")
