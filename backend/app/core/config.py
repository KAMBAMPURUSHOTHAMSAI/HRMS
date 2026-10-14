
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "HRMS API"
    app_env: str = "development"
    frontend_base_url: str = "http://localhost:5174"

    # Browser origins allowed to call the backend.
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:5174"
    )

    postgres_user: str = "hrms_user"
    postgres_password: SecretStr
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_db: str = "hrms_db"

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    demo_admin_email: str = "admin@example.com"
    demo_admin_password: SecretStr | None = None

    demo_hr_email: str = "hr@example.com"
    demo_hr_password: SecretStr | None = None

    demo_employee_email: str = "employee@example.com"
    demo_employee_password: SecretStr | None = None

    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


settings = Settings()
