"""
Configuration management for the DevOps PR Auto-Orchestrator
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional
import base64


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_env: str = "dev"
    port: int = 8000
    log_level: str = "INFO"
    
    # GitHub App Configuration
    github_app_id: Optional[int] = None
    github_private_key_base64: Optional[str] = None
    github_webhook_secret: Optional[str] = None
    
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "app"
    db_password: str = "app_pw"
    db_name: str = "pr_orchestrator"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    
    # Processing Configuration
    enable_treesitter: bool = False
    max_patch_bytes: int = 400000
    max_suggestions_per_function: int = 3
    
    # Risk Scoring
    additions_threshold: int = 1000
    high_risk_dependencies: list[str] = [
        "cryptography", "pyjwt", "requests", "urllib3"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def database_url(self) -> str:
        """Get database URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def github_private_key(self) -> Optional[str]:
        """Decode GitHub private key from base64"""
        if self.github_private_key_base64:
            return base64.b64decode(self.github_private_key_base64).decode('utf-8')
        return None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()