from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRY_MINUTES: int = 60
    MOCK_AUTH_URL: str = "http://localhost:9001"
    MOCK_HRMS_URL: str = "http://localhost:9002"
    MOCK_ITSM_URL: str = "http://localhost:9003"
    MOCK_ADMISSIONS_URL: str = "http://localhost:9004"
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:" # Default to in-memory for dev/tests

    # Rasa role-pack instances (one per role pack) — see docs/decisions/ADR-002-rasa-chat-contract.md
    RASA_HR_URL: str = "http://localhost:5005"
    RASA_IT_URL: str = "http://localhost:5006"
    RASA_ADMISSIONS_URL: str = "http://localhost:5007"
    RETRAINING_INTERNAL_TOKEN: str = ""
    ROLE_PACKS_DIR: str = "/rolepacks"

    # Chat engine tuning
    # Top intent below this confidence → clarification prompt instead of a workflow (FR-2).
    CONFIDENCE_THRESHOLD: float = 0.4
    # How long a conversation session stays live before expiring (minutes).
    SESSION_TTL_MINUTES: int = 60

    # Text-to-Speech (talk mode, slice-06). Path to the Google Cloud service-account
    # JSON with Text-to-Speech access. Empty → talk mode degrades to text-only.
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
