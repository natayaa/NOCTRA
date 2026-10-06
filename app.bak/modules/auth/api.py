from fastapi import APIRouter, Request, status

from core.deps import DbSession
from modules.auth.dependencies import CurrentUser
from modules.auth.schemas import LoginRequest, MeResponse, TokenPair
from modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenPair:
    ip = request.client.host if request.client else None
    _, tokens = await AuthService(db).login(
        payload,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(refresh_token: str, db: DbSession) -> TokenPair:
    return await AuthService(db).refresh(refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    data = MeResponse.model_validate(user)
    data.roles = [r.name for r in user.roles]
    return data