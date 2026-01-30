"""
NoteTrial Backend - 配置模块
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# 项目根目录 (notetrial/)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置 - 自动从 .env 读取"""
    
    # OpenAI API 配置
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    
    # 小红书 MCP 配置
    xiaohongshu_mcp_url: str = "http://localhost:18060/mcp"
    
    # 服务配置
    backend_port: int = 8000
    frontend_port: int = 3000
    debug: bool = True
    
    # 模拟配置
    default_max_users: int = 20
    batch_size: int = 5
    
    # Pydantic v2 配置方式
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
