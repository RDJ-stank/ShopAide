"""离线任务队列 — Redis 持久化 + 重试 + 死信队列

海上平台弱网场景：断网时任务暂存 Redis，恢复后自动重放。
超出最大重试次数的任务移入 dead_letter 队列，留着人工排查。

用法:
    off_queue = OfflineRetryQueue(redis_url)
    off_queue.push_task({"input": "查物流", "chat_history": []})
    ...
    task = off_queue.pop_pending()
    off_queue.mark_success(task_id)
"""

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_OFFLINE_KEY = "shopaide:offline_retry"
_DEAD_KEY = "shopaide:dead_letter"
_DEFAULT_MAX_RETRIES = 3


class OfflineRetryQueue:
    def __init__(self, redis_url: str, max_retries: int = _DEFAULT_MAX_RETRIES):
        import redis
        self._r = redis.from_url(redis_url, decode_responses=True)
        self._max_retries = max_retries

    def push_task(
        self,
        task_id: str,
        input_text: str,
        chat_history: list | None = None,
    ) -> None:
        """将任务加入离线重试队列（幂等——同 task_id 不重复入队）。

        Args:
            task_id: 任务唯一 ID
            input_text: 用户输入
            chat_history: 对话历史
        """
        # 幂等检查
        pending = self._r.lrange(_OFFLINE_KEY, 0, -1)
        for raw in pending:
            try:
                existing = json.loads(raw)
                if existing.get("task_id") == task_id:
                    logger.info(f"[OfflineQueue] 任务已存在, 跳过: {task_id}")
                    return
            except json.JSONDecodeError:
                continue

        payload = {
            "task_id": task_id,
            "input": input_text,
            "chat_history": chat_history or [],
            "retry_count": 0,
            "max_retries": self._max_retries,
            "created_at": time.time(),
        }
        self._r.lpush(_OFFLINE_KEY, json.dumps(payload, ensure_ascii=False))
        logger.info(
            f"[OfflineQueue] 离线任务入队: {task_id}, "
            f"队列长度={self._r.llen(_OFFLINE_KEY)}"
        )

    def pop_pending(self) -> dict[str, Any] | None:
        """取出一个待处理的离线任务（从队尾取，保证 FIFO）。"""
        raw = self._r.rpop(_OFFLINE_KEY)
        if raw is None:
            return None
        return json.loads(raw)

    def mark_failed(self, task_id: str, reason: str = "") -> None:
        """将任务移入死信队列（超出最大重试次数时调用）。"""
        dead_payload = {
            "task_id": task_id,
            "reason": reason,
            "moved_at": time.time(),
        }
        self._r.lpush(_DEAD_KEY, json.dumps(dead_payload, ensure_ascii=False))
        logger.error(
            f"[OfflineQueue] 任务彻底失败, 已移入死信队列: "
            f"task_id={task_id}, reason={reason}, "
            f"死信数量={self._r.llen(_DEAD_KEY)}"
        )

    def pending_count(self) -> int:
        return self._r.llen(_OFFLINE_KEY)

    def dead_count(self) -> int:
        return self._r.llen(_DEAD_KEY)

    def repush_with_retry(self, task: dict) -> None:
        """重新入队（retry_count 由调用方自增后传入）。FIFO, 从队尾推入。"""
        self._r.rpush(_OFFLINE_KEY, json.dumps(task, ensure_ascii=False))
