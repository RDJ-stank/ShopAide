"""ShopAide Chainlit 前端 — 流式输出 + 多轮记忆

启动方式:
    chainlit run app.py
"""

import chainlit as cl
from chainlit import AsyncLangchainCallbackHandler
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

    # 配置 Chainlit 回调处理器：
    # - stream_final_answer=True → token 级别逐字渲染
    # - 工具调用中间步骤自动展示在界面侧边
    cb = AsyncLangchainCallbackHandler(
        stream_final_answer=True,
    )

    # cl.make_async 将同步 agent.invoke 放入线程池，
    # callbacks 由 LangChain 内部分发给 AsyncLangchainCallbackHandler
    result = await cl.make_async(agent.invoke)(
        {
            "input": message.content,
            "chat_history": chat_history,
        },
        {"callbacks": [cb]},
    )

    answer = result["output"]

    # 持久化本轮对话到 session（下次提问时作为上下文传入）
    chat_history.append(HumanMessage(content=message.content))
    chat_history.append(AIMessage(content=answer))
    cl.user_session.set("chat_history", chat_history)
