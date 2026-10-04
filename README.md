# EasyNovel 小说创作工作站

Windows x64 本地桌面应用，作者审核规划、正文与记忆后入库。使用自带的模型 API，支持中文连载与精品小说两种模式。

## 当前启动方式

本机的 Windows 应用程序控制策略阻止 Rust 构建脚本运行（错误 4551），桌面安装包尚未构建成功。可先运行浏览器开发工作台：

本机已配置好依赖，双击桌面的 **EasyNovel** 快捷方式，或根目录 **启动.cmd**。会自动启动本地服务、打开浏览器并连接，不需要复制会话令牌。保留启动窗口，关闭窗口即可退出；重复启动复用同一实例。

端口占用时自动选择可用端口；重复启动也能找到使用其他端口的实例。数据目录有后台进程锁，避免连续点击或手工启动产生两个后台同时使用同一作品库。

命令行可用 `./scripts/start-browser.ps1 -OpenBrowser`。服务只监听回环地址。当前浏览器运行需要 `.venv`、Node.js 和前端依赖；新电脑首次配置运行 `./scripts/setup.ps1`。可用 `./scripts/create-shortcut.ps1` 创建桌面快捷方式。详细操作见 [上手说明](docs/USAGE.md)。

完整桌面构建在允许运行构建程序的 Windows 环境中执行 `./scripts/build.ps1`，安装包输出到 `apps/desktop/src-tauri/target/release/bundle/nsis/`。项目提供 Windows CI 工作流，但本次尚未执行远程 CI。构建成功后的桌面用户无需安装 Python、Node.js 或 Rust。

## 创作流程

1. 新建作品，或导入 TXT / Markdown 并检查分章边界。
2. 在“设置”添加 OpenAI-compatible 服务、密钥和实际模型 ID；可按智能体指定模型与提示词。密钥存系统凭据库。价格未知时使用 token 上限，费用以供应商账单为准。
3. 确认人物、世界规则、时间线、认知、计划和伏笔。计划与正文事实分别检索。
4. 创建或选择章节，在作者导演中输入本章要求、选择模型并设置预算。默认「直接写正文」自动完成规划、写作和审稿，中央显示正文候选；满意后选择性确认正文与记忆入库。「先审核计划」保留逐步导演流程。「整理创作指令」只产生候选约束卡，不生成正文。
5. 不满意时展开「让 AI 按要求修改」，输入具体改稿要求并生成修改稿；原稿和历史保留，修改稿再次审核入库。也可以返回编辑器手工改稿。修改已确认正文或设定时查看影响清单，受影响章节可以改稿修复，正式续写仍须等待修复或核查。

工作流支持暂停、取消、恢复，自动修订最多两轮。网络调用结果不确定时保留预算和账本，避免静默重复付费。硬约束超过模型容量会暂停。场景按视角和故事时间分别构建上下文。

新任务默认 200000 Token，保留用户自选额度。任务 Token 上限是所有调用的累计额度；模型与角色的「单次输出上限」决定每次回答最多多长。总额度设为 1000000 不会提高单次输出上限。因单次输出截断暂停时，在恢复窗口提高对应角色和模型的输出上限（例如 8192），不能只增加总预算。原输出和已用消耗会保留，截断内容不会当作完整成果入库。更新后端代码后，先关闭旧启动窗口，再双击启动；新会话自动连接，已有作品和任务仍在本地库中。

## 数据与恢复

默认目录 `%LOCALAPPDATA%\EasyNovel`；权威库 `studio.sqlite3`，检索索引可重建。完整备份包含正文、版本、资料、运行与检查点，不含 API 密钥。自动备份保留七份，手动备份不清理。升级迁移前生成备份。

原目录 `ai_novel_studio.db` 不被修改。迁移先备份旧库，在新库建立草稿与待核查记忆；旧摘要不会成为已确认事实。

## 开发与测试

开发环境：Python 3.12、Node.js 24、Rust MSVC、Windows C++ Build Tools。

```powershell
./scripts/setup.ps1
./.venv/Scripts/python.exe -m pytest
npm.cmd --prefix apps/web test -- --run
npm.cmd --prefix apps/web run build
./.venv/Scripts/python.exe scripts/benchmark.py
./scripts/build.ps1
```

`./scripts/build.ps1 -BackendOnly` 仅生成后端可执行文件；`./start.ps1 -Development` 启动 Tauri 开发桌面。`scripts/live_smoke.py` 读取环境变量 `DEEPSEEK_API_KEY` 调用 `deepseek-flash`，会产生供应商费用。测试数据隔离在 `artifacts/live-smoke/`，默认任务上限 100000 tokens。

目录：`easynovel/` 领域服务与工作流；`apps/web/` React/Tiptap 工作台；`apps/desktop/` Tauri 壳；`migrations/` 迁移；`tests/` 测试。接口见 [API_CONTRACT](docs/API_CONTRACT.md)，设计见 [DESIGN](.ulpi/design/DESIGN.md)。

核心创作闭环已实现。专业版本的验收结果及未完成要求见 [ACCEPTANCE](docs/ACCEPTANCE.md)。模型审稿和合成规模数据不能替代长期连载与读者盲评。

2026-10-03 的完整写作、读稿修订、界面和启动回归见 [本次验收报告](docs/QA-2026-10-03.md)。三种题材各两章的真实模型样章包含作者意见和逐句细修，不代表无人审核的成稿质量。
