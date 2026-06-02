import uuid

from fastapi import status, HTTPException, Request, Depends, Security
from fastapi.responses import Response
from fastapi.security.api_key import APIKeyHeader

from datetime import datetime, timedelta
from typing_extensions import Optional, Dict, Annotated, Any
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
from jose import jwt, JWTError


async def get_authenticated(login_container: Dict[str, str] = {}) -> Dict:
    if not login_container:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Login")
    
    
def _generate_token(payload: Dict[str, str], secret_key: str, algorithm: str, expires_delta: timedelta, subject: Optional[str] = None) -> str:
    now = datetime.now()
    try:
        expired_timestamp = int((now + expires_delta).replace(tzinfo="Asia/Jakarta").timestamp())
    except OSError:
        expired_timestamp = int((now + timedelta(days=7)).timestamp())
        
    encode_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": expired_timestamp,
        "jti": str(uuid.uuid4())
    }
    
    if subject:
        encode_payload.update({"sub": subject})
        
    return jwt.encode(encode_payload, secret_key, algorithm)


# access token & refresh token
async def create_access_token(payload: Dict[str, str], subject: Optional[str] = None) -> str:
    pass

async def create_refresh_token(payload: Dict[str, str], subject: Optional[str] = None) -> str:
    pass



