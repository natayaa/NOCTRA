# app/modules/auth/repositories/token_repository.py
"""
Token repository for access and refresh token management.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_repository import BaseRepository
from app.modules.auth.models.access_token import AccessToken
from app.modules.auth.models.refresh_token import RefreshToken
from app.modules.auth.enums import TokenStatus, TokenType
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class TokenRepository:
    """
    Repository for token operations (access and refresh tokens).
    
    Handles token creation, validation, revocation, and cleanup.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== ACCESS TOKEN OPERATIONS ====================
    
    async def create_access_token(
        self,
        token: str,
        jti: str,
        session_id: UUID,
        user_id: UUID,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[str] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> AccessToken:
        """
        Create an access token.
        
        Args:
            token: JWT token string
            jti: JWT ID
            session_id: Session ID
            user_id: User ID
            expires_at: Expiration timestamp
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created AccessToken instance
        """
        data = {
            "token": token,
            "jti": jti,
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": expires_at,
            "status": TokenStatus.ACTIVE,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        instance = AccessToken(**data)
        self.db.add(instance)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(instance)
        else:
            await self.db.flush()
        
        return instance
    
    async def get_access_token(
        self,
        token: str,
        include_revoked: bool = False
    ) -> Optional[AccessToken]:
        """
        Get an access token by token string.
        
        Args:
            token: JWT token string
            include_revoked: Whether to include revoked tokens
            
        Returns:
            AccessToken instance or None
        """
        query = select(AccessToken).where(
            AccessToken.token == token,
            AccessToken.is_active == True
        )
        
        if not include_revoked:
            query = query.where(AccessToken.status == TokenStatus.ACTIVE)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_access_token_by_jti(
        self,
        jti: str,
        include_revoked: bool = False
    ) -> Optional[AccessToken]:
        """
        Get an access token by JTI.
        
        Args:
            jti: JWT ID
            include_revoked: Whether to include revoked tokens
            
        Returns:
            AccessToken instance or None
        """
        query = select(AccessToken).where(
            AccessToken.jti == jti,
            AccessToken.is_active == True
        )
        
        if not include_revoked:
            query = query.where(AccessToken.status == TokenStatus.ACTIVE)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_access_tokens(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[AccessToken]:
        """
        Get active access tokens for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            
        Returns:
            List of active AccessToken instances
        """
        now = datetime.utcnow()
        
        query = select(AccessToken).where(
            AccessToken.user_id == user_id,
            AccessToken.status == TokenStatus.ACTIVE,
            AccessToken.expires_at > now,
            AccessToken.revoked_at.is_(None),
            AccessToken.is_active == True
        ).order_by(AccessToken.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def revoke_access_token(
        self,
        token: str,
        revoked_by: Optional[UUID] = None,
        commit: bool = True
    ) -> bool:
        """
        Revoke an access token.
        
        Args:
            token: JWT token string
            revoked_by: User ID who revoked the token
            commit: Whether to commit immediately
            
        Returns:
            True if revoked successfully
        """
        instance = await self.get_access_token(token, include_revoked=True)
        if not instance:
            return False
        
        instance.revoke(revoked_by)
        
        if commit:
            await self.db.commit()
        
        return True
    
    async def revoke_access_tokens_by_session(
        self,
        session_id: UUID,
        revoked_by: Optional[UUID] = None,
        commit: bool = True
    ) -> int:
        """
        Revoke all access tokens for a session.
        
        Args:
            session_id: Session ID
            revoked_by: User ID who revoked the tokens
            commit: Whether to commit immediately
            
        Returns:
            Number of tokens revoked
        """
        now = datetime.utcnow()
        
        query = update(AccessToken).where(
            AccessToken.session_id == session_id,
            AccessToken.status == TokenStatus.ACTIVE,
            AccessToken.revoked_at.is_(None),
            AccessToken.is_active == True
        ).values(
            status=TokenStatus.REVOKED,
            revoked_at=now,
            revoked_by=revoked_by
        )
        
        result = await self.db.execute(query)
        
        if commit:
            await self.db.commit()
        
        return result.rowcount
    
    # ==================== REFRESH TOKEN OPERATIONS ====================
    
    async def create_refresh_token(
        self,
        token: str,
        jti: str,
        session_id: UUID,
        user_id: UUID,
        expires_at: datetime,
        access_token_jti: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[str] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> RefreshToken:
        """
        Create a refresh token.
        
        Args:
            token: Refresh token string
            jti: JWT ID
            session_id: Session ID
            user_id: User ID
            expires_at: Expiration timestamp
            access_token_jti: JTI of the associated access token
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created RefreshToken instance
        """
        data = {
            "token": token,
            "jti": jti,
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": expires_at,
            "access_token_jti": access_token_jti,
            "status": TokenStatus.ACTIVE,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        instance = RefreshToken(**data)
        self.db.add(instance)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(instance)
        else:
            await self.db.flush()
        
        return instance
    
    async def get_refresh_token(
        self,
        token: str,
        include_revoked: bool = False
    ) -> Optional[RefreshToken]:
        """
        Get a refresh token by token string.
        
        Args:
            token: Refresh token string
            include_revoked: Whether to include revoked tokens
            
        Returns:
            RefreshToken instance or None
        """
        query = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.is_active == True
        )
        
        if not include_revoked:
            query = query.where(RefreshToken.status == TokenStatus.ACTIVE)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_refresh_token_by_jti(
        self,
        jti: str,
        include_revoked: bool = False
    ) -> Optional[RefreshToken]:
        """
        Get a refresh token by JTI.
        
        Args:
            jti: JWT ID
            include_revoked: Whether to include revoked tokens
            
        Returns:
            RefreshToken instance or None
        """
        query = select(RefreshToken).where(
            RefreshToken.jti == jti,
            RefreshToken.is_active == True
        )
        
        if not include_revoked:
            query = query.where(RefreshToken.status == TokenStatus.ACTIVE)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_refresh_tokens(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[RefreshToken]:
        """
        Get active refresh tokens for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            
        Returns:
            List of active RefreshToken instances
        """
        now = datetime.utcnow()
        
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.status == TokenStatus.ACTIVE,
            RefreshToken.expires_at > now,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.is_active == True
        ).order_by(RefreshToken.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def revoke_refresh_token(
        self,
        token: str,
        revoked_by: Optional[UUID] = None,
        commit: bool = True
    ) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            token: Refresh token string
            revoked_by: User ID who revoked the token
            commit: Whether to commit immediately
            
        Returns:
            True if revoked successfully
        """
        instance = await self.get_refresh_token(token, include_revoked=True)
        if not instance:
            return False
        
        instance.revoke(revoked_by)
        
        if commit:
            await self.db.commit()
        
        return True
    
    async def revoke_refresh_tokens_by_session(
        self,
        session_id: UUID,
        revoked_by: Optional[UUID] = None,
        commit: bool = True
    ) -> int:
        """
        Revoke all refresh tokens for a session.
        
        Args:
            session_id: Session ID
            revoked_by: User ID who revoked the tokens
            commit: Whether to commit immediately
            
        Returns:
            Number of tokens revoked
        """
        now = datetime.utcnow()
        
        query = update(RefreshToken).where(
            RefreshToken.session_id == session_id,
            RefreshToken.status == TokenStatus.ACTIVE,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.is_active == True
        ).values(
            status=TokenStatus.REVOKED,
            revoked_at=now,
            revoked_by=revoked_by
        )
        
        result = await self.db.execute(query)
        
        if commit:
            await self.db.commit()
        
        return result.rowcount
    
    async def rotate_refresh_token(
        self,
        old_token: str,
        new_token: str,
        new_jti: str,
        new_expires_at: datetime,
        new_access_token_jti: str,
        revoked_by: Optional[UUID] = None,
        commit: bool = True
    ) -> Tuple[RefreshToken, RefreshToken]:
        """
        Rotate a refresh token (revoke old, create new).
        
        Args:
            old_token: Old refresh token string
            new_token: New refresh token string
            new_jti: New JWT ID
            new_expires_at: New expiration timestamp
            new_access_token_jti: New access token JTI
            revoked_by: User ID who revoked the old token
            commit: Whether to commit immediately
            
        Returns:
            Tuple of (old_refresh_token, new_refresh_token)
            
        Raises:
            NotFoundError: If old token not found
        """
        # Get old token
        old_instance = await self.get_refresh_token(old_token, include_revoked=True)
        if not old_instance:
            raise NotFoundError("Refresh token not found")
        
        # Revoke old token
        old_instance.revoke(revoked_by)
        
        # Create new token
        new_instance = await self.create_refresh_token(
            token=new_token,
            jti=new_jti,
            session_id=old_instance.session_id,
            user_id=old_instance.user_id,
            expires_at=new_expires_at,
            access_token_jti=new_access_token_jti,
            ip_address=old_instance.ip_address,
            user_agent=old_instance.user_agent,
            metadata=old_instance.metadata,
            commit=False
        )
        
        if commit:
            await self.db.commit()
            await self.db.refresh(old_instance)
            await self.db.refresh(new_instance)
        
        return old_instance, new_instance
    
    # ==================== TOKEN PAIR OPERATIONS ====================
    
    async def create_token_pair(
        self,
        access_token: str,
        access_jti: str,
        refresh_token: str,
        refresh_jti: str,
        session_id: UUID,
        user_id: UUID,
        access_expires_at: datetime,
        refresh_expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[str] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> Tuple[AccessToken, RefreshToken]:
        """
        Create a token pair (access + refresh).
        
        Args:
            access_token: Access token string
            access_jti: Access token JTI
            refresh_token: Refresh token string
            refresh_jti: Refresh token JTI
            session_id: Session ID
            user_id: User ID
            access_expires_at: Access token expiration
            refresh_expires_at: Refresh token expiration
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Tuple of (AccessToken, RefreshToken)
        """
        # Create access token
        access = await self.create_access_token(
            token=access_token,
            jti=access_jti,
            session_id=session_id,
            user_id=user_id,
            expires_at=access_expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            created_by=created_by,
            commit=False
        )
        
        # Create refresh token
        refresh = await self.create_refresh_token(
            token=refresh_token,
            jti=refresh_jti,
            session_id=session_id,
            user_id=user_id,
            expires_at=refresh_expires_at,
            access_token_jti=access_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            created_by=created_by,
            commit=False
        )
        
        if commit:
            await self.db.commit()
            await self.db.refresh(access)
            await self.db.refresh(refresh)
        
        return access, refresh
    
    async def revoke_token_pair(
        self,
        access_token: str,
        refresh_token: str,
        revoked_by: Optional[UUID] = None,
        commit: bool = True
    ) -> Tuple[bool, bool]:
        """
        Revoke a token pair.
        
        Args:
            access_token: Access token string
            refresh_token: Refresh token string
            revoked_by: User ID who revoked the tokens
            commit: Whether to commit immediately
            
        Returns:
            Tuple of (access_revoked, refresh_revoked)
        """
        access_revoked = await self.revoke_access_token(access_token, revoked_by, False)
        refresh_revoked = await self.revoke_refresh_token(refresh_token, revoked_by, False)
        
        if commit:
            await self.db.commit()
        
        return access_revoked, refresh_revoked
    
    # ==================== CLEANUP OPERATIONS ====================
    
    async def cleanup_expired_tokens(
        self,
        commit: bool = True
    ) -> Tuple[int, int]:
        """
        Clean up expired tokens (both access and refresh).
        
        Args:
            commit: Whether to commit immediately
            
        Returns:
            Tuple of (access_tokens_cleaned, refresh_tokens_cleaned)
        """
        now = datetime.utcnow()
        
        # Clean up expired access tokens
        access_query = update(AccessToken).where(
            AccessToken.status == TokenStatus.ACTIVE,
            AccessToken.expires_at <= now,
            AccessToken.is_active == True
        ).values(status=TokenStatus.EXPIRED)
        
        access_result = await self.db.execute(access_query)
        
        # Clean up expired refresh tokens
        refresh_query = update(RefreshToken).where(
            RefreshToken.status == TokenStatus.ACTIVE,
            RefreshToken.expires_at <= now,
            RefreshToken.is_active == True
        ).values(status=TokenStatus.EXPIRED)
        
        refresh_result = await self.db.execute(refresh_query)
        
        if commit:
            await self.db.commit()
        
        return access_result.rowcount, refresh_result.rowcount
    
    async def cleanup_revoked_tokens(
        self,
        days: int = 30,
        commit: bool = True
    ) -> Tuple[int, int]:
        """
        Delete revoked tokens older than specified days.
        
        Args:
            days: Number of days to keep revoked tokens
            commit: Whether to commit immediately
            
        Returns:
            Tuple of (access_tokens_deleted, refresh_tokens_deleted)
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Soft delete revoked access tokens
        access_query = update(AccessToken).where(
            AccessToken.status == TokenStatus.REVOKED,
            AccessToken.revoked_at <= cutoff,
            AccessToken.is_active == True
        ).values(is_active=False)
        
        access_result = await self.db.execute(access_query)
        
        # Soft delete revoked refresh tokens
        refresh_query = update(RefreshToken).where(
            RefreshToken.status == TokenStatus.REVOKED,
            RefreshToken.revoked_at <= cutoff,
            RefreshToken.is_active == True
        ).values(is_active=False)
        
        refresh_result = await self.db.execute(refresh_query)
        
        if commit:
            await self.db.commit()
        
        return access_result.rowcount, refresh_result.rowcount
    
    # ==================== VALIDATION OPERATIONS ====================
    
    async def validate_token(
        self,
        token: str,
        token_type: TokenType
    ) -> Dict[str, Any]:
        """
        Validate a token (access or refresh).
        
        Args:
            token: Token string
            token_type: Type of token
            
        Returns:
            Dictionary with validation result
        """
        if token_type == TokenType.ACCESS:
            instance = await self.get_access_token(token, include_revoked=True)
        else:
            instance = await self.get_refresh_token(token, include_revoked=True)
        
        if not instance:
            return {
                "valid": False,
                "reason": "token_not_found",
                "instance": None,
            }
        
        now = datetime.utcnow()
        
        # Check if soft-deleted
        if not instance.is_active:
            return {
                "valid": False,
                "reason": "token_deleted",
                "instance": instance,
            }
        
        # Check status
        if instance.status == TokenStatus.REVOKED:
            return {
                "valid": False,
                "reason": "token_revoked",
                "instance": instance,
                "revoked_at": instance.revoked_at,
            }
        
        if instance.status == TokenStatus.EXPIRED:
            return {
                "valid": False,
                "reason": "token_expired",
                "instance": instance,
            }
        
        # Check expiry
        if instance.expires_at <= now:
            return {
                "valid": False,
                "reason": "token_expired",
                "instance": instance,
            }
        
        return {
            "valid": True,
            "reason": "token_valid",
            "instance": instance,
            "time_remaining": int((instance.expires_at - now).total_seconds()),
        }


__all__ = ['TokenRepository']