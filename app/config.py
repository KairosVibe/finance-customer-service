"""配置：读取本工程 .env，并在导入 dialoguekit 之前同步到环境变量。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_DIR / ".env"

load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    llm_model: str
    llm_base_url: str
    llm_api_key: str
    finance_base_url: str
    finance_channel_code: str = "MOBILE_BANK"
    finance_operator_no: str = "EMP000001"
    embedding_model_path: str = "D:/codebuddy/General-PurposeRAG/models/bge-m3"
    database_url: str
    app_host: str = "0.0.0.0"
    app_port: int = 8100
    # dialoguekit 兼容字段
    commerce_api_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")


settings = Settings()  # type: ignore[call-arg]


def bootstrap_env() -> None:
    """把本工程配置写入环境变量，供 dialoguekit 内部 Settings 读取（必须在导入 dialoguekit 之前调用）。"""
    os.environ.setdefault("LLM_MODEL", settings.llm_model)
    os.environ.setdefault("LLM_BASE_URL", settings.llm_base_url)
    os.environ.setdefault("LLM_API_KEY", settings.llm_api_key)
    os.environ.setdefault("COMMERCE_API_BASE_URL", settings.commerce_api_base_url)
    os.environ.setdefault("DATABASE_URL", settings.database_url)
    os.environ.setdefault("APP_HOST", settings.app_host)
    os.environ.setdefault("APP_PORT", str(settings.app_port))


