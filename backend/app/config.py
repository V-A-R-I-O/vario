from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRY_MINUTES: int = 60
    MOCK_AUTH_URL: str = "http://localhost:9001"
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:" # Default to in-memory for dev/tests
    
    class Config:
        env_file = ".env"

settings = Settings()
