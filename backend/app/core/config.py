# backend/app/core/config.py
from __future__ import annotations
import os
import json
from typing import List, Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Chat & Social Platform"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/chat_platform",
    )
    DB_SSL_MODE: str | None = os.getenv("DB_SSL_MODE", None)
    DB_CONNECT_TIMEOUT_SECONDS: float = float(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10"))
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"

    # Firebase
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        os.path.join(os.path.dirname(__file__), "firebase_key.json"),
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # CORS
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000")  # parsed by validator

    # Security
    AES_KEY: str = os.getenv("AES_KEY", "")
    ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")  # parsed by validator
    SECURE_SSL_REDIRECT: bool = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "Strict")
    COOKIE_HTTP_ONLY: bool = os.getenv("COOKIE_HTTP_ONLY", "true").lower() == "true"
    CSRF_ENABLED: bool = os.getenv("CSRF_ENABLED", "true").lower() == "true"
    CSRF_COOKIE_NAME: str = os.getenv("CSRF_COOKIE_NAME", "csrf_token")
    CSRF_HEADER_NAME: str = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")
    CSRF_COOKIE_MAX_AGE_SECONDS: int = int(os.getenv("CSRF_COOKIE_MAX_AGE_SECONDS", "3600"))

    # Database connection pool tuning
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "0"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    REQUIRE_DATABASE_ON_STARTUP: bool = os.getenv("REQUIRE_DATABASE_ON_STARTUP", "false").lower() == "true"
    READ_REPLICA_DATABASE_URL: str | None = os.getenv("READ_REPLICA_DATABASE_URL", "")
    DB_FAILOVER_URL: str | None = os.getenv("DB_FAILOVER_URL", "")
    DB_REGION: str | None = os.getenv("DB_REGION", "")

    # Caching and Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CONNECT_TIMEOUT_SECONDS: float = float(os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS", "1.5"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "30"))
    ENABLE_QUERY_PROFILING: bool = os.getenv("ENABLE_QUERY_PROFILING", "false").lower() == "true"
    QUERY_PROFILING_SLOW_THRESHOLD_MS: int = int(os.getenv("QUERY_PROFILING_SLOW_THRESHOLD_MS", "100"))

    TASK_QUEUE_BACKEND: str = os.getenv("TASK_QUEUE_BACKEND", "inprocess")
    TASK_QUEUE_REDIS_KEY: str = os.getenv("TASK_QUEUE_REDIS_KEY", "chattingapp:task_queue")
    RQ_QUEUE_NAME: str = os.getenv("RQ_QUEUE_NAME", "chattingapp")
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    EVENT_BUS_TOPIC_PREFIX: str = os.getenv("EVENT_BUS_TOPIC_PREFIX", "chattingapp")

    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "chattingapp-backend")
    ENABLE_TRACE_LOGGING: bool = os.getenv("ENABLE_TRACE_LOGGING", "true").lower() == "true"

    # Media / CDN / S3
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")
    AWS_S3_REGION: str = os.getenv("AWS_S3_REGION", "")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    CDN_URL: str = os.getenv("CDN_URL", "")

    # AI tagger endpoint (optional)
    AI_TAGGER_URL: str = os.getenv("AI_TAGGER_URL", "")

    # Enable AVIF conversions when ffmpeg/libaom is available
    ENABLE_AVIF: bool = os.getenv("ENABLE_AVIF", "false").lower() == "true"

    # Rate limiting and security
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    AUTH_RATE_LIMIT_REQUESTS: int = int(os.getenv("AUTH_RATE_LIMIT_REQUESTS", "20"))
    AUDIT_LOGGING_ENABLED: bool = os.getenv("AUDIT_LOGGING_ENABLED", "true").lower() == "true"
    XSS_SANITIZATION_ENABLED: bool = os.getenv("XSS_SANITIZATION_ENABLED", "true").lower() == "true"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def normalize_app_env(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"prod", "production"}:
                return "production"
            if normalized in {"stag", "staging"}:
                return "staging"
            if normalized in {"dev", "development"}:
                return "development"
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes"}:
                return True
        return value

    @field_validator("FIREBASE_CREDENTIALS_PATH", mode="after")
    @classmethod
    def resolve_firebase_credentials_path(cls, value):
        if not value or os.path.isabs(value):
            return value

        config_dir = os.path.dirname(__file__)
        backend_dir = os.path.abspath(os.path.join(config_dir, "..", ".."))
        candidates = [
            os.path.abspath(value),
            os.path.abspath(os.path.join(config_dir, value)),
            os.path.abspath(os.path.join(backend_dir, value)),
            os.path.abspath(os.path.join(config_dir, os.path.basename(value))),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return value

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def validate_environment(self) -> None:
        errors: list[str] = []

        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required.")
        elif not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            errors.append("DATABASE_URL must use postgresql+asyncpg:// for async Postgres connections.")

        if self.READ_REPLICA_DATABASE_URL and not self.READ_REPLICA_DATABASE_URL.startswith("postgresql+asyncpg://"):
            errors.append("READ_REPLICA_DATABASE_URL must use postgresql+asyncpg:// for async Postgres read replica connections.")
        if self.DB_FAILOVER_URL and not self.DB_FAILOVER_URL.startswith("postgresql+asyncpg://"):
            errors.append("DB_FAILOVER_URL must use postgresql+asyncpg:// for async Postgres failover connections.")

        if self.FIREBASE_CREDENTIALS_PATH and not os.path.isfile(self.FIREBASE_CREDENTIALS_PATH):
            errors.append(f"Firebase credential file not found: {self.FIREBASE_CREDENTIALS_PATH}")

        # Strict production security checks
        if self.is_production:
            if not self.FIREBASE_PROJECT_ID:
                errors.append("FIREBASE_PROJECT_ID is required in production.")
            if not self.FIREBASE_CREDENTIALS_PATH or not os.path.isfile(self.FIREBASE_CREDENTIALS_PATH):
                errors.append("FIREBASE_CREDENTIALS_PATH must point to a valid file in production.")
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
                errors.append("JWT_SECRET_KEY must be set to a strong random secret (min 32 chars) in production.")
            if not self.AES_KEY or len(self.AES_KEY) < 32:
                errors.append("AES_KEY must be set to a strong encryption key (min 32 chars) in production.")
            if self.DEBUG:
                errors.append("DEBUG must be False in production.")
            if "*" in self.CORS_ORIGINS or any("*" in origin for origin in self.CORS_ORIGINS):
                errors.append("CORS_ORIGINS must not contain wildcards (*) in production.")

        if errors:
            raise RuntimeError("Environment validation failed:\n  - " + "\n  - ".join(errors))

    class Config:
        env_file = os.getenv("ENV_FILE", ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
