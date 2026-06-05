from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://eai.744477.xyz,"
    "https://eai.744477.xyz"
)


class Settings(BaseSettings):
    app_name: str = "Fruit Health Backend"
    database_url: str = "sqlite:///./fruit_health.db"
    data_dir: Path = Path("data")
    foodkeeper_json_path: Path = Path("../data/foodkeeper.json")
    cors_allowed_origins: str = DEFAULT_CORS_ALLOWED_ORIGINS
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "*"
    llm_api_base: str = "https://xplt.sdu.edu.cn:4000"
    llm_api_key: str | None = None
    llm_model: str = "Ali-dashscope/DeepSeek-V3.2"
    llm_enable_thinking_default: bool = False
    llm_timeout_seconds: float = 45.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.cors_allowed_origins)

    @property
    def cors_methods(self) -> list[str]:
        return _split_csv(self.cors_allow_methods)

    @property
    def cors_headers(self) -> list[str]:
        return _split_csv(self.cors_allow_headers)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


settings = Settings()
