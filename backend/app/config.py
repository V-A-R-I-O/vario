from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRY_MINUTES: int = 60
    MOCK_AUTH_URL: str = "http://localhost:9001"
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:" # Default to in-memory for dev/tests

    # Rasa role-pack instances (one per role pack) — see docs/decisions/ADR-002-rasa-chat-contract.md
    RASA_HR_URL: str = "http://localhost:5005"
    RASA_IT_URL: str = "http://localhost:5006"
    RASA_ADMISSIONS_URL: str = "http://localhost:5007"

    # Chat engine tuning
    # Top intent below this confidence → clarification prompt instead of a workflow (FR-2).
    CONFIDENCE_THRESHOLD: float = 0.4
    # How long a conversation session stays live before expiring (minutes).
    SESSION_TTL_MINUTES: int = 60

    class Config:
        env_file = ".env"

settings = Settings()
