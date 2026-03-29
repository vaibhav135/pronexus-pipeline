from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # LLM — Groq (owner extraction)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Discovery — Scraper Tech Google Maps
    map_scraper: str = ""

    # Search fallback — Tavily (1,000 free/month, resets)
    tavily_api_key: str = ""

    # Search fallback — Exa (1,000 free/month)
    exa_api_key: str = ""

    # Website scraping — Jina Reader
    jina_ai_api_key: str = ""

    # Future — residential proxy for Google search
    dataimpulse_proxy_url: str = ""

    # Email finding
    outscraper_api_key: str = ""
    prospeo_api_key: str = ""

    # Facebook supplement
    apify_token: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Pipeline config
    pipeline_batch_size: int = 50
    pipeline_sleep_seconds: float = 2.0
    max_subpages_to_crawl: int = 20
    log_level: str = "INFO"


settings = Settings()
