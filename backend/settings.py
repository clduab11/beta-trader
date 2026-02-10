import os
from pydantic import BaseModel, Field
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    """Application settings with environment variable loading."""
    
    # Environment
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Integration Keys
    openai_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openrouter_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    exa_api_key: str | None = Field(default_factory=lambda: os.getenv("EXA_API_KEY"))
    tavily_api_key: str | None = Field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    firecrawl_api_key: str | None = Field(default_factory=lambda: os.getenv("FIRECRAWL_API_KEY"))
    
    # Infrastructure
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))

class SettingsManager:
    """Manages application settings and provides accessors."""
    
    def __init__(self):
        self._settings = Settings()
    
    def get_settings(self) -> Settings:
        return self._settings
    
    def update_settings(self, new_settings: dict) -> Settings:
        """Update settings at runtime and persist to .env."""
        # Update in-memory
        for key, value in new_settings.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)

        # Persist to .env
        env_path = ".env"
        try:
            # Read existing
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    lines = f.readlines()
            
            # Create dict of existing keys
            env_map = {}
            for i, line in enumerate(lines):
                if "=" in line:
                    key = line.split("=", 1)[0].strip()
                    env_map[key] = i
            
            # Update or append
            for key, value in new_settings.items():
                env_key = key.upper()
                # Ensure value is string
                val_str = str(value) if value is not None else ""
                line_content = f"{env_key}={val_str}\n"
                
                if env_key in env_map:
                    lines[env_map[env_key]] = line_content
                else:
                    lines.append(line_content)
                    env_map[env_key] = len(lines) - 1
            
            with open(env_path, "w") as f:
                f.writelines(lines)
                
        except Exception as e:
            # In a real app we'd log this, but structlog isn't set up in this module
            print(f"Failed to save .env: {e}")

        return self._settings

@lru_cache
def get_settings() -> Settings:
    return Settings()

@lru_cache
def get_settings_manager() -> SettingsManager:
    return SettingsManager()
