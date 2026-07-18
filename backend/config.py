from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    genius_access_token: str
    anthropic_api_key: str
    supabase_url: str
    supabase_service_key: str
    youtube_api_key: str
    newsapi_key: str = ""

    # Comma-separated list of origins allowed to hit the API. In production, set to
    # your deployed frontend URL (and any staging/preview URLs). Defaults to the
    # local dev frontend so `.env`-less local runs still work.
    allowed_origins: str = "http://localhost:3000"

    model_config = ConfigDict(env_file=".env", extra="ignore")

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

settings = Settings()
