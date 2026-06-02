"""ShopAide Chainlit 前端 — 可视化聊天界面

启动方式:
    chainlit run app.py

首次启动前需先构建向量库:
    python -c "from shopaide.knowledge.vector_store import build_vector_store; \
               from shopaide.knowledge.policies import POLICIES; \
               build_vector_store(POLICIES)"
"""

import chainlit as cl

from shopaide.agent.agent import build_agent
from shopaide.knowledge.vector_store import get_retriever


@cl.on_chat_start
async def on_chat_start():
    """用户首次进入会话时，初始化 Agent 并存入 session"""
    # 确保向量库已初始化（幂等操作）
    get_retriever()

    agent = build_agent()
    cl.user_session.set("agent", agent)

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
    """处理用户消息，交给 Agent 执行"""
    agent: cl.user_session.get("agent")

    # 将消息发给 Agent（Chainlit 会自动处理 tool_call / final_answer 的渲染）
    result = agent.invoke({"input": message.content})

    await cl.Message(content=result["output"]).send()
