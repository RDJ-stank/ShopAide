"""飞书集成模块 — Tenant Token + 消息发送 + 事件回调处理"""

import json
import time
import logging
import requests
from threading import Lock

logger = logging.getLogger(__name__)

# ============================================================
# Tenant Access Token 管理（自动缓存 + 过期续期）
# ============================================================
_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
_SEND_MSG_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

_token_cache: dict = {"token": "", "expires_at": 0}
_token_lock = Lock()


def _get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 Tenant Access Token（带缓存，过期自动刷新）。

    Token 有效期 2 小时，提前 5 分钟刷新以防止边界失效。
    """
    with _token_lock:
        if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 300:
            return _token_cache["token"]

        resp = requests.post(
            _TOKEN_URL,
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书 Token 获取失败: {data}")

        _token_cache["token"] = data["tenant_access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expire", 7200)
        logger.info("飞书 Tenant Token 已刷新")
        return _token_cache["token"]


def send_text_message(app_id: str, app_secret: str, chat_id: str, text: str) -> dict:
    """向指定群聊发送纯文本消息。

    Args:
        app_id: 飞书应用 App ID
        app_secret: 飞书应用 App Secret
        chat_id: 消息来源的 chat_id（从事件回调中取得）
        text: 要发送的文本内容

    Returns:
        飞书 API 响应 JSON
    """
    token = _get_tenant_token(app_id, app_secret)
    content = json.dumps({"text": text}, ensure_ascii=False)
    resp = requests.post(
        _SEND_MSG_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"receive_id": chat_id, "msg_type": "text", "content": content},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        logger.error(f"飞书发消息失败: {result}")
    return result


def parse_message_event(body: dict) -> dict | None:
    """从飞书事件回调中提取消息文本和会话 ID。

    飞书事件体结构（简化）:
      body = {
        "header": {"event_type": "im.message.receive_v1", ...},
        "event": {
          "message": {
            "chat_id": "oc_xxx",
            "message_type": "text",
            "content": "{\"text\":\"你好\"}"
          }
        }
      }

    Returns:
        {"chat_id": str, "text": str} 或 None（非消息事件）
    """
    header = body.get("header", {})
    if header.get("event_type") != "im.message.receive_v1":
        return None

    event = body.get("event", {})
    msg = event.get("message", {})
    chat_id = msg.get("chat_id", "")
    content_str = msg.get("content", "{}")

    try:
        content = json.loads(content_str)
        text = content.get("text", "")
    except json.JSONDecodeError:
        text = content_str

    return {"chat_id": chat_id, "text": text} if chat_id and text else None
