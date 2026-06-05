# Agent Handoff — 前端优化（2026-06-05）

## 改动范围

4 个文件，3 次提交，全部在 Chainlit 配置层完成（未触及 Chainlit 内置 React 代码）。

## 逐文件变更

### 1. `chainlit.md` — 欢迎页品牌化

**Before**: Chainlit 默认英文模板（"Welcome to Chainlit!..."）  
**After**: 谷雨 ShopAide 中文欢迎页，含核心能力表、快速上手示例、使用提示  
**动机**: 默认模板与项目无关，用户首次进入会困惑

### 2. `public/style.css` (新建) — 品牌样式表

**内容**:
- 品牌色系：谷雨青 `#0d9488` / `#14b8a6` / `#0f766e`，设 CSS 变量
- 中文字体栈：PingFang SC → Microsoft YaHei → system-ui 降级
- 用户消息气泡：青绿渐变 + 右下小圆角
- AI 消息气泡：白底 + 边框 + 左下小圆角
- 工具 Step：左边框青色高亮
- 输入框聚焦光环、滚动条美化、欢迎页表格样式

**启用方式**: 在 `config.toml` 中设置 `custom_css = "/public/style.css"`

### 3. `.chainlit/config.toml` — UI 布局解锁

| 配置项 | 原值 | 新值 | 效果 |
|--------|------|------|------|
| `default_theme` | (注释) | `"light"` | 统一浅色主题 |
| `language` | (注释) | `"zh-CN"` | 强制中文界面 |
| `layout` | (注释) | `"wide"` | 宽屏利用大屏空间 |
| `default_sidebar_state` | (注释) | `"open"` | 默认展开历史会话列表 |
| `custom_css` | (注释) | `"/public/style.css"` | 加载品牌样式 |

### 4. `app.py` — 欢迎语增强 + 异常兜底

**欢迎语** (`on_chat_start`): 纯文本列表 → Markdown 表格（6 功能模块）+ blockquote 引导语

**异常处理** (`on_message`): `astream_events` 循环外包裹 `try/except Exception`，捕获后：
- `logger.exception()` 记录完整堆栈
- 向用户输出中文友好提示（3 条可能原因 + 人工客服引导）
- 不阻断对话持久化逻辑

## 关键决策

- **不修改 Chainlit React 代码**: 所有 UI 定制通过 TOML 配置 + CSS + Python 事件钩子完成，Chainlit 升级时零冲突
- **品牌色选青绿色系**: 呼应"谷雨"节气，区分于常见蓝/紫色 AI 聊天 UI
- **异常不吞没**: `except` 只包 `astream_events` 流式循环，外层 `msg.update()` 和 `chat_history` 持久化不受影响

## Git 追溯

```
d432108 feat: 欢迎语 Markdown 增强 + Agent 异常捕获与友好错误提示
c8e08b9 feat: 添加品牌 CSS 样式 + UI 布局优化（宽屏/浅色主题/中文/侧边栏展开）
d6acc83 feat: 汉化 chainlit.md 欢迎页 + 创建 CLAUDE.md 知识基座
```
