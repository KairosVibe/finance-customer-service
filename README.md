# 金融智能客服系统 customer-service

基于 [dialoguekit](D:\260331_大模型\项目一智能客服-胡中奎\code\dialoguekit) 通用对话框架（已按方案 B 完善流程引擎/动作渲染/上下文机制）构建的金融智能客服服务。

## 能力

- **信息检索**：FAQ 精确层（相似度 ≥ 0.78 直出）+ 知识库语义召回（≥ 0.6，top4）+ RAG 引用回答（[n]）与无依据拒答
- **任务型对话**：账户查询、交易查询、贷款申请、信用卡挂失、投诉工单（写入类带摘要确认 + 风控提示 + 幂等提交）
- **对话管控**：槽位收集、上下文保持（已验证账户自动复用）、流程切换/恢复/取消、业务对象消息自动填槽
- **闲聊兜底**：金融人设 + 业务引导 + 连续 3 轮转人工提示
- **可观测性**：`cs_trace` 记录 intent/tool_call/reply/state 事件 + `request_id` 全链路
- **SSE 流式**：`/api/chat/stream`（status/delta/tool/done 事件）
- **演示页**：`http://127.0.0.1:8100/` 单文件页面（会话管理/流式对话/对象卡片/状态侧栏/调试区）

## 技术栈

Python 3.12+ / uv / FastAPI / SQLAlchemy(async) + aiomysql / LangChain / sentence-transformers（本地 bge-m3）/ DeepSeek(deepseek-chat) / httpx / MySQL

## 启动顺序

前置：MySQL（root/123456）、Python 3.12 + uv。

```bash
# 1. 业务数据底座 finance-data（:8000）
cd D:\260331_大模型\尚硅谷大模型项目实战之电商小二实战-张冬冬\finance-data
uv sync
uv run init_db.py            # 初始化 finance 库
uv run -m generate.main --profile full   # 生成全量样本数据（约 30-60 分钟）
uv run -m app.main           # http://127.0.0.1:8000

# 2. 客服智能层 customer-service（:8100）
cd D:\qianwen\customer-service
uv sync                       # 安装依赖（含 dialoguekit 可编辑路径依赖）
mysql -uroot -p123456 < sql/customer_service.sql   # 建 customer_service 库 5 张表
uv run python -m app.rag.build_index   # 构建知识库索引（加载 bge-m3 向量化）
uv run -m app.main            # http://127.0.0.1:8100（演示页 /）
```

## 验收

```bash
uv run python scripts/demo/acceptance.py   # 覆盖需求第 8 章 5 条验收标准（8/8）
```

## 主要接口

| 接口 | 方法 | 路径 |
|---|---|---|
| 创建会话 | POST | /api/sessions |
| 对话（非流式） | POST | /api/chat |
| 对话（流式 SSE） | POST | /api/chat/stream |
| 历史消息 | GET | /api/sessions/{id}/messages?page_no&page_size |
| 会话状态 | GET | /api/sessions/{id}/state |
| 会话列表 | GET | /api/customers/{customer_no}/sessions |
| 健康检查 | GET | /health |

统一响应：`{"code":0, "message":"ok", "request_id":"...", "data":{...}}`；请求头 `X-Request-Id` 全链路透传。

## 说明

- 大模型：DeepSeek（deepseek-chat，OpenAI 兼容）；向量：本地 bge-m3（`D:\codebuddy\General-PurposeRAG\models\bge-m3`），首次 RAG 查询加载约 25 秒、常驻约 2GB 内存
- 配置见 `.env`（LLM/数据库/finance-data/渠道/员工号，已 gitignore）
- 贷款申请依赖客户授信额度；验收脚本会自动挑选有足够额度的客户，重复演示可能消耗额度

---

## GitHub 提交说明

- 本仓库**不含** `.venv` 虚拟环境、模型文件（bge-m3 在本地 `EMBEDDING_MODEL_PATH` 配置）、密钥（见 `.env.example`）。
- `dialoguekit` 通用对话框架已 vendor 到 `vendor/dialoguekit/`（`pyproject.toml` 通过相对路径引用），克隆后即可 `uv sync` 运行。
- 测试截图见 `docs/screenshots/`（演示页截图 + 验收/质量门禁日志）。

### 从仓库运行（前置：MySQL、Python 3.12+、uv、本地 bge-m3）

```bash
uv sync
mysql -uroot -p123456 < sql/customer_service.sql
cp .env.example .env      # 填入 LLM key / 数据库 / 模型路径
uv run python -m app.rag.build_index
uv run -m app.main        # http://127.0.0.1:8100/
```
