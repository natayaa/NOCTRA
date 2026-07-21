# app/modules/auth/services/authorization_service.py
"""
Authorization service for permission checking and role management.
"""

from typing import Optional, List, Dict, Any, Set
from uuid import UUID

from app.modules.auth.domain.permission_checker import PermissionChecker
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.models.user import User
from app.modules.auth.enums import UserRole, PermissionAction, PermissionCategory
from app.modules.auth.permissions import Permissions, PERMISSION_METADATA
from app.modules.auth.exceptions import PermissionDeniedError, UserNotFoundError

from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthorizationService:
    """
    Authorization service for permission checking and role management.
    
    Handles:
    - Permission checking for users and roles
    - Role management
    - Permission validation and metadata
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        permission_checker: Optional[PermissionChecker] = None,
    ):
        self.user_repo = user_repo
        self.permission_checker = permission_checker or PermissionChecker()
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== PERMISSION CHECKING ====================
    
    async def check_permission(
        self,
        user_id: UUID,
        permission: str,
        raise_exception: bool = True,
    ) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: User ID
            permission: Permission string
            raise_exception: Whether to raise exception if denied
            
        Returns:
            True if user has permission
            
        Raises:
            PermissionDeniedError: If user doesn't have permission and raise_exception is True
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        has_permission = self.permission_checker.has_permission(user.role, permission)
        
        if not has_permission and raise_exception:
            raise PermissionDeniedError(
                f"User with role {user.role.value} does not have permission: {permission}"
            )
        
        return has_permission
    
    async def check_permissions(
        self,
        user_id: UUID,
        permissions: List[str],
        require_all: bool = True,
        raise_exception: bool = True,
    ) -> bool:
        """
        Check if a user has multiple permissions.
        
        Args:
            user_id: User ID
            permissions: List of permission strings
            require_all: If True, require all permissions; if False, require any
            raise_exception: Whether to raise exception if denied
            
        Returns:
            True if user has required permissions
            
        Raises:
            PermissionDeniedError: If user doesn't have required permissions
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        
        if require_all:
            has_permission = self.permission_checker.has_all_permissions(
                user.role,
                permissions
            )
        else:
            has_permission = self.permission_checker.has_any_permission(
                user.role,
                permissions
            )
        
        if not has_permission and raise_exception:
            raise PermissionDeniedError(
                f"User with role {user.role.value} does not have required permissions: {permissions}"
            )
        
        return has_permission
    
    async def get_user_permissions(
        self,
        user_id: UUID,
    ) -> List[str]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of permission strings
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        return self.permission_checker.get_permissions(user.role)
    
    async def get_user_permission_set(
        self,
        user_id: UUID,
    ) -> Set[str]:
        """
        Get all permissions for a user as a set.
        
        Args:
            user_id: User ID
            
        Returns:
            Set of permission strings
            
        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.user_repo.get_or_raise(user_id)
        return self.permission_checker.get_permission_set(user.role)
    
    # ==================== PERMISSION METADATA ====================
    
    def get_permission_metadata(self, permission: str) -> Optional[Dict]:
        """
        Get metadata for a permission.
        
        Args:
            permission: Permission string
            
        Returns:
            Permission metadata or None
        """
        return self.permission_checker.get_permission_metadata(permission)
    
    def get_all_permissions(self) -> Dict[str, Dict]:
        """
        Get all permissions with metadata.
        
        Returns:
            Dictionary of all permissions
        """
        return PERMISSION_METADATA
    
    def get_permissions_by_category(
        self,
        category: PermissionCategory,
    ) -> List[str]:
        """
        Get all permissions in a category.
        
        Args:
            category: Permission category
            
        Returns:
            List of permission strings
        """
        from app.modules.auth.permissions import get_permissions_by_category
        return get_permissions_by_category(category)
    
    def get_permissions_by_action(
        self,
        action: PermissionAction,
    ) -> List[str]:
        """
        Get all permissions with a specific action.
        
        Args:
            action: Permission action
            
        Returns:
            List of permission strings
        """
        from app.modules.auth.permissions import get_permissions_by_action
        return get_permissions_by_action(action)
    
    # ==================== ROLE MANAGEMENT ====================
    
    async def change_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        changed_by: UUID,
    ) -> User:
        """
        Change a user's role.
        
        Args:
            user_id: User ID
            new_role: New role
            changed_by: User ID who changed the role
            
        Returns:
            Updated User instance
            
        Raises:
            UserNotFoundError: If user not found
            PermissionDeniedError: If changer doesn't have permission
        """
        # Check if changer has permission to change roles
        await self.check_permission(changed_by, Permissions.USER_ROLES)
        
        user = await self.user_repo.update_role(user_id, new_role)
        
        self.logger.info(f"User {user_id} role changed to {new_role.value} by {changed_by}")
        return user
    
    async def get_users_by_role(
        self,
        role: UserRole,
        limit: int = 50,
        offset: int = 0,
    ) -> List[User]:
        """
        Get all users with a specific role.
        
        Args:
            role: User role
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of users
        """
        return await self.user_repo.get_users_by_role(role, limit=limit, offset=offset)
    
    async def get_roles_with_permissions(self) -> Dict[str, List[str]]:
        """
        Get all roles with their permissions.
        
        Returns:
            Dictionary of roles and their permissions
        """
        from app.modules.auth.permissions import ROLE_PERMISSIONS
        
        return {
            role.value: permissions
            for role, permissions in ROLE_PERMISSIONS.items()
        }
    
    async def compare_role_permissions(
        self,
        role1: UserRole,
        role2: UserRole,
    ) -> Dict[str, Any]:
        """
        Compare permissions between two roles.
        
        Args:
            role1: First role
            role2: Second role
            
        Returns:
            Comparison results
        """
        return self.permission_checker.compare_permissions(role1, role2)
    
    # ==================== PERMISSION VALIDATION ====================
    
    def validate_permission(self, permission: str) -> bool:
        """
        Validate that a permission exists.
        
        Args:
            permission: Permission string
            
        Returns:
            True if permission exists
        """
        return self.permission_checker.validate_permission(permission)
    
    def validate_permissions(self, permissions: List[str]) -> List[str]:
        """
        Validate a list of permissions and return invalid ones.
        
        Args:
            permissions: List of permission strings
            
        Returns:
            List of invalid permissions
        """
        return self.permission_checker.validate_permissions(permissions)
    
    # ==================== ROLE HIERARCHY ====================
    
    def is_admin(self, role: UserRole) -> bool:
        """
        Check if role is admin.
        
        Args:
            role: User role
            
        Returns:
            True if role is admin
        """
        return self.permission_checker.is_admin(role)
    
    def is_management(self, role: UserRole) -> bool:
        """
        Check if role is management (admin or manager).
        
        Args:
            role: User role
            
        Returns:
            True if role is admin or manager
        """
        return self.permission_checker.is_management(role)
    
    def is_staff(self, role: UserRole) -> bool:
        """
        Check if role is staff-level.
        
        Args:
            role: User role
            
        Returns:
            True if role is staff or higher
        """
        return self.permission_checker.is_staff(role)
    
    def get_role_level(self, role: UserRole) -> int:
        """
        Get role level (higher number = higher permission).
        
        Args:
            role: User role
            
        Returns:
            Role level (0-5)
        """
        return self.permission_checker.get_role_level(role)
    
    def is_higher_or_equal(
        self,
        role1: UserRole,
        role2: UserRole,
    ) -> bool:
        """
        Check if role1 has higher or equal permission level than role2.
        
        Args:
            role1: First role
            role2: Second role
            
        Returns:
            True if role1 level >= role2 level
        """
        return self.permission_checker.is_higher_or_equal(role1, role2)


__all__ = ['AuthorizationService']