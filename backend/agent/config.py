"""
Agent configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional


class AgentConfig(BaseSettings):
    """Agent configuration"""

    # LLM config
    qwen_api_key: Optional[str] = None
    qwen_model: str = "qwen-max"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    # Query config
    default_query_size: int = 100
    max_query_size: int = 1000

    # Report config
    report_max_table_rows: int = 20
    report_chart_max_items: int = 10

    # Stream config
    stream_chunk_delay: float = 0.01  # Stream output delay (seconds)

    # Cache config
    enable_cache: bool = True
    cache_ttl: int = 300  # Cache time (seconds)

    class Config:
        env_prefix = "AGENT_"
        case_sensitive = False


# Global config instance
agent_config = AgentConfig()
