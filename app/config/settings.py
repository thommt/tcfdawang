from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TCF Learning Service"

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
