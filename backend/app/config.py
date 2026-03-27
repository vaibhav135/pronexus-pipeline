from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Groq
    groq_api_key: str = ""

    # Scraper Tech - Google Maps
    map_scraper: str = ""

    # Apify (Facebook Pages)
    apify_token: str = ""

    # Outscraper
    outscraper_api_key: str = ""

    # Serper
    serper_api_key: str = ""

    # Prospeo
    prospeo_api_key: str = ""

    # Hunter.io
    hunter_api_key: str = ""

    # Pipeline config
    pipeline_batch_size: int = 50
    pipeline_sleep_seconds: float = 2.0
    max_subpages_to_crawl: int = 20
    groq_model: str = "openai/gpt-oss-20b"
    log_level: str = "INFO"


settings = Settings()
