"""Redis 消息队列 — LPUSH 入队 + BRPOP 消费 + 结果缓存"""

import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class RedisQueue:
    """基于 Redis 的轻量任务队列。

    不引入 Celery/RabbitMQ 等重型依赖，MVP 够用。
    生产环境可替换为 Redis Stream 或 RabbitMQ。

    用法:
        queue = RedisQueue("redis://localhost:6379")
        task_id = queue.push({"input": "查物流", "chat_history": []})
        result = queue.wait(task_id, timeout=30)
    """

    def __init__(self, redis_url: str):
        import redis
        self._r = redis.from_url(redis_url, decode_responses=True)
        self._task_key = "shopaide:task_queue"
        self._result_prefix = "shopaide:result:"

    def push(self, payload: dict) -> str:
        """将任务推入队列，返回 task_id。

        payload 格式: {"input": str, "chat_history": [...], ...}
        """
        task_id = str(uuid.uuid4())[:8]
        payload["task_id"] = task_id
        self._r.lpush(self._task_key, json.dumps(payload, ensure_ascii=False))
        logger.info(f"[RedisQueue] 任务入队 task_id={task_id}")
        return task_id

    def pop_blocking(self, timeout: int = 5) -> dict[str, Any] | None:
        """阻塞式从队列取出任务（Worker 侧调用）。

        Args:
            timeout: BRPOP 等待秒数，超时返回 None

        Returns:
            {"task_id": str, "input": str, "chat_history": [...]} 或 None
        """
        result = self._r.brpop(self._task_key, timeout=timeout)
        if result is None:
            return None
        _, raw = result
        return json.loads(raw)

    def set_result(self, task_id: str, output: str, expire: int = 300) -> None:
        """写入任务结果，默认 5 分钟过期。

        Args:
            task_id: 任务 ID
            output: Agent 回复文本
            expire: 过期秒数
        """
        key = f"{self._result_prefix}{task_id}"
        self._r.setex(key, expire, output)
        logger.info(f"[RedisQueue] 任务完成 task_id={task_id}")

    def get_result(self, task_id: str) -> str | None:
        """轮询查询任务结果（前端侧调用）。"""
        key = f"{self._result_prefix}{task_id}"
        return self._r.get(key)

    def queue_length(self) -> int:
        """当前队列长度（监控用）。"""
        return self._r.llen(self._task_key)
