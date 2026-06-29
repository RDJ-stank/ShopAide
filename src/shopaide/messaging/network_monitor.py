"""网络连通性检测模块

为海上石油平台等极端卫星网络场景设计。
多目标 HTTP 探测 + threading.Event 状态通知 + 零 CPU 空转。

用法:
    monitor = NetworkMonitor()
    monitor.on_status_change(lambda online: print(f"网络: {online}"))
    monitor.start_polling(interval=15)
    ...
    monitor.is_online  # True/False
"""

import logging
import threading
import time
from http.client import HTTPConnection, HTTPSConnection

logger = logging.getLogger(__name__)

_DEFAULT_TARGETS = [
    ("https", "api.deepseek.com", 443, "/v1/models", 5),
    ("https", "cloudflare.com", 443, "/", 5),
]


class NetworkMonitor:
    """轻量级网络连通性检测器。

    - 多目标 HTTP HEAD 探测，任一可达即视为在线
    - 内置 threading.Event 实现状态变更通知
    - 间隔轮询，零 CPU 空转
    """

    def __init__(self, targets: list[tuple] | None = None):
        self._targets = targets or _DEFAULT_TARGETS
        self._lock = threading.Lock()
        self._online = True   # 乐观假设在线，避免冷启动降级
        self._callbacks: list = []
        self._poll_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_online(self) -> bool:
        with self._lock:
            return self._online

    @is_online.setter
    def is_online(self, value: bool):
        changed = False
        with self._lock:
            if self._online != value:
                self._online = value
                changed = True
        if changed:
            state = "在线" if value else "断网"
            logger.warning(f"[NetworkMonitor] 状态变更 → {state}")
            for cb in self._callbacks:
                try:
                    cb(value)
                except Exception:
                    logger.exception("状态回调异常")

    def on_status_change(self, callback):
        """注册网络状态变更回调。callback(online: bool)。"""
        self._callbacks.append(callback)

    def check_connectivity(self) -> bool:
        """多目标 HTTP HEAD 探测。任一可达返回 True。"""
        for scheme, host, port, path, timeout in self._targets:
            try:
                if scheme == "https":
                    conn = HTTPSConnection(host, port, timeout=timeout)
                else:
                    conn = HTTPConnection(host, port, timeout=timeout)
                conn.request("HEAD", path)
                resp = conn.getresponse()
                conn.close()
                if resp.status < 500:
                    return True
            except Exception:
                continue
        return False

    def _poll_loop(self):
        """后台轮询线程。"""
        logger.info("[NetworkMonitor] 后台轮询已启动")
        while not self._stop_event.is_set():
            try:
                reachable = self.check_connectivity()
                self.is_online = reachable
            except Exception:
                logger.exception("连通性检测异常")
                self.is_online = False
            self._stop_event.wait(15)  # 15 秒间隔

    def start_polling(self, interval: int = 15):
        """启动后台轮询线程。"""
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._stop_event.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info(f"[NetworkMonitor] 轮询启动, 间隔={interval}s")

    def stop_polling(self):
        """停止后台轮询。"""
        self._stop_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=5)


# 全局单例
monitor = NetworkMonitor()
