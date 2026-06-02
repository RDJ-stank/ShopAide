"""ShopAide Chainlit 前端 — 流式输出 + 多轮记忆

启动方式:
    chainlit run app.py
"""

import chainlit as cl
from langchain_core.messages import AIMessage, HumanMessage

from shopaide.agent.agent import build_agent
from shopaide.knowledge.vector_store import get_retriever


@cl.on_chat_start
async def on_chat_start():
    """用户进入会话：初始化 Agent、历史记录为空、发送欢迎语"""
    get_retriever()

    agent = build_agent()
    cl.user_session.set("agent", agent)
    cl.user_session.set("chat_history", [])

    await cl.Message(
        content=(
            "你好！我是谷雨，你的电商售后助手。\n\n"
            "我可以帮你：\n"
            "- 查询订单物流状态\n"
            "- 修改收货地址\n"
            "- 解答退换货政策与售后规则\n\n"
            "请问有什么可以帮你的？"
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

    # astream_events 是 LangChain 原生异步流式 API，
    # 不依赖任何 Chainlit 回调，token 级别逐个产出事件
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

        # 工具开始调用 → 在界面展示步骤
        elif kind == "on_tool_start":
            tool_name = event["name"]
            tool_input = event["data"].get("input", {})
            await cl.Message(
                content=f"🔧 调用工具: `{tool_name}`\n参数: {tool_input}",
                author="System",
            ).send()

        # 工具返回结果 → 展示在可折叠面板中
        elif kind == "on_tool_end":
            tool_output = event["data"].get("output", "")
            await cl.Message(
                content=f"📋 工具返回:\n```\n{tool_output}\n```",
                author="System",
            ).send()

    # 流式完成，标记消息结束
    await msg.update()

    # 持久化本轮对话
    if full_answer:
        chat_history.append(HumanMessage(content=message.content))
        chat_history.append(AIMessage(content=full_answer))
        cl.user_session.set("chat_history", chat_history)
