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

    # Output Directory
    output_dir: str = os.environ.get("OUTPUT_DIR", "data/")

    # Model configuration for Settings loading
    model_config = SettingsConfigDict(
        env_file='.env',          # Load .env file
        env_file_encoding='utf-8',
        extra='ignore'           # Ignore extra fields from .env
    )

# Create a single settings instance
settings = Settings()

# Validate essential settings
if not settings.openai_api_key:
    logger.error("OPENAI_API_KEY environment variable not set or empty in .env file.")
    # Depending on your application's needs, you might want to raise an error
    # or exit here if the API key is absolutely essential for startup.
    # raise ValueError("OPENAI_API_KEY must be set") 