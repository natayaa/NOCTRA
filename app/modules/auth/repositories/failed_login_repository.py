# app/modules/auth/repositories/failed_login_repository.py
"""
Failed Login repository for tracking failed login attempts.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_repository import BaseRepository
from app.modules.auth.models.failed_login import FailedLogin
from app.modules.auth.enums import LoginType
from app.core.logging import get_logger

logger = get_logger(__name__)


class FailedLoginRepository(BaseRepository[FailedLogin]):
    """
    Repository for FailedLogin model operations.
    
    Handles tracking and querying failed login attempts for security monitoring.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(FailedLogin, db)
    
    # ==================== CREATE OPERATIONS ====================
    
    async def log_failed_attempt(
        self,
        identifier: str,
        identifier_type: str = "email",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        login_type: LoginType = LoginType.WEB,
        reason: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> FailedLogin:
        """
        Log a failed login attempt.
        
        Args:
            identifier: Email, phone, username, or IP
            identifier_type: Type of identifier
            ip_address: Client IP address
            user_agent: Client user agent
            login_type: Type of login attempt
            reason: Reason for failure
            error_code: Error code
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created FailedLogin instance
        """
        data = {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "login_type": login_type,
            "attempt_time": datetime.utcnow(),
            "reason": reason,
            "error_code": error_code,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        return await self.create(data, commit=commit)
    
    # ==================== QUERY OPERATIONS ====================
    
    async def get_recent_attempts(
        self,
        identifier: str,
        minutes: int = 5
    ) -> List[FailedLogin]:
        """
        Get recent failed login attempts for an identifier.
        
        Args:
            identifier: Email, phone, username, or IP
            minutes: Time window in minutes
            
        Returns:
            List of failed login attempts
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = select(FailedLogin).where(
            FailedLogin.identifier == identifier,
            FailedLogin.attempt_time >= cutoff,
            FailedLogin.is_active == True
        ).order_by(FailedLogin.attempt_time.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_attempt_count(
        self,
        identifier: str,
        minutes: int = 5,
        ip_address: Optional[str] = None
    ) -> int:
        """
        Get count of recent failed login attempts.
        
        Args:
            identifier: Email, phone, username, or IP
            minutes: Time window in minutes
            ip_address: Optional IP address to filter
            
        Returns:
            Number of attempts
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = select(func.count()).select_from(FailedLogin).where(
            FailedLogin.identifier == identifier,
            FailedLogin.attempt_time >= cutoff,
            FailedLogin.is_active == True
        )
        
        if ip_address:
            query = query.where(FailedLogin.ip_address == ip_address)
        
        result = await self.db.execute(query)
        return result.scalar_one() or 0
    
    async def get_attempts_by_identifier(
        self,
        identifier: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[FailedLogin]:
        """
        Get failed login attempts by identifier with pagination.
        
        Args:
            identifier: Email, phone, username, or IP
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of failed login attempts
        """
        query = select(FailedLogin).where(
            FailedLogin.identifier == identifier,
            FailedLogin.is_active == True
        ).order_by(
            FailedLogin.attempt_time.desc()
        ).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_attempts_by_ip(
        self,
        ip_address: str,
        minutes: Optional[int] = None,
        limit: int = 50
    ) -> List[FailedLogin]:
        """
        Get failed login attempts by IP address.
        
        Args:
            ip_address: Client IP address
            minutes: Optional time window in minutes
            limit: Maximum number of records
            
        Returns:
            List of failed login attempts
        """
        query = select(FailedLogin).where(
            FailedLogin.ip_address == ip_address,
            FailedLogin.is_active == True
        )
        
        if minutes:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)
            query = query.where(FailedLogin.attempt_time >= cutoff)
        
        query = query.order_by(FailedLogin.attempt_time.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ==================== STATISTICS OPERATIONS ====================
    
    async def get_statistics(
        self,
        identifier: Optional[str] = None,
        ip_address: Optional[str] = None,
        minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for failed login attempts.
        
        Args:
            identifier: Optional identifier to filter
            ip_address: Optional IP address to filter
            minutes: Optional time window in minutes
            
        Returns:
            Dictionary with statistics
        """
        query = select(
            func.count().label("total_attempts"),
            func.count(func.distinct(FailedLogin.identifier)).label("unique_identifiers"),
            func.count(func.distinct(FailedLogin.ip_address)).label("unique_ips"),
        ).select_from(FailedLogin).where(FailedLogin.is_active == True)
        
        conditions = []
        
        if identifier:
            conditions.append(FailedLogin.identifier == identifier)
        
        if ip_address:
            conditions.append(FailedLogin.ip_address == ip_address)
        
        if minutes:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)
            conditions.append(FailedLogin.attempt_time >= cutoff)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        row = result.one()
        
        # Get breakdown by error code
        error_query = select(
            FailedLogin.error_code,
            func.count().label("count")
        ).select_from(FailedLogin).where(FailedLogin.is_active == True)
        
        if conditions:
            error_query = error_query.where(and_(*conditions))
        
        error_query = error_query.group_by(FailedLogin.error_code).order_by(
            func.count().desc()
        ).limit(10)
        
        error_result = await self.db.execute(error_query)
        error_breakdown = {row.error_code: row.count for row in error_result.all()}
        
        return {
            "total_attempts": row.total_attempts or 0,
            "unique_identifiers": row.unique_identifiers or 0,
            "unique_ips": row.unique_ips or 0,
            "error_breakdown": error_breakdown,
            "identifier": identifier,
            "ip_address": ip_address,
            "time_window_minutes": minutes,
        }
    
    # ==================== CLEANUP OPERATIONS ====================
    
    async def cleanup_old_attempts(
        self,
        days: int = 30,
        commit: bool = True
    ) -> int:
        """
        Delete failed login attempts older than specified days.
        
        Args:
            days: Number of days to keep
            commit: Whether to commit immediately
            
        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = select(FailedLogin).where(
            FailedLogin.attempt_time < cutoff,
            FailedLogin.is_active == True
        )
        
        result = await self.db.execute(query)
        attempts = result.scalars().all()
        
        for attempt in attempts:
            attempt.soft_delete()
        
        if commit:
            await self.db.commit()
        
        logger.info(f"Soft-deleted {len(attempts)} failed login attempts older than {days} days")
        return len(attempts)


__all__ = ['FailedLoginRepository']