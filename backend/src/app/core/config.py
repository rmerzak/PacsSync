import os
import jinja2
from enum import Enum
from pydantic_settings import BaseSettings
from starlette.config import Config

current_file_dir = os.path.dirname(os.path.realpath(__file__))
env_path = os.path.join(current_file_dir, "..", "..", ".env")
template_path = os.path.join(current_file_dir, "..", "templates")
config = Config(env_path)
class AppSettings(BaseSettings):
    APP_NAME: str = config("APP_NAME", default="FastAPI app")
    APP_DESCRIPTION: str | None = config("APP_DESCRIPTION", default=None)
    APP_VERSION: str | None = config("APP_VERSION", default=None)
    LICENSE_NAME: str | None = config("LICENSE", default=None)
    CONTACT_NAME: str | None = config("CONTACT_NAME", default=None)
    CONTACT_EMAIL: str | None = config("CONTACT_EMAIL", default=None)



class DatabaseSettings(BaseSettings):
    pass


class TestSettings(BaseSettings):
    TEST_NAME: str = config("TEST_NAME", default="Tester User")
    TEST_EMAIL: str = config("TEST_EMAIL", default="test@tester.com")
    TEST_USERNAME: str = config("TEST_USERNAME", default="testeruser")
    TEST_PASSWORD: str = config("TEST_PASSWORD", default="Str1ng$t")

class PostgresSettings(DatabaseSettings):
    POSTGRES_USER: str = config("POSTGRES_USER", default="backend")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="backend")
    POSTGRES_SERVER: str = config("POSTGRES_SERVER", default="localhost")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432)
    POSTGRES_DB: str = config("POSTGRES_DB", default="database")
    POSTGRES_SYNC_PREFIX: str = config("POSTGRES_SYNC_PREFIX", default="postgresql://")
    POSTGRES_ASYNC_PREFIX: str = config("POSTGRES_ASYNC_PREFIX", default="postgresql+asyncpg://")
    POSTGRES_URI: str = f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    POSTGRES_URL: str | None = config("POSTGRES_URL", default=None)

class CloadinarySettings(BaseSettings):
    CLOUDINARY_CLOUD_NAME: str = config("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = config("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = config("CLOUDINARY_API_SECRET")
class CryptSettings(BaseSettings):
    SECRET_KEY: str = config("SECRET_KEY")
    ALGORITHM: str = config("ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = config("REFRESH_TOKEN_EXPIRE_DAYS", default=7)
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = config("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS", default=12)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = config("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", default=30)

class EnvironmentOption(Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class EmailTemplates:
    EMAIL_TEMPLATES_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_path))
    EMAIL_TEMPLATES = {
        "verify_email": "verify_email_template.html",
        "reset_password": "reset_password_template.html",
    }


class ExternalSettings(BaseSettings):
    FRONT_URL: str = config("FRONT_URL", default="http://localhost:3000")
    EMAIL_SENDER: str = config("EMAIL_SENDER", default="smtp.gmail.com")
    SMTP_HOST: str = config("SMTP_HOST", default="6379")
    SMTP_USERNAME: str = config("SMTP_USERNAME", default="Abdou")
    SMTP_PASSWORD: str = config("SMTP_PASSWORD", default="your app password")

    @property
    def Categories(self):
        return ModelCategoriesEnum

class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: EnvironmentOption = config("ENVIRONMENT", default="local")



class Settings(
    AppSettings,
    TestSettings,
    PostgresSettings,
    EnvironmentSettings,
    CryptSettings,
    ExternalSettings,
    EmailTemplates,
    CloadinarySettings,
):
    pass


settings = Settings()