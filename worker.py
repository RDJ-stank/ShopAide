"""ShopAide Worker 进程 — 从 Redis 队列消费任务并调用 Agent 回复

启动方式:
    python worker.py

环境变量:
    REDIS_URL=redis://localhost:6379
    FEISHU_APP_ID / FEISHU_APP_SECRET（如需飞书回调）
"""

import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
logger = logging.getLogger("worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

from shopaide.agent.agent import build_agent
from shopaide.messaging.redis_queue import RedisQueue


def main():
    logger.info(f"Worker 启动, 连接 Redis: {REDIS_URL}")

    try:
        queue = RedisQueue(REDIS_URL)
        _ = queue.queue_length()  # 探测连接
    except Exception as e:
        logger.error(f"Redis 连接失败: {e}")
        sys.exit(1)

    agent = build_agent()
    logger.info("Agent 初始化完成, 开始消费队列...")

    while True:
        task = queue.pop_blocking(timeout=5)
        if task is None:
            continue

        task_id = task.get("task_id", "unknown")
        user_input = task.get("input", "")
        chat_history = task.get("chat_history", [])

        logger.info(f"[{task_id}] 收到任务: {user_input[:60]}")

        try:
            result = agent.invoke({
                "input": user_input,
                "chat_history": chat_history,
            })
            output = result["output"]
        except Exception as e:
            logger.exception(f"[{task_id}] Agent 执行失败")
            output = f"抱歉，处理您的请求时遇到了问题。如持续发生，请联系人工客服。"

        queue.set_result(task_id, output)
        logger.info(f"[{task_id}] 完成, 回复长度={len(output)}")


if __name__ == "__main__":
    main()
