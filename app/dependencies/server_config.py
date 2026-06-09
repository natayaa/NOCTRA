import os

from pydantic import BaseModel, Field
from typing_extensions import List, Dict, Union, Any
from dotenv import load_dotenv

# initialize loadenv
load_dotenv()

class ServerConfig(BaseModel):
    SERVER_STAGE: str = os.getenv("STAGE", "development").lower()
    HOSTNAME: str = os.getenv("HOSTNAME")
    PORT: int = os.getenv("PORT")
    API_NAME: str = os.getenv("API_NAME")
    API_DESCRIPTION: str = os.getenv("API_DESCRIPTION")
    API_VERSION: str = os.getenv("API_VERSION")
    API_TOKENURL: str = os.getenv("API_TOKENURL")
    API_ENABLE_DOCS: str | None = Field(default_factory=lambda: None if os.getenv("API_ENABLE_DOCS", "false").lower() == "false" else str(os.getenv("API_PREFIX_PATH")))
    
    # HTTP Server Configuration
    ACCESS_SECRETKEY: str = Field(default_factory=lambda: os.getenv("ACCESS_SECRETKEY"))
    REFRESH_SECRETKEY: str = Field(default_factory=lambda: os.getenv("REFRESH_SECRETKEY"))
    
    ACCESS_EXPIRED_MINUTES_TOKEN: int = os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", 10)
    REFRESH_EXPIRED_DAYS_TOKEN: int = os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", 7)
    
    CSRF_SECRETKEY: str = Field(default_factory=lambda: os.getenv("CSRF_SECRETKEY"))
    CSRF_SALTKEY: str = Field(default_factory=lambda: os.getenv("CSRF_SALTKEY"))
    SESSIONID_EXPIRES: int = os.getenv("SESSIONID_EXPIRES_MINUTES", 60)
    HTTP_ONLY: bool = Field(default_factory=lambda: str(os.getenv("HTTP_ONLY", "false")).lower() == "true")
    CONFIG_PATH: str = os.getenv("CONFIG_PATH")
    SAMESITE_VALUE: str = os.getenv("SAMESITE_VALUE")
    TOKEN_MAXAGE: int = Field(default_factory=lambda: os.getenv("TOKEN_MAXAGE"))
    
class DatabaseConfiguration(BaseModel):
    # bingung rek make mongo atau 
    # postgres
    pass