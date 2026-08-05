# app/modules/auth/domain/session_manager.py
"""
Session management domain logic.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.modules.auth.constants import AuthConstants
from app.modules.auth.enums import SessionStatus, LoginType


class SessionManager:
    """
    Domain service for session management.
    Handles session creation, validation and lifecycle.
    """
    
    def __init__(self):
        self.session_max_age = AuthConstants.SESSION_MAX_AGE
        self.refresh_threshold = AuthConstants.SESSION_REFRESH_THRESHOLD
    
    def create_session_data(
        self,
        user_id: UUID,
        login_type: LoginType = LoginType.WEB,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create session data for storage.
        
        Args:
            user_id: User identifier
            login_type: Type of login
            ip_address: Client IP address
            user_agent: Client user agent
            device_info: Device information
            
        Returns:
            Session data dictionary
        """
        now = datetime.utcnow()
        session_token = self._generate_session_token()
        device_info = device_info or {}
        
        return {
            "user_id": user_id,
            "session_token": session_token,
            "login_type": login_type,
            "status": SessionStatus.ACTIVE,
            "expires_at": now + timedelta(seconds=self.session_max_age),
            "last_activity": now,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "is_2fa_verified": False,
            **self._extract_device_info(device_info)
        }
    
    def update_session_activity(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update session last activity time.
        
        Args:
            session_data: Existing session data
            
        Returns:
            Updated session data
        """
        session_data["last_activity"] = datetime.utcnow()
        return session_data
    
    def is_session_active(self, session_data: Dict[str, Any]) -> bool:
        """
        Check if session is active.
        
        Args:
            session_data: Session data
            
        Returns:
            True if session is active
        """
        if session_data.get('status') != SessionStatus.ACTIVE.value:
            return False
        
        expires_at = session_data.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            
            if expires_at <= datetime.utcnow():
                return False
        
        return True
    
    def is_session_expired(self, session_data: Dict[str, Any]) -> bool:
        """
        Check if session is expired.
        
        Args:
            session_data: Session data
            
        Returns:
            True if session is expired
        """
        expires_at = session_data.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            
            return expires_at <= datetime.utcnow()
        
        return False
    
    def is_session_idle(
        self,
        session_data: Dict[str, Any],
        max_idle: int = 28800  # 8 hours default
    ) -> bool:
        """
        Check if session is idle for too long.
        
        Args:
            session_data: Session data
            max_idle: Maximum idle time in seconds
            
        Returns:
            True if session is idle
        """
        last_activity = session_data.get("last_activity")
        if last_activity:
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity)
            
            idle_seconds = (datetime.utcnow() - last_activity).total_seconds()
            return idle_seconds > max_idle
        
        return False
    
    def needs_2fa_verification(self, session_data: Dict[str, Any]) -> bool:
        """
        Check if session needs 2FA verification.
        
        Args:
            session_data: Session data
            
        Returns:
            True if 2FA is required but not verified
        """
        return not session_data.get("is_2fa_verified", False)
    
    def mark_2fa_verified(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mark session as 2FA verified.
        
        Args:
            session_data: Session data
            
        Returns:
            Updated session data
        """
        session_data["is_2fa_verified"] = True
        return session_data
    
    def get_session_expiry_info(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get session expiry information.
        
        Args:
            session_data: Session data
            
        Returns:
            Dictionary with expiry information
        """
        now = datetime.utcnow()
        expires_at = session_data.get("expires_at")
        
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            time_remaining = max(0, int((expires_at - now).total_seconds()))
        else:
            time_remaining = 0
        
        last_activity = session_data.get("last_activity")
        if last_activity:
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity)
            idle_time = int((now - last_activity).total_seconds())
        else:
            idle_time = 0
        
        return {
            "expires_at": expires_at.isoformat() if expires_at else None,
            "time_remaining": time_remaining,
            "idle_time": idle_time,
            "is_expired": self.is_session_expired(session_data),
            "is_idle": self.is_session_idle(session_data),
        }
    
    def generate_session_metadata(
        self,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate session metadata from request data.
        
        Args:
            request_data: Request data (IP, user-agent, etc.)
            
        Returns:
            Session metadata
        """
        user_agent = request_data.get("user_agent")
        
        return {
            "ip_address": request_data.get("ip_address"),
            "user_agent": user_agent,
            "device_id": request_data.get("device_id"),
            "device_name": request_data.get("device_name"),
            "device_type": self._detect_device_type(user_agent),
            "os_name": self._detect_os(user_agent),
            "browser_name": self._detect_browser(user_agent),
        }
    
    def _generate_session_token(self) -> str:
        """Generate a unique session token."""
        import secrets
        return f"ses_{secrets.token_urlsafe(32)}"
    
    def _extract_device_info(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract device information from device info dict."""
        return {
            "device_id": device_info.get("device_id"),
            "device_name": device_info.get("device_name"),
            "device_type": device_info.get("device_type"),
            "os_name": device_info.get("os_name"),
            "os_version": device_info.get("os_version"),
            "browser_name": device_info.get("browser_name"),
            "browser_version": device_info.get("browser_version"),
        }
    
    def _detect_device_type(self, user_agent: Optional[str]) -> str:
        """Detect device type from user agent."""
        if not user_agent:
            return "unknown"
        
        ua = user_agent.lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            return "mobile"
        if "tablet" in ua or "ipad" in ua:
            return "tablet"
        return "desktop"
    
    def _detect_os(self, user_agent: Optional[str]) -> str:
        """Detect operating system from user agent."""
        if not user_agent:
            return "unknown"
        
        ua = user_agent.lower()
        if "windows" in ua:
            return "windows"
        if "mac" in ua or "darwin" in ua:
            return "macos"
        if "linux" in ua:
            return "linux"
        if "android" in ua:
            return "android"
        if "iphone" in ua or "ios" in ua:
            return "ios"
        return "unknown"
    
    def _detect_browser(self, user_agent: Optional[str]) -> str:
        """Detect browser from user agent."""
        if not user_agent:
            return "unknown"
        
        ua = user_agent.lower()
        if "chrome" in ua and "edge" not in ua:
            return "chrome"
        if "firefox" in ua:
            return "firefox"
        if "safari" in ua and "chrome" not in ua:
            return "safari"
        if "edge" in ua:
            return "edge"
        if "opera" in ua:
            return "opera"
        return "unknown"


__all__ = ['SessionManager']