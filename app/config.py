from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str
    first_model_name: str 
    second_model_name: str 
    port : int
    default_lang: str = "en"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings() # type: ignore