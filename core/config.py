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

country_code_map = {
    "FRANCE": "105015875",
    "BELGIUM": "100565514",
    "SPAIN": "105646813",
    "ENGLAND": "102299470",
    "GERMANY": "101282230",
    "ITALY": "103350119",
    "UNITED_STATES": "103644278",
    "UNITED STATES": "103644278",
    "CANADA": "101174742",
    "AUSTRALIA": "101452733",
    "INDIA": "102713980",
    "CHINA": "102890883",
    "JAPAN": "101355337",
    "BRAZIL": "106057199",
    "POLAND": "105072130",
    "NETHERLANDS": "102890719",
    "UKRAINE": "102264497",
    "SWITZERLAND": "106693272",
    "SWEDEN": "105117694",
    "ALBANIA": "102845717",
    "RUSSIA": "101728296",
    "UNITED_ARAB_EMIRATES": "104305776",
    "UNITED ARAB EMIRATES": "104305776",
    "ANDORRA": "106296266",
    "AUSTRIA": "103883259",
    "BELARUS": "101705918",
    "BULGARIA": "105333783",
    "CROATIA": "104688944",
    "CZECH_REPUBLIC": "104508036",
    "CZECH REPUBLIC": "104508036",
    "DENMARK": "104514075",
    "ESTONIA": "102974008",
    "FINLAND": "100456013",
    "GEORGIA": "106315325",
    "GREECE": "104677530",
    "HUNGARY": "100288700",
    "TURKEY": "106732692",
    "ROMANIA": "106670623",
    "PORTUGAL": "100364837",
    "NORWAY": "103819153",
    "MOLDOVA": "106178099",
    "LITHUANIA": "101464403",
    "LUXEMBOURG": "104042105",
    "SERBIA": "101855366",
    "SLOVAKIA": "103119917",
    "BOSNIA_AND_HERZEGOVINA": "102869081",
    "BOSNIA AND HERZEGOVINA": "102869081",
    "LATVIA": "104341318",
    "LIECHTENSTEIN": "100878084",
    "ISRAEL": "101620260",
    "KAZAKHSTAN": "106049128",
    "AZERBAIJAN": "103226548",
    "UZBEKISTAN": "107734735",
    "TAJIKISTAN": "105925962",
}
