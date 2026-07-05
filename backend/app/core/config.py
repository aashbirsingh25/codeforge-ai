import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Ensure environment variables from .env are loaded into system env
load_dotenv()


class Settings(BaseSettings):
    # App General Settings
    PROJECT_NAME: str = "CodeForge AI"
    API_V1_STR: str = "/api/v1"
    
    # Server Listen Address
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Workspace Settings
    WORKSPACE_DIR: Path = Path(os.getenv("WORKSPACE_DIR", "c:/Users/Aashbir/OneDrive/Desktop/project 2/workspace")).resolve()

    # Restored LLM Configurations
    LLM_PROVIDER: str = "gemini"
    GEMINI_MODEL: str = "gemini-2.5-pro"
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    def __getattribute__(self, name):
        """Allows config values to be loaded dynamically from the environment.

        This ensures test overrides via environment dict mocking are reflected immediately
        on the global settings instance.
        """
        dynamic_fields = {
            "LLM_PROVIDER",
            "GEMINI_MODEL",
            "OPENAI_MODEL",
            "GEMINI_API_KEY",
            "OPENAI_API_KEY"
        }
        if name in dynamic_fields:
            if name in os.environ:
                return os.environ[name]
            elif name in {"GEMINI_API_KEY", "OPENAI_API_KEY"}:
                return None
        return super().__getattribute__(name)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure workspace directory exists
settings.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
