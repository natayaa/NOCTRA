import os

from pydantic import BaseModel
from typing_extensions import List, Dict, Union, Any
from dotenv import load_dotenv

# initialize loadenv
load_dotenv()

class ServerConfig(BaseModel):
    HOSTNAME: str = os.getenv("HOSTNAME")
    PORT: int = os.getenv("PORT")
    