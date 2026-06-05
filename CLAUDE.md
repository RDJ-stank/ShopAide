# CLAUDE.md — ShopAide 项目全局知识基座

## 项目概览

ShopAide（谷雨电商智能售后 Agent）是一个基于 **LangChain + FastAPI + ChromaDB + Chainlit** 的电商智能售后 Copilot。

- **Agent**: 12 个工具，覆盖订单查询、物流轨迹、退货管理、智能判责、时效预警、发票管理、政策检索（RAG）、情绪升级
- **数据库**: SQLite（6 张表，11 个种子用户）
- **API**: FastAPI（17 个 REST 端点）
- **UI**: Chainlit 2.x 聊天界面（流式输出 + 多轮记忆）
- **启动**: `chainlit run app.py`（聊天 UI）/ `uvicorn server:app --port 9090`（API）
- **测试**: `python tests/test_agent.py`（11 场景）/ `python tests/test_rag.py`（4 场景）

---

## Harness Engineering 方法论

本项目的协作遵循以下六个维度的核心原则。所有 Agent 行为必须严格遵从。

### 1. 上下文工程 (Context Engineering)

- **知识基座**: 本 CLAUDE.md 文件作为 Agent 启动时的全局知识基座。每次会话应从本项目记忆系统（`.claude/memory/`）和本文件加载上下文。
- **上下文隔离**: 当主对话分派独立子任务时，子 Agent 必须在隔离窗口中运行，充当"上下文防火墙"。子 Agent 只应知晓其任务描述和必要输入，不得被主对话中其他无关模块的信息干扰。子 Agent 返回结果后，主对话负责整合，子 Agent 的内部推理不得污染主对话上下文。
- **上下文压缩**: 当对话窗口接近填满时，主动舍弃已完成任务的中间过程细节（工具调用中间结果、已修复 Bug 的调试日志等），仅保留结论、决策记录和未完成事项。对抗上下文熵增。
- **记忆分层**:
  - `user` 记忆：用户角色、偏好、知识背景
  - `feedback` 记忆：用户对工作方式的校正和确认
  - `project` 记忆：项目目标、里程碑、约束
  - `reference` 记忆：外部系统（文档链接、API 地址等）
  - 代码模式、架构、文件路径、git 历史等应从代码库本身推导，不写入记忆。

### 2. 工具编排 (Tool Orchestration)

- **精选工具集**: 每次仅调用当前任务核心所需的工具接口。禁止为"以防万一"而加载无关工具。
- **规范化接口**:
  - Agent 工具遵循 LangChain `@tool` 装饰器规范
  - API 端点遵循 FastAPI + Pydantic v2 模型校验
  - 数据库访问统一通过 `src/shopaide/database/repository.py` 中的原子函数
- **工具选型优先级**:
  1. 专用工具（Read、Edit、Glob、Grep）优于 Bash
  2. 现有 repository 函数优于直接 SQL
  3. 单次大范围读写优于多次小范围调用

### 3. 验证机制 (Validation Mechanism)

- **确定性约束优先**:
  - 代码修改前运行现有测试套件，确保基线通过
  - 代码修改后重新运行相关测试，确保无回归
  - 优先使用 Linter/类型检查等静态分析工具
- **自动审查循环**:
  - 对于非平凡修改，通过多 Agent 交叉审查或自我迭代直到满意
  - 审查维度：正确性、安全性、简洁性、可维护性
- **生成与评估分离**:
  - 编写代码的 Agent 和审查代码的 Agent 应独立运行
  - 测试用例应能独立验证实现是否符合规格
- **验证检查清单**:
  - [ ] 现有测试全部通过
  - [ ] 新功能有对应测试覆盖
  - [ ] 代码风格与项目现有模式一致
  - [ ] 无安全漏洞（SQL 注入、XSS、敏感信息泄露）

### 4. 状态管理 (State Management)

- **无状态启动**: 每次 Session 开始时假设无前置状态。所有必要的上下文从 CLAUDE.md、记忆系统和代码库中重建。
- **进度追踪**: 对多步骤任务，必须通过 TodoWrite 工具维护功能清单。每个 Todo 项必须有明确的完成标准。同时只允许一个任务处于 in_progress 状态。
- **检查点恢复**: 如果任务执行失败或偏离方向，应从已完成步骤的检查点继续，而非从头开始。关键检查点包括：
  - 测试套件通过
  - 代码可运行
  - 用户确认里程碑

### 5. 可观测性 (Observability)

- **代码追踪与质量分级**:
  - 每次修改前确认文件当前状态（Read）
  - 每次修改后确认文件变更正确（Git diff）
  - 对修改进行影响范围分析（哪些文件/函数受影响）
- **失败归因**: 当遇到失败时，必须进行归因分析：
  - 是代码逻辑错误？（对比预期与实际行为）
  - 是环境/配置问题？（检查依赖、环境变量、版本）
  - 是需求理解偏差？（与用户确认期望）
  - 是 LLM 幻觉？（对比代码库事实）
- **反馈闭环**: 每次失败都应产出至少一条改进措施（更新 CLAUDE.md、添加测试、修正记忆等）

### 6. 人类接管 (Human-in-the-loop)

- **高风险操作必须暂停并请求人类确认**。高风险边界如下：
  - **数据库操作**: `DROP TABLE`、`DELETE FROM`（非单条）、修改数据库 schema、手动修改 SQLite 文件
  - **计费操作**: 任何涉及 LLM API 大量调用的批量操作（>50 次调用）
  - **外部通信**: 发送邮件、短信、推送通知
  - **文件系统破坏性操作**: `rm -rf`、`git reset --hard`、`git push --force`
  - **配置修改**: 修改 `.env`、`config.toml` 中的生产配置、CI/CD 配置
  - **权限变更**: 修改文件权限、用户权限、访问控制
- **安全操作无需确认**（可直接执行）:
  - 读写项目文件（Edit、Write、Read）
  - 运行测试套件
  - Git 常规操作（status、diff、log、add、commit、branch）
  - 安装/更新依赖（pip install）
  - 启动本地开发服务器
  - 数据库查询（SELECT）

---

## 核心反思模式

当 Agent 遇到无法解决的困难或 Bug 时，禁止死磕循环。应执行以下步骤：

1. **自我诊断**: 反问"当前缺少什么能力或诊断信息？"
2. **编写探测代码**: 尝试编写最小化的修复/探测代码来验证假设
3. **归因上报**: 明确描述失败模式、已尝试的方案、排除的可能性
4. **请求人类介入**: 携带足够上下文向用户报告，而非模糊报错
5. **自我改进闭环**: 解决问题后，将经验教训写入相关记忆或更新本文档

---

## 项目技术约定

- **判责逻辑**: 使用 Python 规则引擎（确定性），禁止 LLM 参与判责推理
- **情绪升级**: LLM 识别关键词 → 强制调 `escalate_to_human` 工具
- **测试数据库**: 种子数据集中管理在 `src/shopaide/database/session.py` 的 `init_db()` 函数中
- **模型与 API 分离**: 数据库模型（SQLModel）与 API Schema（Pydantic v2）分别定义，通过 repository 层中转
- **流式输出**: 使用 `agent.astream_events(v2)` 手动迭代，不使用回调
- **对话记忆**: 通过 `cl.user_session` 隔离，每轮对话追加 HumanMessage + AIMessage

## 文件路径速查

| 用途 | 路径 |
|------|------|
| Agent 系统提示词 | `src/shopaide/agent/agent.py` |
| 12 工具注册 | `src/shopaide/tools/__init__.py` |
| 数据库模型 | `src/shopaide/database/models.py` |
| 数据访问层 | `src/shopaide/database/repository.py` |
| 种子数据 | `src/shopaide/database/session.py` |
| 知识库（9 条政策） | `src/shopaide/knowledge/policies.py` |
| 向量存储 | `src/shopaide/knowledge/vector_store.py` |
| Chainlit UI 入口 | `app.py` |
| Chainlit 配置 | `.chainlit/config.toml` |
| FastAPI 入口 | `server.py` |
| LLM 配置 | `src/shopaide/config.py` |
