import os
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App General Settings
    PROJECT_NAME: str = "CodeForge AI"
    API_V1_STR: str = "/api/v1"
    
    # Server Listen Address
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Workspace Settings
    WORKSPACE_DIR: Path = Path(os.getenv("WORKSPACE_DIR", "c:/Users/Aashbir/OneDrive/Desktop/project 2/workspace")).resolve()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure workspace directory exists
settings.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
