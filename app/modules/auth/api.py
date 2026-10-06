from fastapi import APIRouter, Request, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import DbSession
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schemas import LoginRequest, MeResponse, TokenPair
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


# New form endpoint used ONLY by Swagger's Authorize button
@router.post("/token", response_model=TokenPair, include_in_schema=True)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: DbSession = None,
) -> TokenPair:
    payload = LoginRequest(
        username=form_data.username,
        password=form_data.password,
    )
    ip = request.client.host if request.client else None
    _, tokens = await AuthService(db).login(
        payload,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    return tokens

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