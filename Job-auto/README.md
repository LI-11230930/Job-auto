# Job-auto 核心引擎包（`job_agent`）

本目录包含 **Job-auto** 智能求职桌面助手的 Python 后端与核心流水线实现。

## 模块划分

- `job_agent/cli.py`：CLI 子命令与本地独立窗口/桌面端入口（`up` / `start` / `doctor` / `setup` / `run-stage2` / `review` / `weekly-report` 等）。
- `job_agent/db.py` & `job_agent/config.py`：SQLite 持久化存储与基于 Pydantic 的脱敏安全配置加载。
- `job_agent/sources/` & `job_agent/inbox_server.py`：浏览器扩展采岗接收端、校招/公开数据源抓取器与网页 HTML 导入器。
- `job_agent/stage2/`：AI 岗位匹配打分、严格事实核验简历定制与单页 A4 PDF 渲染引擎。
- `job_agent/stage3/`：`FastAPI` 本地工作台后端服务（`review_server.py`）、单文件 UI（`workbench_ui.py`）以及投递进度与状态管理。
- `job_agent/stage4/`：打招呼话术整理、官网自动预填数据包生成与截止提醒周报。
- `job_agent/cloud_relay.py` & `job_agent/relay_mobile_ui.py`：基于 `AES-256-GCM` 的端到端零知识云中转同步客户端与手机审阅前端。
- `job_agent/demo_seed.py`：零 API Key 脱敏演示工作区初始化模块。

完整安装教程、界面展示与日常使用说明请查阅仓库根目录的 [README.md](../README.md)。
