# AI Novel Studio

AI 驱动的小说生产工作流系统，基于 LangChain/LangGraph 构建。

## 项目概述

AI Novel Studio 是一个半自动工业化写作系统，旨在提高小说创作生产力，同时保持人工审核和创意控制。

### 核心特性

- **多 Agent 协作**：10+ 个专业 Agent 协同工作
- **质量保证**：多层次质量评估和人工审核
- **版本控制**：完整的版本历史和对比功能
- **记忆系统**：6 类记忆确保长期一致性
- **可扩展架构**：支持多种模型和平台

### 技术栈

- **后端**：FastAPI + SQLAlchemy
- **工作流**：LangGraph
- **数据库**：SQLite（开发）/ PostgreSQL（生产）
- **模型**：DeepSeek 默认，支持 OpenAI-compatible API 配置
- **前端**：React + TypeScript 本地工作台

## 项目结构

```
ai-novel-studio/
├── apps/
│   ├── api/          # FastAPI 后端
│   └── web/          # React 前端
├── packages/
│   ├── database/     # 数据库模型
│   ├── workflow/     # LangGraph 工作流
│   ├── agents/       # Agent 实现
│   ├── memory/       # 记忆系统
│   ├── models/       # 模型网关
│   ├── prompts/      # Prompt 模板
│   └── evals/        # 质量评估
├── projects/         # 小说项目数据
├── tests/            # 测试代码
└── docs/             # 文档
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd ai-novel-studio

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install poetry
poetry install
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑 .env 文件，配置以下变量：
# MODEL_API_KEY=your_model_api_key
# MODEL_BASE_URL=https://api.deepseek.com/v1
# MODEL_FLASH=deepseek-v4-flash
# MODEL_PRO=deepseek-v4-pro
# DATABASE_URL=sqlite:///./ai_novel_studio.db
```

### 3. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head
```

### 4. 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=packages --cov-report=html
```

### 5. 启动服务

```bash
# 启动 FastAPI 后端
cd apps/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端
cd apps/web
npm install
npm start
```

也可以在 Windows 下直接运行：

```powershell
.\start.ps1
```

本地发布版支持章节版本化保存、世界观/人物/风格/时间线/伏笔设定库、模型配置检查、成本摘要，以及 TXT/Markdown 导出。

## 核心工作流

### 工作流 1：新建小说项目

```
IdeaAgent → MarketFitAgent → StoryBibleAgent → CharacterAgent 
→ VolumeOutlineAgent → StyleGuideAgent → HumanReview
```

### 工作流 2：生成单章

```
选择 chapter_id → ContextPackBuilder → ChapterPlannerAgent 
→ HumanReview（章节卡确认）→ DraftWriterAgent → PlotEditorAgent 
→ HumanStylePolisherAgent → ContinuityAuditorAgent → QualityJudgeAgent 
→ HumanReview（润色稿确认）→ MemoryUpdater → HumanReview（发布确认）
```

## Agent 列表

| Agent | 职责 | 模型 |
|-------|------|------|
| StoryBible Agent | 建立维护世界观规则 | deepseek-v4-pro |
| Character Agent | 创建维护人物状态卡 | deepseek-v4-pro |
| Chapter Planner Agent | 输出结构化章节卡 | deepseek-v4-pro |
| Draft Writer Agent | 按章节卡写初稿 | deepseek-v4-flash |
| Plot Editor Agent | 检查故事质量 | deepseek-v4-pro |
| HumanStylePolisher Agent | 清除 AI 味，增强人类风格 | deepseek-v4-pro |
| Continuity Auditor Agent | 检查设定一致性 | deepseek-v4-flash |
| Quality Judge Agent | 多维度质量评分 | deepseek-v4-pro |
| Editor-in-Chief Agent | 方向判断 | deepseek-v4-pro |

## 记忆系统

| 记忆类型 | 用途 | 存储格式 |
|----------|------|----------|
| Canon Memory | 硬设定库 | YAML |
| Timeline Memory | 时间线 | JSON |
| Character State | 人物状态 | JSON |
| Foreshadowing Ledger | 伏笔账本 | JSON |
| Style Memory | 文风记忆 | JSON |
| Chapter Vector | 章节语义检索 | Vector DB |

## 质量评估体系

### 评分维度

- **plot_progression**：剧情推进
- **conflict_strength**：冲突强度
- **character_consistency**：人物一致性
- **style_naturalness**：语言自然度
- **dialogue_quality**：对话质量
- **hook_strength**：章末钩子
- **continuity_safety**：连续性安全
- **cliche_density**：套话密度

### 自动拦截规则

- 连续性冲突未解决
- 人物知道不该知道的信息
- 新增重大设定但没入库
- 章末没有钩子
- 润色改变剧情事实
- 大量模板化句子
- 字数明显低于目标

## 开发指南

### 添加新 Agent

1. 在 `packages/agents/` 目录下创建新 Agent 文件
2. 实现 Agent 类，继承基础 Agent 类
3. 在 `packages/workflow/nodes/` 中添加工作流节点
4. 编写单元测试
5. 更新文档

### 添加新模型

1. 在 `packages/models/` 目录下创建模型客户端
2. 实现统一的模型接口
3. 在模型路由中注册新模型
4. 编写测试用例

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 测试

### 测试结构

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
└── e2e/            # 端到端测试
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/unit/test_database_models.py -v

# 运行带标记的测试
python -m pytest -m unit
python -m pytest -m integration
```

### 测试覆盖率

```bash
# 生成覆盖率报告
python -m pytest tests/ --cov=packages --cov-report=html

# 查看覆盖率报告
start htmlcov/index.html
```

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t ai-novel-studio .

# 运行容器
docker run -p 8000:8000 ai-novel-studio
```

### 生产环境配置

1. 使用 PostgreSQL 替代 SQLite
2. 配置 pgvector 进行向量检索
3. 设置 Redis 缓存
4. 配置 Nginx 反向代理
5. 设置 SSL 证书

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目链接：https://github.com/your-username/ai-novel-studio
- 问题反馈：https://github.com/your-username/ai-novel-studio/issues

## 致谢

- LangChain/LangGraph 团队
- DeepSeek API
- FastAPI 社区
- SQLAlchemy 社区
