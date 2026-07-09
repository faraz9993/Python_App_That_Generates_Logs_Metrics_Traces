from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = Field(default=8080, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    service_name: str = Field(default="my-observability-service", alias="SERVICE_NAME")

    otel_service_name: str = Field(default="my-observability-service", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_exporter_otlp_protocol: str = Field(default="grpc", alias="OTEL_EXPORTER_OTLP_PROTOCOL")
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")

    enable_traffic_generator: bool = Field(default=True, alias="ENABLE_TRAFFIC_GENERATOR")
    error_rate: float = Field(default=0.1, ge=0, le=1, alias="ERROR_RATE")
    latency_rate: float = Field(default=0.05, ge=0, le=1, alias="LATENCY_RATE")
    traffic_rate: float = Field(default=5, gt=0, alias="TRAFFIC_RATE")

    cpu_simulation_enabled: bool = Field(default=True, alias="CPU_SIMULATION_ENABLED")
    memory_simulation_enabled: bool = Field(default=True, alias="MEMORY_SIMULATION_ENABLED")

    downstream_service_url: str = Field(
        default="http://downstream-service:8080", alias="DOWNSTREAM_SERVICE_URL"
    )

    nested_spans_enabled: bool = Field(default=True, alias="NESTED_SPANS_ENABLED")
    multi_log_enabled: bool = Field(default=True, alias="MULTI_LOG_ENABLED")
    error_spans_enabled: bool = Field(default=True, alias="ERROR_SPANS_ENABLED")
    db_spans_enabled: bool = Field(default=False, alias="DB_SPANS_ENABLED")

    db_host: str = Field(default="postgres", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="orders", alias="DB_NAME")
    db_user: str = Field(default="app", alias="DB_USER")
    db_password: str = Field(default="app", alias="DB_PASSWORD")
    db_pool_min_size: int = Field(default=1, alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=5, alias="DB_POOL_MAX_SIZE")
    db_connect_timeout_seconds: float = Field(default=5.0, alias="DB_CONNECT_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()

