# modules/auth/router.py
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.models import User
from core.database import get_db
from core.base import BaseResponse, PaginatedResponse
from core.dependencies import success_response, get_service
from core.exceptions import NotFoundError, ValidationError, UnauthorizedError, ForbiddenError
from .schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    UserRegister,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionCreate,
    PermissionResponse,
    UserRoleCreate,
    UserRoleResponse,
)
from .services import AuthService
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_permission,
    require_superuser,
)


auth_router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# ============================================================================
# Authentication Endpoints
# ============================================================================

@auth_router.post("/login", response_model=BaseResponse)
async def login(
    request: Request,
    data: UserLogin,
    service: AuthService = Depends(get_service(AuthService))
):
    """Login user."""
    try:
        result = await service.login(
            data,
            ip_address=request.client.host if request.client else None
        )
        await service.db.commit()
        return success_response(result, message="Login successful")
    except UnauthorizedError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@auth_router.post("/register", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    request: Request,
    service: AuthService = Depends(get_service(AuthService))
):
    """Register new user."""
    try:
        user = await service.register(
            data,
            ip_address=request.client.host if request.client else None
        )
        await service.db.commit()
        return success_response(
            {"id": str(user.id), "username": user.username},
            message="User registered successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.post("/refresh", response_model=BaseResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_service(AuthService))
):
    """Refresh access token."""
    try:
        result = await service.refresh_token(
            data.refresh_token,
            ip_address=request.client.host if request.client else None
        )
        await service.db.commit()
        return success_response(result, message="Token refreshed successfully")
    except UnauthorizedError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@auth_router.post("/logout", response_model=BaseResponse)
async def logout(
    data: RefreshTokenRequest,
    service: AuthService = Depends(get_service(AuthService))
):
    """Logout user."""
    try:
        result = await service.logout(data.refresh_token)
        await service.db.commit()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
        return success_response(None, message="Logout successful")
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.post("/logout-all", response_model=BaseResponse)
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_service(AuthService))
):
    """Logout from all devices."""
    try:
        count = await service.logout_all(current_user.id)
        await service.db.commit()
        return success_response(
            {"devices": count},
            message=f"Logged out from {count} devices"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.get("/me", response_model=BaseResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_service(AuthService))
):
    """Get current user profile."""
    permissions = await service.user_repo.get_user_permissions(current_user.id)
    roles = await service.user_repo.get_user_roles(current_user.id)

    return success_response({
        "user": UserResponse.model_validate(current_user).model_dump(),
        "roles": roles,
        "permissions": permissions
    }, message="User profile retrieved")


# ============================================================================
# Password Management
# ============================================================================

@auth_router.post("/change-password", response_model=BaseResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    service: AuthService = Depends(get_service(AuthService))
):
    """Change user password."""
    try:
        await service.change_password(current_user.id, data)
        await service.db.commit()
        return success_response(None, message="Password changed successfully")
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.post("/forgot-password", response_model=BaseResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    service: AuthService = Depends(get_service(AuthService))
):
    """Request password reset."""
    try:
        reset_token = await service.reset_password(data.email)
        await service.db.commit()
        # TODO: Send email with reset link
        return success_response(
            {"email": data.email, "reset_token": reset_token},
            message="Password reset link sent to email"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# User Management (Admin)
# ============================================================================

@auth_router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """List all users (admin only)."""
    users = await service.user_repo.get_all(limit=limit, offset=offset)
    total = await service.user_repo.count()

    return PaginatedResponse.from_paginated(
        items=[UserResponse.model_validate(u).model_dump() for u in users],
        total=total,
        page=(offset // limit) + 1,
        page_size=limit,
        message="Users retrieved successfully"
    )


@auth_router.get("/users/{user_id}", response_model=BaseResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Get user by ID (admin only)."""
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    permissions = await service.user_repo.get_user_permissions(user_id)

    return success_response({
        "user": UserResponse.model_validate(user).model_dump(),
        "permissions": permissions
    }, message="User retrieved successfully")


@auth_router.post("/users", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Create new user (admin only)."""
    try:
        # Check if username exists
        existing = await service.user_repo.get_by_username(data.username)
        if existing:
            raise ValidationError(f"Username '{data.username}' already exists")

        # Check if email exists
        existing = await service.user_repo.get_by_email(data.email)
        if existing:
            raise ValidationError(f"Email '{data.email}' already exists")

        # Create user
        user_data = data.model_dump(exclude={"password", "role_ids"})
        user = User(
            **user_data,
            password_hash=PasswordService.hash_password(data.password),
            status=UserStatus.ACTIVE
        )
        user = await service.user_repo.create(user)

        # Assign roles
        if data.role_ids:
            for role_id in data.role_ids:
                await service.user_repo.assign_role(user.id, role_id, current_user.id)

        await service.db.flush()
        await service.db.refresh(user)

        return success_response(
            {"id": str(user.id), "username": user.username},
            message="User created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.patch("/users/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Update user (admin only)."""
    try:
        user = await service.update_user(user_id, data.model_dump(exclude_unset=True))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        await service.db.commit()
        return success_response(
            {"id": str(user.id)},
            message="User updated successfully"
        )
    except (NotFoundError, ValidationError) as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.delete("/users/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Delete user (admin only)."""
    try:
        if user_id == current_user.id:
            raise ValidationError("Cannot delete yourself")

        deleted = await service.user_repo.delete(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        await service.db.commit()
        return success_response(
            {"id": str(user_id)},
            message="User deleted successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Role Management (Admin)
# ============================================================================

@auth_router.get("/roles", response_model=BaseResponse)
async def list_roles(
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """List all roles."""
    roles = await service.role_repo.get_all()
    return success_response(
        [RoleResponse.model_validate(r).model_dump() for r in roles],
        message="Roles retrieved successfully"
    )


@auth_router.post("/roles", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Create new role."""
    try:
        existing = await service.role_repo.get_by_name(data.name)
        if existing:
            raise ValidationError(f"Role '{data.name}' already exists")

        role = await service.create_role(data.model_dump(exclude_unset=True))
        await service.db.commit()
        return success_response(
            {"id": str(role.id), "name": role.name},
            message="Role created successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.patch("/roles/{role_id}", response_model=BaseResponse)
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Update role."""
    try:
        role = await service.update_role(role_id, data.model_dump(exclude_unset=True))
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        await service.db.commit()
        return success_response(
            {"id": str(role.id)},
            message="Role updated successfully"
        )
    except NotFoundError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@auth_router.delete("/roles/{role_id}", response_model=BaseResponse)
async def delete_role(
    role_id: UUID,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Delete role."""
    try:
        role = await service.role_repo.get(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if role.is_system:
            raise ValidationError("Cannot delete system role")

        deleted = await service.role_repo.delete(role_id)
        await service.db.commit()
        return success_response(
            {"id": str(role_id)},
            message="Role deleted successfully"
        )
    except ValidationError as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# User Role Management (Admin)
# ============================================================================

@auth_router.post("/users/{user_id}/roles", response_model=BaseResponse)
async def assign_role(
    user_id: UUID,
    data: UserRoleCreate,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Assign role to user."""
    try:
        # Check user exists
        user = await service.user_repo.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check role exists
        role = await service.role_repo.get(data.role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        user_role = await service.user_repo.assign_role(user_id, data.role_id, current_user.id)
        await service.db.commit()

        return success_response(
            {"id": str(user_role.id)},
            message=f"Role '{role.name}' assigned to user"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.delete("/users/{user_id}/roles/{role_id}", response_model=BaseResponse)
async def remove_role(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(require_superuser),
    service: AuthService = Depends(get_service(AuthService))
):
    """Remove role from user."""
    try:
        role = await service.role_repo.get(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        deleted = await service.user_repo.remove_role(user_id, role_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User does not have this role")

        await service.db.commit()
        return success_response(
            {"user_id": str(user_id), "role_id": str(role_id)},
            message=f"Role '{role.name}' removed from user"
        )
    except Exception as e:
        await service.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
