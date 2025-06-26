import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # OpenAI API Key
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")

    # Database Configuration
    db_name: str = os.environ.get("DB_NAME", "recruiting")
    db_user: str = os.environ.get("DB_USER", "postgres")
    db_password: str = os.environ.get("DB_PASSWORD", "postgres")
    db_host: str = os.environ.get("DB_HOST", "127.0.0.1")
    db_port: str = os.environ.get("DB_PORT", "5466")

    output_dir: str = os.environ.get("OUTPUT_DIR", "data/")

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()
if not settings.openai_api_key:
    logger.error("OPENAI_API_KEY environment variable not set or empty in .env file.")

