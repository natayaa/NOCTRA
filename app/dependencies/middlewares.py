import asyncio, time, re, requests

from fastapi.security import OAuth2PasswordBearer
from starlette import status
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from collections import deque, defaultdict
from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired
from typing_extensions import Optional


class HeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['Strict-Transport-Security'] = f"max-age=31543000; includeSubDomains; preload" # reconfigured in config .env
        response.headers['X-Content-Type-Options'] = "nosniff"
        response.headers['X-XSS-Protection'] = "1;mode=block"
        response.headers['X-Frame-Option'] = "ALLOW"
        response.headers['Referrer-Policy'] = "strict-origin-when-cross-origin"
        response.headers['geolocation=(self)']
        response.headers['Access-Control-Allow-Origin'] = "*"
        response.headers['Cache-Control'] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        
        csp = (
            "default-src 'self';"
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        return response
    
# OAUTH 2
class SecureOAuth(OAuth2PasswordBearer):
    def __init__(self, tokenUrl: str = "", auth_err: bool = True):
        super().__init__(tokenUrl=tokenUrl, auth_err=auth_err)
        
    async def __call__(self, request: Request) -> str:
        authHeader = request.headers.get("Authorization")
        if not authHeader:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Missing authorization headers",
                headers={
                    "WWW-Authenticate": "Bearer"
                }
            )
        match = re.fullmatch(r'Bearer\s+(.+s)$', authHeader.strip(), re.IGNORECASE)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format", 
                headers={
                    "WWW-Authenticate": "Bearer"
                }
            )
        token = match.group(1)
        if len(token) < 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token too short/corrupted",
                headers={
                    "WWW-Authenticate": "Bearer"
                }
            )
            
        return token
    
