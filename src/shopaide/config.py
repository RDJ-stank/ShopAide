"""应用配置 — 统一从环境变量加载，本地开发使用 .env 文件"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """全局配置单例（够 MVP 用，不做复杂抽象）"""

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    model_name: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    temperature: float = float(os.getenv("TEMPERATURE", "0"))

    @property
    def llm_kwargs(self) -> dict:
        """组装给 ChatOpenAI 的参数"""
        kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
            "api_key": self.openai_api_key,
        }
        if self.openai_api_base:
            kwargs["base_url"] = self.openai_api_base
        return kwargs


settings = Settings()
