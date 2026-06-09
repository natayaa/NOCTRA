from pydantic import BaseModel
from typing_extensions import List, Dict, AnyStr, Optional, Any

class BaseResponse(BaseModel):
    status: int = 0
    message: str = ""
    data: Optional[Any] = None
    
class BaseRequest(BaseModel):
    results: List[Dict[str, AnyStr]]