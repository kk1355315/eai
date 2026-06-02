from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fruit Health Backend"
    database_url: str = "sqlite:///./fruit_health.db"
    data_dir: Path = Path("data")
    foodkeeper_json_path: Path = Path("../data/foodkeeper.json")
    llm_api_base: str = "https://xplt.sdu.edu.cn:4000"
    llm_api_key: str | None = None
    llm_model: str = "Ali-dashscope/DeepSeek-V3.2"
    llm_enable_thinking_default: bool = False
    llm_timeout_seconds: float = 45.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
