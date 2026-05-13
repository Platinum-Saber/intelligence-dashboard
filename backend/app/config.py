from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    debug: bool = True
    database_url: str = "sqlite:///./procurement_intel.db"
    seed_days: int = 365

    # Phase 2: live data feed keys
    fx_api_key: str = ""           # exchangerate-api.com
    newsapi_key: str = ""          # newsapi.org

    # Phase 2: NLP
    sentiment_enabled: bool = True  # set False to skip FinBERT loading

    # SMTP alert notifications
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_from_email: str = ""

    # CORS
    frontend_url: str = "http://localhost:5173"


settings = Settings()
