from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str
    first_model_name: str 
    second_model_name: str 
    port : int
    default_lang: str = "en"
    pinecone_api_key: str
    pinecone_env: str
    pinecone_index_name: str
    pinecone_metadata_namespace: str
    word_matching_threshold: float = 0.35
    ai_name: str = "SPARK"
    mongo_uri : str 
    db_name : str = "spark"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings() # type: ignore