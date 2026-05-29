import os

from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing_extensions import List, Dict, Union

# init loadenv
load_dotenv()

class ServerConfig(BaseModel):
    IPHOSTNAME: str = os.getenv("IP_HOSTNAME")
    HOSTNAME_PORT: int = os.getenv("HOSTNAME_PORT")
    
    _PREFIX: str = os.getenv("SERVER_PREFIX")
    ENABLE_DOCS: Union[bool] = 