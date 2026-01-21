"""
Configuration settings for UCP Portal Backend.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    debug: bool = False
    workers: int = 4
    cors_origins: list[str] = ["*"]

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-06-01"

    # MLC LLM
    mlc_llm_endpoint: str = "http://mlc-llm-gateway.mlc-llm.svc.cluster.local"
    mlc_llm_timeout: int = 120

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_ssl: bool = True

    # Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_database: str = "webllm-platform"

    # Service Bus
    servicebus_namespace: str = ""
    servicebus_topic_requests: str = "agent-requests"
    servicebus_topic_responses: str = "agent-responses"
    servicebus_topic_broadcast: str = "agent-broadcast"

    # Routing
    default_tier: str = "auto"
    fallback_enabled: bool = True
    cost_optimization: bool = True

    # Rate limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_tokens_per_minute: int = 100000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
