# app/modules/auth/services/session_service.py
"""
Session service for session management.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from app.modules.auth.domain.session_manager import SessionManager
from app.modules.auth.repositories.session_repository import SessionRepository
from app.modules.auth.repositories.token_repository import TokenRepository
from app.modules.auth.models.session import Session
from app.modules.auth.exceptions import UserNotFoundError

from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionService:
    """
    Session service for session management.
    
    Handles:
    - Session retrieval and listing
    - Session termination
    - Session validation
    - Session cleanup
    """
    
    def __init__(
        self,
        session_repo: SessionRepository,
        token_repo: TokenRepository,
        session_manager: Optional[SessionManager] = None,
    ):
        self.session_repo = session_repo
        self.token_repo = token_repo
        self.session_manager = session_manager or SessionManager()
        self.logger = get_logger(self.__class__.__name__)
    
    # ==================== SESSION RETRIEVAL ====================
    
    async def get_session(self, session_id: UUID) -> Optional[Session]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session instance or None
        """
        return await self.session_repo.get(session_id)
    
    async def get_session_by_token(
        self,
        session_token: str,
    ) -> Optional[Session]:
        """
        Get session by token.
        
        Args:
            session_token: Session token
            
        Returns:
            Session instance or None
        """
        return await self.session_repo.get_by_token(session_token)
    
    async def get_user_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Session]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of sessions
        """
        return await self.session_repo.get_all_sessions(
            user_id,
            limit=limit,
            offset=offset,
            include_expired=True,
        )
    
    async def get_active_sessions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
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
        return await self.session_repo.get_active_sessions(
            user_id,
            limit=limit,
            offset=offset,
        )
    
    async def count_active_sessions(
        self,
        user_id: UUID,
    ) -> int:
        """
        Count active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of active sessions
        """
        return await self.session_repo.count_active_sessions(user_id)
    
    # ==================== SESSION TERMINATION ====================
    
    async def terminate_session(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Terminate a specific session.
        
        Args:
            session_id: Session ID
            user_id: User ID (for verification)
            
        Returns:
            True if terminated successfully
            
        Raises:
            UserNotFoundError: If user not found
        """
        # Verify session belongs to user
        session = await self.session_repo.get_or_raise(session_id)
        if session.user_id != user_id:
            raise UserNotFoundError("Session does not belong to this user")
        
        # Terminate session
        await self.session_repo.terminate_session(session_id, terminated_by=user_id)
        
        # Revoke all tokens for this session
        await self.token_repo.revoke_access_tokens_by_session(session_id, revoked_by=user_id)
        await self.token_repo.revoke_refresh_tokens_by_session(session_id, revoked_by=user_id)
        
        self.logger.info(f"Session {session_id} terminated by user {user_id}")
        return True
    
    async def terminate_all_sessions(
        self,
        user_id: UUID,
        except_session_id: Optional[UUID] = None,
    ) -> int:
        """
        Terminate all sessions for a user.
        
        Args:
            user_id: User ID
            except_session_id: Session ID to keep active
            
        Returns:
            Number of sessions terminated
        """
        count = await self.session_repo.terminate_all_sessions(
            user_id,
            except_session_id=except_session_id,
            terminated_by=user_id,
        )
        
        self.logger.info(f"All sessions for user {user_id} terminated, except {except_session_id}")
        return count
    
    async def expire_session(
        self,
        session_id: UUID,
    ) -> Session:
        """
        Expire a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Updated Session instance
        """
        session = await self.session_repo.expire_session(session_id)
        
        self.logger.info(f"Session {session_id} expired")
        return session
    
    # ==================== SESSION VALIDATION ====================
    
    async def validate_session(
        self,
        session_token: str,
    ) -> Dict[str, Any]:
        """
        Validate a session.
        
        Args:
            session_token: Session token
            
        Returns:
            Validation result
        """
        return await self.session_repo.validate_session(session_token)
    
    async def update_session_activity(
        self,
        session_id: UUID,
    ) -> Session:
        """
        Update session activity timestamp.
        
        Args:
            session_id: Session ID
            
        Returns:
            Updated Session instance
        """
        return await self.session_repo.update_activity(session_id)
    
    async def update_session_activity_by_token(
        self,
        session_token: str,
    ) -> Optional[Session]:
        """
        Update session activity by token.
        
        Args:
            session_token: Session token
            
        Returns:
            Updated Session instance or None
        """
        return await self.session_repo.update_activity_by_token(session_token)
    
    # ==================== SESSION 2FA ====================
    
    async def verify_session_2fa(
        self,
        session_id: UUID,
        verified: bool = True,
    ) -> Session:
        """
        Update session 2FA verification status.
        
        Args:
            session_id: Session ID
            verified: Whether 2FA is verified
            
        Returns:
            Updated Session instance
        """
        return await self.session_repo.update_2fa_status(session_id, verified)
    
    # ==================== SESSION CLEANUP ====================
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        count = await self.session_repo.cleanup_expired_sessions()
        self.logger.info(f"Cleaned up {count} expired sessions")
        return count
    
    async def cleanup_terminated_sessions(
        self,
        days: int = 30,
    ) -> int:
        """
        Clean up terminated sessions older than specified days.
        
        Args:
            days: Number of days to keep terminated sessions
            
        Returns:
            Number of sessions deleted
        """
        count = await self.session_repo.cleanup_terminated_sessions(days)
        self.logger.info(f"Cleaned up {count} terminated sessions older than {days} days")
        return count
    
    # ==================== SESSION INFO ====================
    
    async def get_session_info(
        self,
        session_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get detailed session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information
            
        Raises:
            UserNotFoundError: If session not found
        """
        session = await self.session_repo.get_or_raise(session_id)
        
        # Get token counts
        access_tokens = await self.token_repo.get_access_tokens_by_session(session_id)
        refresh_tokens = await self.token_repo.get_refresh_tokens_by_session(session_id)
        
        return {
            "session": session.to_dict(),
            "access_tokens_count": len(access_tokens),
            "refresh_tokens_count": len(refresh_tokens),
            "access_tokens": [t.to_dict() for t in access_tokens[:5]],  # Limit for response
        }
    
    async def get_user_session_summary(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get session summary for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Session summary
        """
        active_sessions = await self.get_active_sessions(user_id)
        
        return {
            "user_id": str(user_id),
            "total_active_sessions": len(active_sessions),
            "active_sessions": [s.to_dict() for s in active_sessions[:10]],
            "devices": list(set(s.device_type for s in active_sessions if s.device_type)),
        }


__all__ = ['SessionService']