"""ShopAide Worker 进程 — 网络感知 + 离线容灾

启动方式:
    python worker.py

架构:
    main_loop() → RedisQueue.pop_blocking() → Agent.invoke()
                     ↑                              ↓ (断网)
              Online / Offline              OfflineRetryQueue.push_task()
                                                ↓ (恢复)
                                          recovery_loop() → pop_pending → Agent
"""

import logging
import os
import signal
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
logger = logging.getLogger("worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OFFLINE_RETRY_MAX = int(os.getenv("OFFLINE_RETRY_MAX", "3"))
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

from shopaide.agent.agent import build_agent
from shopaide.messaging.network_monitor import monitor
from shopaide.messaging.offline_queue import OfflineRetryQueue
from shopaide.messaging.redis_queue import RedisQueue


# ============================================================
# 全局状态
# ============================================================
_agent = None
_queue = None
_offline_queue = None
_recovering = False


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


# ============================================================
# 正常任务处理
# ============================================================
def process_task(task: dict) -> bool:
    """处理单个任务。返回 True=成功, False=需离线暂存。"""
    task_id = task.get("task_id", "unknown")
    user_input = task.get("input", "")
    chat_history = task.get("chat_history", [])

    if not monitor.is_online:
        logger.warning(f"[{task_id}] 网络断开, 任务暂存离线队列: {user_input[:60]}")
        _offline_queue.push_task(task_id, user_input, chat_history)
        return False

    logger.info(f"[{task_id}] 处理中: {user_input[:60]}")
    try:
        agent = get_agent()
        result = agent.invoke({
            "input": user_input,
            "chat_history": chat_history,
        })
        output = result["output"]
    except Exception:
        logger.exception(f"[{task_id}] Agent 执行失败, 暂存离线队列")
        _offline_queue.push_task(task_id, user_input, chat_history)
        return False

    _queue.set_result(task_id, output)
    logger.info(f"[{task_id}] 完成, 回复长度={len(output)}")
    return True


# ============================================================
# 断网恢复 — 逐个重放积压任务
# ============================================================
def recovery_loop():
    """网络恢复时，按 FIFO 顺序重放离线队列中的所有积压任务。"""
    global _recovering
    if _recovering:
        return
    _recovering = True

    pending_count = _offline_queue.pending_count()
    if pending_count == 0:
        logger.info("[Recovery] 离线队列为空, 无需恢复")
        _recovering = False
        return

    logger.warning(
        f"[Recovery] 网络恢复! 开始重放离线队列, "
        f"积压任务数={pending_count}, "
        f"死信数={_offline_queue.dead_count()}"
    )

    success = 0
    fail = 0
    while True:
        task = _offline_queue.pop_pending()
        if task is None:
            break

        task_id = task["task_id"]
        retry_count = task.get("retry_count", 0) + 1
        max_retries = task.get("max_retries", OFFLINE_RETRY_MAX)

        logger.info(f"[Recovery] [{task_id}] 重试 {retry_count}/{max_retries}: {task.get('input', '')[:60]}")

        if retry_count > max_retries:
            _offline_queue.mark_failed(task_id, f"超出最大重试次数 {max_retries}")
            fail += 1
            continue

        try:
            agent = get_agent()
            result = agent.invoke({
                "input": task["input"],
                "chat_history": task.get("chat_history", []),
            })
            _queue.set_result(task_id, result["output"])
            logger.info(f"[Recovery] [{task_id}] 重放成功")
            success += 1
        except Exception:
            logger.exception(f"[Recovery] [{task_id}] 第 {retry_count} 次重试失败")
            # 重新入队（更新 retry_count）
            _offline_queue.repush_with_retry({**task, "retry_count": retry_count})

    logger.warning(
        f"[Recovery] 恢复完成: 成功={success}, 失败(死信)={fail}, "
        f"剩余={_offline_queue.pending_count()}"
    )
    _recovering = False


def on_network_change(online: bool):
    """网络状态变更回调 — 注册到 NetworkMonitor。"""
    if online:
        logger.info("→ 网络恢复, 触发离线队列重放")
        # 在新线程中执行恢复，不阻塞监控
        import threading
        t = threading.Thread(target=recovery_loop, daemon=True)
        t.start()
    else:
        logger.warning("→ 网络断开, 后续任务将自动暂存离线队列")


# ============================================================
# 主循环
# ============================================================
def main():
    logger.info(f"Worker 启动 (离线模式: 重试上限={OFFLINE_RETRY_MAX})")

    global _queue, _offline_queue
    try:
        _queue = RedisQueue(REDIS_URL)
        _offline_queue = OfflineRetryQueue(REDIS_URL, max_retries=OFFLINE_RETRY_MAX)
        _ = _queue.queue_length()
        _ = _offline_queue.pending_count()
    except Exception as e:
        logger.error(f"Redis 连接失败: {e}")
        sys.exit(1)

    # 启动 Agent（延迟初始化）
    agent = get_agent()
    logger.info(f"Agent 已就绪 ({type(agent).__name__})")

    # 注册网络监控回调 + 启动后台轮询
    monitor.on_status_change(on_network_change)
    monitor.start_polling()

    # 如果启动时网络正常, 先恢复任何残留的离线任务
    if monitor.is_online:
        recovery_loop()

    # 主循环: 消费 Redis 任务队列
    logger.info("主循环启动, 等待任务...")
    while True:
        task = _queue.pop_blocking(timeout=5)
        if task is None:
            continue
        process_task(task)


if __name__ == "__main__":
    main()
