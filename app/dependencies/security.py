import uuid

from fastapi import status, HTTPException, Request, Depends, Security
from fastapi.responses import Response
from fastapi.security.api_key import APIKeyHeader

from datetime import datetime, timedelta
from typing_extensions import Optional, Dict, Annotated, Any
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
from jose import jwt, JWTError


oauth2_schemes = ""

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

def _verify_token(token: str, secret_key: str, algorithm: str) -> Dict:
    try:
        payload = jwt.decode(token=token, secret_key=secret_key, algorithms=algorithm)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Expired : {e}",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )
        
# access token & refresh token
async def create_access_token(payload: Dict[str, str], subject: Optional[str] = None) -> str:
    return _generate_token(
        payload=payload,
        secret_key="",
        algorithm="",
        expires_delta="", #timedelta(minutes=int())
        subject=subject
    )

async def create_refresh_token(payload: Dict[str, str], subject: Optional[str] = None) -> str:
    # should be different from access token for the configuration
    return _generate_token(
        payload=payload,
        secret_key="",
        algorithm="",
        expires_delta="", #timedelta(days=int())
        subject=subject
    )

async def verify_access_token(token: str) -> Dict[str, Any]:
    return _verify_token(token=token, secret_key="", algorithm="")

async def verify_refresh_token(token: str) -> Dict[str, Any]:
    return _verify_token(token=token, secret_key="", algorithm="")

# securing access endpoints
async def securing_endpoints(token: Annotated[str, str] = Depends(oauth2_schemes)):
    credentials_exceptions = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials, reauthenticate required",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )
    
    try:
        payload = jwt.decode(
            token=token,
            key="", # fill with secret key
            algorithms="" # fill with algorithm
        )
        
        username: str = payload.get("sub")
        if not username:
            raise credentials_exceptions
    except JWTError:
        raise credentials_exceptions
    
    return username