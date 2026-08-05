# app/modules/auth/domain/permission_checker.py
"""
Permission checking domain logic.
Pure business logic - no framework dependencies.
"""

from typing import List, Optional, Set, Union, Dict

from app.modules.auth.enums import UserRole
from app.modules.auth.permissions import (
    ROLE_PERMISSIONS,
    PERMISSION_METADATA,
    get_role_permissions,
    has_permission as _has_permission,
    has_any_permission as _has_any_permission,
    has_all_permissions as _has_all_permissions
)


class PermissionChecker:
    """
    Domain service for permission checking.
    Handles role-based permission evaluations.
    """
    
    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS
        self.permission_metadata = PERMISSION_METADATA
    
    def has_permission(self, role: UserRole, permission: str) -> bool:
        """
        Check if a role has a specific permission.
        
        Args:
            role: User role
            permission: Permission string
            
        Returns:
            True if role has the permission
        """
        return _has_permission(role, permission)
    
    def has_any_permission(self, role: UserRole, permissions: List[str]) -> bool:
        """
        Check if a role has any of the given permissions.
        
        Args:
            role: User role
            permissions: List of permission strings
            
        Returns:
            True if role has any of the permissions
        """
        return _has_any_permission(role, permissions)
    
    def has_all_permissions(self, role: UserRole, permissions: List[str]) -> bool:
        """
        Check if a role has all of the given permissions.
        
        Args:
            role: User role
            permissions: List of permission strings
            
        Returns:
            True if role has all of the permissions
        """
        return _has_all_permissions(role, permissions)
    
    def get_permissions(self, role: UserRole) -> List[str]:
        """
        Get all permissions for a role.
        
        Args:
            role: User role
            
        Returns:
            List of permission strings
        """
        return get_role_permissions(role)
    
    def get_permission_set(self, role: UserRole) -> Set[str]:
        """
        Get all permissions for a role as a set.
        
        Args:
            role: User role
            
        Returns:
            Set of permission strings
        """
        return set(self.get_permissions(role))
    
    def get_permission_metadata(self, permission: str) -> Optional[dict]:
        """
        Get metadata for a permission.
        
        Args:
            permission: Permission string
            
        Returns:
            Permission metadata or None
        """
        return self.permission_metadata.get(permission)
    
    def get_permission_description(self, permission: str) -> Optional[str]:
        """
        Get description for a permission.
        
        Args:
            permission: Permission string
            
        Returns:
            Permission description or None
        """
        metadata = self.get_permission_metadata(permission)
        return metadata.get("description") if metadata else None
    
    def validate_permission(self, permission: str) -> bool:
        """
        Validate that a permission exists.
        
        Args:
            permission: Permission string
            
        Returns:
            True if permission exists
        """
        return permission in self.permission_metadata
    
    def validate_permissions(self, permissions: List[str]) -> List[str]:
        """
        Validate a list of permissions and return invalid ones.
        
        Args:
            permissions: List of permission strings
            
        Returns:
            List of invalid permissions
        """
        return [p for p in permissions if not self.validate_permission(p)]
    
    def compare_permissions(
        self,
        role1: UserRole,
        role2: UserRole
    ) -> Dict[str, Union[List[str], Set[str]]]:
        """
        Compare permissions between two roles.
        
        Args:
            role1: First role
            role2: Second role
            
        Returns:
            Dictionary with comparison results
        """
        perms1 = set(self.get_permissions(role1))
        perms2 = set(self.get_permissions(role2))
        
        return {
            "role1_only": perms1 - perms2,
            "role2_only": perms2 - perms1,
            "common": perms1 & perms2,
            "role1_count": len(perms1),
            "role2_count": len(perms2),
        }
    
    def is_admin(self, role: UserRole) -> bool:
        """
        Check if role is admin.
        
        Args:
            role: User role
            
        Returns:
            True if role is admin
        """
        return role == UserRole.ADMIN
    
    def is_management(self, role: UserRole) -> bool:
        """
        Check if role is management (admin or manager).
        
        Args:
            role: User role
            
        Returns:
            True if role is admin or manager
        """
        return role in [UserRole.ADMIN, UserRole.MANAGER]
    
    def is_staff(self, role: UserRole) -> bool:
        """
        Check if role is staff-level.
        
        Args:
            role: User role
            
        Returns:
            True if role is staff, mechanic, or higher
        """
        return role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.STAFF, UserRole.MECHANIC]
    
    def get_role_level(self, role: UserRole) -> int:
        """
        Get role level (higher number = higher permission).
        
        Args:
            role: User role
            
        Returns:
            Role level (0-5)
        """
        levels = {
            UserRole.GUEST: 0,
            UserRole.CUSTOMER: 1,
            UserRole.MECHANIC: 2,
            UserRole.STAFF: 3,
            UserRole.MANAGER: 4,
            UserRole.ADMIN: 5,
        }
        return levels.get(role, 0)
    
    def is_higher_or_equal(self, role1: UserRole, role2: UserRole) -> bool:
        """
        Check if role1 has higher or equal permission level than role2.
        
        Args:
            role1: First role to compare
            role2: Second role to compare
            
        Returns:
            True if role1 level >= role2 level
        """
        return self.get_role_level(role1) >= self.get_role_level(role2)


__all__ = ['PermissionChecker']