import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # OpenAI API Key
    openai_api_key: str = ""

    # Database Configuration
    db_name: str = "recruiting"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "127.0.0.1"
    db_port: str = "6543"

    # Output Directory
    output_dir: str = "data/"

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