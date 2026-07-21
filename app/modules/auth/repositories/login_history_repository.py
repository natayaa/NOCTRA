# app/modules/auth/repositories/login_history_repository.py
"""
Login History repository for tracking login events.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_repository import BaseRepository
from app.modules.auth.models.login_history import LoginHistory
from app.modules.auth.enums import LoginType
from app.core.logging import get_logger

logger = get_logger(__name__)


class LoginHistoryRepository(BaseRepository[LoginHistory]):
    """
    Repository for LoginHistory model operations.
    
    Handles tracking and querying login events for audit purposes.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(LoginHistory, db)
    
    # ==================== CREATE OPERATIONS ====================
    
    async def log_login_attempt(
        self,
        user_id: UUID,
        login_type: LoginType = LoginType.WEB,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        login_method: Optional[str] = None,
        is_successful: bool = False,
        is_2fa_required: bool = False,
        is_2fa_verified: bool = False,
        failure_reason: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> LoginHistory:
        """
        Log a login attempt.
        
        Args:
            user_id: User ID
            login_type: Type of login
            ip_address: Client IP address
            user_agent: Client user agent
            device_id: Device identifier
            device_name: Device name
            login_method: Login method (password, otp, social, etc)
            is_successful: Whether login was successful
            is_2fa_required: Whether 2FA was required
            is_2fa_verified: Whether 2FA was verified
            failure_reason: Reason for failure
            error_code: Error code
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created LoginHistory instance
        """
        data = {
            "user_id": user_id,
            "login_type": login_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id,
            "device_name": device_name,
            "login_method": login_method,
            "is_successful": is_successful,
            "is_2fa_required": is_2fa_required,
            "is_2fa_verified": is_2fa_verified,
            "failure_reason": failure_reason,
            "error_code": error_code,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        return await self.create(data, commit=commit)
    
    async def log_successful_login(
        self,
        user_id: UUID,
        session_id: UUID,
        login_type: LoginType = LoginType.WEB,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        login_method: Optional[str] = None,
        is_2fa_required: bool = False,
        is_2fa_verified: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> LoginHistory:
        """
        Log a successful login.
        
        Args:
            user_id: User ID
            session_id: Session ID
            login_type: Type of login
            ip_address: Client IP address
            user_agent: Client user agent
            device_id: Device identifier
            device_name: Device name
            login_method: Login method
            is_2fa_required: Whether 2FA was required
            is_2fa_verified: Whether 2FA was verified
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created LoginHistory instance
        """
        data = {
            "user_id": user_id,
            "session_id": session_id,
            "login_type": login_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id,
            "device_name": device_name,
            "login_method": login_method,
            "is_successful": True,
            "is_2fa_required": is_2fa_required,
            "is_2fa_verified": is_2fa_verified,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        return await self.create(data, commit=commit)
    
    async def log_failed_login(
        self,
        user_id: UUID,
        login_type: LoginType = LoginType.WEB,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        login_method: Optional[str] = None,
        failure_reason: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> LoginHistory:
        """
        Log a failed login.
        
        Args:
            user_id: User ID
            login_type: Type of login
            ip_address: Client IP address
            user_agent: Client user agent
            device_id: Device identifier
            device_name: Device name
            login_method: Login method
            failure_reason: Reason for failure
            error_code: Error code
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created LoginHistory instance
        """
        data = {
            "user_id": user_id,
            "login_type": login_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id,
            "device_name": device_name,
            "login_method": login_method,
            "is_successful": False,
            "failure_reason": failure_reason,
            "error_code": error_code,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        return await self.create(data, commit=commit)
    
    # ==================== QUERY OPERATIONS ====================
    
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        successful_only: bool = False
    ) -> List[LoginHistory]:
        """
        Get login history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination
            successful_only: Only return successful logins
            
        Returns:
            List of login history records
        """
        query = select(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.is_active == True
        )
        
        if successful_only:
            query = query.where(LoginHistory.is_successful == True)
        
        query = query.order_by(LoginHistory.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_session_id(
        self,
        session_id: UUID
    ) -> Optional[LoginHistory]:
        """
        Get login history by session ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            LoginHistory or None
        """
        query = select(LoginHistory).where(
            LoginHistory.session_id == session_id,
            LoginHistory.is_active == True
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_recent_logins(
        self,
        user_id: UUID,
        days: int = 7
    ) -> List[LoginHistory]:
        """
        Get recent logins for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of recent login history records
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.created_at >= cutoff,
            LoginHistory.is_successful == True,
            LoginHistory.is_active == True
        ).order_by(LoginHistory.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_last_login(
        self,
        user_id: UUID
    ) -> Optional[LoginHistory]:
        """
        Get the last successful login for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Last login record or None
        """
        query = select(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.is_successful == True,
            LoginHistory.is_active == True
        ).order_by(LoginHistory.created_at.desc()).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_login_count(
        self,
        user_id: UUID,
        days: int = 30
    ) -> int:
        """
        Get login count for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Login count
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(func.count()).select_from(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.created_at >= cutoff,
            LoginHistory.is_successful == True,
            LoginHistory.is_active == True
        )
        
        result = await self.db.execute(query)
        return result.scalar_one() or 0
    
    # ==================== STATISTICS OPERATIONS ====================
    
    async def get_user_statistics(
        self,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get login statistics for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Total logins
        total_query = select(func.count()).select_from(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.created_at >= cutoff,
            LoginHistory.is_active == True
        )
        total_result = await self.db.execute(total_query)
        total_logins = total_result.scalar_one() or 0
        
        # Successful logins
        success_query = select(func.count()).select_from(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.created_at >= cutoff,
            LoginHistory.is_successful == True,
            LoginHistory.is_active == True
        )
        success_result = await self.db.execute(success_query)
        successful_logins = success_result.scalar_one() or 0
        
        # Unique devices
        devices_query = select(
            func.count(func.distinct(LoginHistory.device_id))
        ).select_from(LoginHistory).where(
            LoginHistory.user_id == user_id,
            LoginHistory.created_at >= cutoff,
            LoginHistory.device_id.isnot(None),
            LoginHistory.is_active == True
        )
        devices_result = await self.db.execute(devices_query)
        unique_devices = devices_result.scalar_one() or 0
        
        return {
            "user_id": str(user_id),
            "total_logins": total_logins,
            "successful_logins": successful_logins,
            "failed_logins": total_logins - successful_logins,
            "success_rate": (successful_logins / total_logins * 100) if total_logins > 0 else 0,
            "unique_devices": unique_devices,
            "days": days,
        }
    
    # ==================== CLEANUP OPERATIONS ====================
    
    async def cleanup_old_history(
        self,
        days: int = 90,
        commit: bool = True
    ) -> int:
        """
        Delete login history older than specified days.
        
        Args:
            days: Number of days to keep
            commit: Whether to commit immediately
            
        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(LoginHistory).where(
            LoginHistory.created_at < cutoff,
            LoginHistory.is_active == True
        )
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        for record in records:
            record.soft_delete()
        
        if commit:
            await self.db.commit()
        
        logger.info(f"Soft-deleted {len(records)} login history records older than {days} days")
        return len(records)


__all__ = ['LoginHistoryRepository']