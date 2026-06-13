"""应用配置 — 统一从环境变量加载，本地开发使用 .env 文件"""

import os

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# LLM 提供商预设（方便快速切换，无需每次手动填 base_url + model）
# ============================================================
LLM_PROVIDER_PRESETS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "openai": {
        "base_url": "",                         # 官方 API 不需要 base_url
        "model": "gpt-4o-mini",
    },
}


class Settings:
    """全局配置单例（够 MVP 用，不做复杂抽象）"""

    # LLM 提供商：deepseek / qwen / openai（三选一）
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")

    # 手动覆盖值（优先级高于 preset）
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    model_name: str = os.getenv("MODEL_NAME", "")
    temperature: float = float(os.getenv("TEMPERATURE", "0"))

    # API 访问令牌（不设则允许所有请求，设为空字符串则需在 .env 中配置）
    api_access_token: str = os.getenv("API_ACCESS_TOKEN", "")

    # Sentry DSN（错误监控，不设则跳过 Sentry 初始化）
    sentry_dsn: str = os.getenv("SENTRY_DSN", "")

    def _resolve(self) -> dict:
        """根据 LLM_PROVIDER 拼出最终参数，环境变量可手动覆盖"""
        preset = LLM_PROVIDER_PRESETS.get(
            self.llm_provider,
            LLM_PROVIDER_PRESETS["openai"],
        )

        base_url = self.openai_api_base or preset["base_url"] or None
        model = self.model_name or preset["model"]

        kwargs = {
            "model": model,
            "temperature": self.temperature,
            "api_key": self.openai_api_key,
        }
        if base_url:
            kwargs["base_url"] = base_url
        return kwargs

    @property
    def llm_kwargs(self) -> dict:
        return self._resolve()


settings = Settings()
