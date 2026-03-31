# Ptilopsis Bot Framework
> 「核心模块加载完成，白面鸮为您服务，博士。」
> 
> 基于Python开发的模块化、高扩展、二次元向Bot开发框架，以明日方舟干员「白面鸮(Ptilopsis)」为看板娘，为您提供稳定、高效、低门槛的Bot开发体验。

---

## 📖 项目介绍
本项目以明日方舟干员白面鸮的英文名「Ptilopsis」命名，是专为二次元场景打造的轻量级Bot开发框架。采用分层解耦设计，完美适配多平台对接、插件化业务开发、热重载更新、事件驱动调度等核心需求，无论是群聊娱乐、功能管理还是二创内容推送，都能快速实现。

> 「已为您完成框架初始化，所有功能模块均通过稳定性测试，无宕机风险。」

---

## ✨ 核心特性
### 🧠 核心算力模块 - 分层解耦架构
采用「适配器层-核心运行时-事件总线-插件层」四层解耦架构，逻辑边界清晰，扩展维护便捷，底层算力稳定输出，杜绝业务逻辑与核心框架耦合。

### 🔌 多平台适配协议 - 适配器模式
内置标准化适配器抽象层，一键对接QQ、Kook、Discord、Telegram等二次元主流社交平台。原生平台事件自动转换为框架标准事件，实现**一次开发，多平台运行**。

### 📦 热插拔插件系统
业务功能完全基于插件模式开发，支持三种插件格式：
- 单文件 `.py` 插件
- 文件夹结构化插件
- 自定义后缀压缩包插件（`.pts`/`.zip`）

支持无重启热加载/卸载/重载，更新功能无需停服，就像白面鸮随时更新医疗方案一样灵活高效。

### ⚡ 事件总线调度系统
完全复刻Mod开发的事件驱动模式，核心能力：
- `pre/normal/post` 三阶段固定执行顺序，解决优先级冲突场景
- 插件全局优先级配置，同阶段内按优先级顺序执行
- 事件取消/传播阻断双机制，精准控制事件流转
- 插件卸载自动清理所有监听器，无内存泄漏风险

### 🎨 可视化开发编辑器
配套基于Electron+Blockly开发的可视化插件编辑器，支持：
- 低代码积木式插件开发，零Python基础也能上手
- Monaco Editor专业代码编辑环境，内置框架语法补全
- 内置对话测试平台，无需启动外部服务即可调试插件
- 插件配置可视化编辑、资源文件一键管理

---

## 🚀 快速开始
### 环境要求
- Python 3.10 及以上版本
- 操作系统：Windows/macOS/Linux 全平台兼容

### 1. 克隆项目
```bash
git clone https://github.com/M1oFeather/Ptilopsis.git
cd Ptilopsis
```

### 2. 安装依赖
```bash
# 使用pip安装
pip install -r requirements.txt

# 或使用Pipfile
pipenv install
```

### 3. 启动框架
```bash
python main.py
```

启动成功后，控制台将输出以下内容，代表框架正常运行：
```
[插件] 示例插件加载成功
[适配器] console 启动成功
✅ Ptilopsis 框架启动成功
[输入消息]:
```

### 4. 第一个插件示例
在 `plugins/` 目录下创建 `hello_白面鸮` 文件夹，结构如下：
```
hello_白面鸮/
├── plugin.py
└── config.json
```

`config.json`
```json
{
    "plugin_id": "hello_白面鸮",
    "name": "白面鸮问候插件",
    "version": "1.0.0",
    "author": "博士",
    "priority": 10,
    "default_config": {
        "reply_text": "博士，你好呀，白面鸮随时为您服务。"
    }
}
```

`plugin.py`
```python
from Ptilopsis import *

class HelloPlugin(BasePlugin):
    async def load(self):
        @self.on(MessageEvent)
        async def on_message(event: MessageEvent):
            if event.content.strip() == "你好白面鸮":
                await event.reply(self.config["reply_text"])

    async def unload(self):
        print(f"[{self.plugin_id}] 已卸载，博士再见。")
```

重启框架后，输入`你好白面鸮`，即可收到白面鸮的回复。

---

## 📁 项目结构
```
Ptilopsis/                   # 框架核心根包
├── __init__.py              # 统一导出接口
├── core.py                  # 核心运行时，生命周期管理
├── event/                   # 事件系统子包
│   ├── __init__.py
│   ├── base.py              # 事件基类定义
│   └── bus.py               # 事件总线核心
├── plugin/                  # 插件系统子包
│   ├── __init__.py
│   ├── base.py              # 插件基类定义
│   ├── manager.py           # 插件生命周期管理
│   └── archive.py           # 压缩包插件处理器
└── adapter/                 # 适配器系统子包
    ├── __init__.py
    ├── base.py              # 适配器基类定义
    └── manager.py           # 适配器生命周期管理

plugins/                     # 用户插件目录，所有业务插件存放于此
config/                      # 用户插件配置目录，与插件包解耦
main.py                      # 框架入口文件
README.md
LICENSE
Pipfile
```

---

## 🤝 贡献指南
「欢迎博士为本项目提交贡献，白面鸮会为您记录所有提交日志。」

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

如果您发现框架bug、有功能建议，也可以直接提交Issue，白面鸮会尽快响应并处理。

---

## 📄 许可证
本项目采用 **GPL-3.0** 许可证开源，详见 [LICENSE](LICENSE) 文件。

---

> 「已为您记录本次README阅读完成，博士。如果本项目对您有帮助，不妨点个Star，白面鸮会将您记录在功勋墙上。」
> 
> 「系统提示：工作再忙，也要记得按时休息。」