from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Payment Processing Service"
    api_key: str = "change-me"
    database_url: str = "postgresql+asyncpg://payments:payments@postgres:5432/payments"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    payment_exchange: str = "payments"
    payment_queue: str = "payments.new"
    payment_routing_key: str = "payments.new"
    dlx_exchange: str = "payments.dlx"
    dlq_queue: str = "payments.dlq"
    outbox_poll_interval: float = 1.0
    outbox_batch_size: int = 100
    webhook_timeout_seconds: float = 5.0
    webhook_max_attempts: int = 3
    consumer_max_attempts: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
