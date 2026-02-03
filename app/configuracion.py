from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SYNC_TOKEN: str  # ✅ token para proteger los endpoints /sync

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
