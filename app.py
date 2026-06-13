"""ShopAide Chainlit 前端 — 流式输出 + 多轮记忆

启动方式:
    chainlit run app.py
"""

import logging
import os

import chainlit as cl
from langchain_core.messages import AIMessage, HumanMessage

from shopaide.config import settings

# ---- Sentry 错误监控（可选，未配 SENTRY_DSN 则跳过） ----
if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            environment=os.getenv("ENV", "development"),
        )
        logging.getLogger("sentry_sdk").setLevel(logging.WARNING)
    except ImportError:
        pass

from shopaide.agent.agent import build_agent
from shopaide.knowledge.vector_store import get_retriever

logger = logging.getLogger(__name__)


@cl.on_chat_start
async def on_chat_start():
    """用户进入会话：初始化 Agent、历史记录为空、发送欢迎语"""
    get_retriever()

    agent = build_agent()
    cl.user_session.set("agent", agent)
    cl.user_session.set("chat_history", [])

    await cl.Message(
        content=(
            "## 你好！我是谷雨，你的电商售后助手\n\n"
            "| 功能 | 说明 |\n"
            "|------|------|\n"
            "| 订单查询 | 查订单状态、物流轨迹、商品详情 |\n"
            "| 退货管理 | 提交退货申请、查询退货进度 |\n"
            "| 发票服务 | 查询发票状态、补开发票 |\n"
            "| 智能判责 | 破损/少件自动定责分流 |\n"
            "| 时效预警 | 延迟发货/物流停滞检测 |\n"
            "| 政策咨询 | 退货/保修/价保政策检索 |\n\n"
            "> 直接输入问题即可开始，支持多轮上下文对话"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """处理用户消息 —— 流式输出 + 多轮对话上下文"""
    agent = cl.user_session.get("agent")
    chat_history: list = cl.user_session.get("chat_history")

    # 创建一个空消息作为流式输出的容器
    msg = cl.Message(content="")
    await msg.send()

    full_answer = ""

    # 跟踪当前活跃的 Step（工具调用），用于流式写入工具输出
    active_steps: dict[str, cl.Step] = {}

    # astream_events 是 LangChain 原生异步流式 API，
    # 每次 LLM 产出 token 或工具开始/结束都会产出事件
    try:
        async for event in agent.astream_events(
            {"input": message.content, "chat_history": chat_history},
            version="v2",
        ):
            kind = event["event"]

            # LLM 生成 token → 逐字追加到聊天界面
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    full_answer += content
                    await msg.stream_token(content)

            # 工具开始调用 → 创建侧边栏 Step（用户主界面看不到）
            elif kind == "on_tool_start":
                tool_name = event["name"]
                tool_input = event["data"].get("input", {})
                step = cl.Step(
                    name=tool_name,
                    type="tool",
                    parent_id=msg.id,
                )
                step.input = str(tool_input)
                step.output = ""
                await step.send()
                active_steps[tool_name] = step

            # 工具返回结果 → 写入对应 Step 的 output
            elif kind == "on_tool_end":
                tool_name = event["name"]
                tool_output = event["data"].get("output", "")
                if tool_name in active_steps:
                    step = active_steps.pop(tool_name)
                    step.output = str(tool_output)
                    await step.update()
    except Exception:
        logger.exception("Agent 执行异常")
        full_answer = (
            "抱歉，处理您的请求时遇到了问题。\n\n"
            "可能的原因：\n"
            "- 后端服务暂时不可用\n"
            "- 请求超时，请尝试简化问题重试\n\n"
            "如问题持续，请联系人工客服获得帮助。"
        )
        await msg.stream_token(full_answer)

    # 流式完成，标记消息结束
    await msg.update()

    # 持久化本轮对话
    if full_answer:
        chat_history.append(HumanMessage(content=message.content))
        chat_history.append(AIMessage(content=full_answer))
        cl.user_session.set("chat_history", chat_history)
