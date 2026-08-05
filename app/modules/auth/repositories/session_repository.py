# app/modules/auth/repositories/session_repository.py
"""
Session repository for user session management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_repository import BaseRepository
from app.modules.auth.models.session import Session
from app.modules.auth.enums import SessionStatus, LoginType
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionRepository(BaseRepository[Session]):
    """
    Repository for Session model operations.
    
    Handles user session management across devices and platforms.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(Session, db)
    
    # ==================== CREATE OPERATIONS ====================
    
    async def create_session(
        self,
        user_id: UUID,
        session_token: str,
        login_type: LoginType = LoginType.WEB,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        os_name: Optional[str] = None,
        os_version: Optional[str] = None,
        browser_name: Optional[str] = None,
        browser_version: Optional[str] = None,
        location: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[UUID] = None,
        commit: bool = True
    ) -> Session:
        """
        Create a new session.
        
        Args:
            user_id: User ID
            session_token: Unique session token
            login_type: Type of login
            ip_address: Client IP address
            user_agent: Client user agent
            device_id: Device identifier
            device_name: Device name
            device_type: Device type
            os_name: Operating system name
            os_version: Operating system version
            browser_name: Browser name
            browser_version: Browser version
            location: Geographic location
            country: Country code
            city: City name
            expires_in: Session expiry in seconds (default from constants)
            metadata: Additional metadata
            created_by: User ID who created this record
            commit: Whether to commit immediately
            
        Returns:
            Created Session instance
        """
        from app.modules.auth.constants import AuthConstants
        
        expires_in = expires_in or AuthConstants.SESSION_MAX_AGE
        now = datetime.utcnow()
        
        data = {
            "user_id": user_id,
            "session_token": session_token,
            "login_type": login_type,
            "status": SessionStatus.ACTIVE,
            "expires_at": now + timedelta(seconds=expires_in),
            "last_activity": now,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "os_name": os_name,
            "os_version": os_version,
            "browser_name": browser_name,
            "browser_version": browser_version,
            "location": location,
            "country": country,
            "city": city,
            "is_2fa_verified": False,
            "metadata": metadata,
            "created_by": created_by,
        }
        
        return await self.create(data, commit=commit)
    
    # ==================== QUERY OPERATIONS ====================
    
    async def get_by_token(
        self,
        session_token: str,
        include_deleted: bool = False,
        load_relations: Optional[List[str]] = None
    ) -> Optional[Session]:
        """
        Get session by token.
        
        Args:
            session_token: Session token
            include_deleted: Whether to include soft-deleted records
            load_relations: List of relationship names to eager load
            
        Returns:
            Session instance or None
        """
        return await self.get_by_field('session_token', session_token, include_deleted, load_relations)
    
    async def get_by_token_or_raise(
        self,
        session_token: str,
        load_relations: Optional[List[str]] = None
    ) -> Session:
        """
        Get session by token or raise NotFoundError.
        
        Args:
            session_token: Session token
            load_relations: List of relationship names to eager load
            
        Returns:
            Session instance
            
        Raises:
            NotFoundError: If session not found
        """
        session = await self.get_by_token(session_token, load_relations=load_relations)
        if not session:
            raise NotFoundError(f"Session not found")
        return session
    
    async def get_active_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """
        Get active sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of active sessions
        """
        now = datetime.utcnow()
        
        query = select(Session).where(
            Session.user_id == user_id,
            Session.status == SessionStatus.ACTIVE,
            Session.expires_at > now,
            Session.is_active == True
        ).order_by(Session.last_activity.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def count_active_sessions(
        self,
        user_id: UUID
    ) -> int:
        """
        Count active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of active sessions
        """
        now = datetime.utcnow()
        
        query = select(func.count()).select_from(Session).where(
            Session.user_id == user_id,
            Session.status == SessionStatus.ACTIVE,
            Session.expires_at > now,
            Session.is_active == True
        )
        
        result = await self.db.execute(query)
        return result.scalar_one() or 0
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_activity(
        self,
        session_id: UUID,
        commit: bool = True
    ) -> Session:
        """
        Update session last activity time.
        
        Args:
            session_id: Session ID
            commit: Whether to commit immediately
            
        Returns:
            Updated Session instance
            
        Raises:
            NotFoundError: If session not found
        """
        session = await self.get_or_raise(session_id)
        session.touch()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(session)
        
        return session
    
    async def update_activity_by_token(
        self,
        session_token: str,
        commit: bool = True
    ) -> Optional[Session]:
        """
        Update session last activity time by token.
        
        Args:
            session_token: Session token
            commit: Whether to commit immediately
            
        Returns:
            Updated Session instance or None
        """
        session = await self.get_by_token(session_token)
        if not session:
            return None
        
        return await self.update_activity(session.id, commit)
    
    async def update_2fa_status(
        self,
        session_id: UUID,
        verified: bool = True,
        commit: bool = True
    ) -> Session:
        """
        Update session 2FA verification status.
        
        Args:
            session_id: Session ID
            verified: Whether 2FA is verified
            commit: Whether to commit immediately
            
        Returns:
            Updated Session instance
            
        Raises:
            NotFoundError: If session not found
        """
        session = await self.get_or_raise(session_id)
        
        if verified:
            session.verify_2fa()
        else:
            session.unverify_2fa()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(session)
        
        return session
    
    async def expire_session(
        self,
        session_id: UUID,
        commit: bool = True
    ) -> Session:
        """
        Expire a session.
        
        Args:
            session_id: Session ID
            commit: Whether to commit immediately
            
        Returns:
            Updated Session instance
            
        Raises:
            NotFoundError: If session not found
        """
        session = await self.get_or_raise(session_id)
        session.expire()
        
        if commit:
            await self.db.commit()
            await self.db.refresh(session)
        
        return session
    
    async def terminate_session(
        self,
        session_id: UUID,
        terminated_by: Optional[UUID] = None,
        commit: bool = True
    ) -> Session:
        """
        Terminate a session.
        
        Args:
            session_id: Session ID
            terminated_by: User ID who terminated the session
            commit: Whether to commit immediately
            
        Returns:
            Updated Session instance
            
        Raises:
            NotFoundError: If session not found
        """
        session = await self.get_or_raise(session_id)
        session.terminate(terminated_by)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(session)
        
        return session
    
    async def terminate_all_sessions(
        self,
        user_id: UUID,
        except_session_id: Optional[UUID] = None,
        terminated_by: Optional[UUID] = None,
        commit: bool = True
    ) -> int:
        """
        Terminate all sessions for a user except one.
        
        Args:
            user_id: User ID
            except_session_id: Session ID to exclude from termination
            terminated_by: User ID who terminated the sessions
            commit: Whether to commit immediately
            
        Returns:
            Number of sessions terminated
        """
        query = update(Session).where(
            Session.user_id == user_id,
            Session.status == SessionStatus.ACTIVE,
            Session.is_active == True
        )
        
        if except_session_id:
            query = query.where(Session.id != except_session_id)
        
        query = query.values(
            status=SessionStatus.TERMINATED,
            terminated_at=datetime.utcnow(),
            terminated_by=terminated_by
        )
        
        result = await self.db.execute(query)
        
        if commit:
            await self.db.commit()
        
        return result.rowcount
    
    # ==================== VALIDATION OPERATIONS ====================
    
    async def validate_session(
        self,
        session_token: str
    ) -> Dict[str, Any]:
        """
        Validate a session and return status information.
        
        Args:
            session_token: Session token
            
        Returns:
            Dictionary with validation result
        """
        session = await self.get_by_token(session_token, load_relations=['access_tokens'])
        
        if not session:
            return {
                "valid": False,
                "reason": "session_not_found",
                "session": None,
            }
        
        now = datetime.utcnow()
        
        # Check status
        if session.status != SessionStatus.ACTIVE:
            return {
                "valid": False,
                "reason": f"session_{session.status.value}",
                "session": session,
            }
        
        # Check if soft-deleted
        if not session.is_active:
            return {
                "valid": False,
                "reason": "session_deleted",
                "session": session,
            }
        
        # Check expiry
        if session.expires_at <= now:
            return {
                "valid": False,
                "reason": "session_expired",
                "session": session,
            }
        
        # Check idle timeout (8 hours)
        idle_seconds = (now - session.last_activity).total_seconds()
        if idle_seconds > 3600 * 8:
            return {
                "valid": False,
                "reason": "session_idle_timeout",
                "session": session,
                "idle_seconds": int(idle_seconds),
            }
        
        return {
            "valid": True,
            "reason": "session_valid",
            "session": session,
            "time_remaining": int((session.expires_at - now).total_seconds()),
            "idle_seconds": int(idle_seconds),
        }


__all__ = ['SessionRepository']