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

    # 跟踪当前活跃的 Step（工具调用），用于流式写入工具输出
    active_steps: dict[str, cl.Step] = {}

    # astream_events 是 LangChain 原生异步流式 API，
    # 每次 LLM 产出 token 或工具开始/结束都会产出事件
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
            # 用 parent_id 将 Step 挂在当前消息下，界面侧边栏可折叠查看
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

    # 流式完成，标记消息结束
    await msg.update()

    # 持久化本轮对话
    if full_answer:
        chat_history.append(HumanMessage(content=message.content))
        chat_history.append(AIMessage(content=full_answer))
        cl.user_session.set("chat_history", chat_history)
