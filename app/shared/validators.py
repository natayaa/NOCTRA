# app/shared/validator.py
from typing import Optional, Any, Dict, List, Union, Pattern
import re
from datetime import datetime
from uuid import UUID
from email_validator import validate_email, EmailNotValidError

from core.constants import RegexPatterns
from core.exceptions import ValidationError

# ==================== VALIDATOR CLASS ====================

class Validator:
    """Validation utilities for common data types"""
    
    @staticmethod
    def validate_required(
        value: Any,
        field_name: str
    ) -> Any:
        """Validate that value is not None or empty"""
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(
                f"{field_name} is required",
                details={"field": field_name}
            )
        return value
    
    @staticmethod
    def validate_uuid(
        value: str,
        field_name: str = "id"
    ) -> str:
        """Validate UUID format"""
        pattern = RegexPatterns.UUID
        if not re.match(pattern, value):
            raise ValidationError(
                f"Invalid {field_name} format. Must be a valid UUID",
                details={"field": field_name, "value": value}
            )
        return value
    
    @staticmethod
    def validate_email(
        value: str,
        field_name: str = "email"
    ) -> str:
        """Validate email format"""
        try:
            result = validate_email(value)
            return result.email
        except EmailNotValidError as e:
            raise ValidationError(
                f"Invalid {field_name}: {str(e)}",
                details={"field": field_name, "value": value}
            )
    
    @staticmethod
    def validate_phone(
        value: str,
        field_name: str = "phone",
        country_code: Optional[str] = None
    ) -> str:
        """Validate phone number format"""
        # Remove whitespace and special characters
        cleaned = re.sub(r'[\s\-\(\)\.]', '', value)
        
        pattern = RegexPatterns.PHONE
        if country_code == "id":
            pattern = RegexPatterns.PHONE_INDONESIA
        
        if not re.match(pattern, cleaned):
            raise ValidationError(
                f"Invalid {field_name} format",
                details={"field": field_name, "value": value}
            )
        return cleaned
    
    @staticmethod
    def validate_nik(
        value: str,
        field_name: str = "nik"
    ) -> str:
        """Validate Indonesian NIK (ID card number)"""
        cleaned = re.sub(r'[\s\-]', '', value)
        
        if not re.match(RegexPatterns.NIK, cleaned):
            raise ValidationError(
                f"Invalid {field_name} format. Must be 16 digits",
                details={"field": field_name, "value": value}
            )
        return cleaned
    
    @staticmethod
    def validate_npwp(
        value: str,
        field_name: str = "npwp"
    ) -> str:
        """Validate Indonesian NPWP (tax ID)"""
        cleaned = re.sub(r'[\s\-\.]', '', value)
        
        if not re.match(RegexPatterns.NPWP, cleaned):
            raise ValidationError(
                f"Invalid {field_name} format. Must be 15 digits",
                details={"field": field_name, "value": value}
            )
        return cleaned
    
    @staticmethod
    def validate_plate_number(
        value: str,
        field_name: str = "plate_number"
    ) -> str:
        """Validate Indonesian vehicle plate number"""
        cleaned = re.sub(r'\s+', ' ', value.strip().upper())
        
        if not re.match(RegexPatterns.PLATE_NUMBER, cleaned):
            raise ValidationError(
                f"Invalid {field_name} format",
                details={"field": field_name, "value": value}
            )
        return cleaned
    
    @staticmethod
    def validate_password(
        value: str,
        field_name: str = "password",
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True
    ) -> str:
        """Validate password strength"""
        if len(value) < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters",
                details={
                    "field": field_name,
                    "min_length": min_length
                }
            )
        
        if require_uppercase and not any(c.isupper() for c in value):
            raise ValidationError(
                f"{field_name} must contain at least one uppercase letter",
                details={"field": field_name}
            )
        
        if require_lowercase and not any(c.islower() for c in value):
            raise ValidationError(
                f"{field_name} must contain at least one lowercase letter",
                details={"field": field_name}
            )
        
        if require_digit and not any(c.isdigit() for c in value):
            raise ValidationError(
                f"{field_name} must contain at least one digit",
                details={"field": field_name}
            )
        
        if require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value):
            raise ValidationError(
                f"{field_name} must contain at least one special character",
                details={"field": field_name}
            )
        
        return value
    
    @staticmethod
    def validate_url(
        value: str,
        field_name: str = "url"
    ) -> str:
        """Validate URL format"""
        if not re.match(RegexPatterns.URL, value):
            raise ValidationError(
                f"Invalid {field_name} format",
                details={"field": field_name, "value": value}
            )
        return value
    
    @staticmethod
    def validate_date(
        value: str,
        field_name: str = "date",
        format: str = "%Y-%m-%d"
    ) -> datetime:
        """Validate and parse date string"""
        try:
            return datetime.strptime(value, format)
        except ValueError:
            raise ValidationError(
                f"Invalid {field_name} format. Expected {format}",
                details={"field": field_name, "value": value}
            )
    
    @staticmethod
    def validate_length(
        value: str,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None
    ) -> str:
        """Validate string length"""
        length = len(value)
        
        if min_length is not None and length < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters",
                details={
                    "field": field_name,
                    "min_length": min_length,
                    "current_length": length
                }
            )
        
        if max_length is not None and length > max_length:
            raise ValidationError(
                f"{field_name} must be at most {max_length} characters",
                details={
                    "field": field_name,
                    "max_length": max_length,
                    "current_length": length
                }
            )
        
        return value
    
    @staticmethod
    def validate_range(
        value: Union[int, float],
        field_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> Union[int, float]:
        """Validate numeric range"""
        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} must be at least {min_value}",
                details={
                    "field": field_name,
                    "min_value": min_value,
                    "current_value": value
                }
            )
        
        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} must be at most {max_value}",
                details={
                    "field": field_name,
                    "max_value": max_value,
                    "current_value": value
                }
            )
        
        return value
    
    @staticmethod
    def validate_enum(
        value: str,
        enum_class: type,
        field_name: str = "value"
    ) -> str:
        """Validate value is in enum"""
        valid_values = [item.value for item in enum_class]
        if value not in valid_values:
            raise ValidationError(
                f"Invalid {field_name}. Must be one of: {', '.join(valid_values)}",
                details={
                    "field": field_name,
                    "value": value,
                    "valid_values": valid_values
                }
            )
        return value
    
    @staticmethod
    def validate_slug(
        value: str,
        field_name: str = "slug"
    ) -> str:
        """Validate slug format"""
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', value):
            raise ValidationError(
                f"Invalid {field_name} format. Use lowercase letters, numbers, and hyphens only",
                details={"field": field_name, "value": value}
            )
        return value
    
    @staticmethod
    def validate_currency(
        value: Union[int, float, str],
        field_name: str = "amount"
    ) -> float:
        """Validate currency value"""
        if isinstance(value, str):
            # Remove currency symbols and thousand separators
            cleaned = re.sub(r'[^\d.,\-]', '', value)
            cleaned = cleaned.replace(',', '.')
            try:
                value = float(cleaned)
            except ValueError:
                raise ValidationError(
                    f"Invalid {field_name} format",
                    details={"field": field_name, "value": value}
                )
        
        if value < 0:
            raise ValidationError(
                f"{field_name} cannot be negative",
                details={"field": field_name, "value": value}
            )
        
        # Round to 2 decimal places
        return round(value, 2)

# ==================== VALIDATION SCHEMA MIXIN ====================

class ValidationMixin:
    """Mixin for validation in Pydantic models"""
    
    def validate_required_fields(self, fields: List[str]) -> None:
        """Validate that required fields are present"""
        for field in fields:
            value = getattr(self, field, None)
            Validator.validate_required(value, field)
    
    def validate_uuid_fields(self, fields: Dict[str, str]) -> None:
        """Validate UUID fields"""
        for field, value in fields.items():
            if value:
                Validator.validate_uuid(value, field)
    
    def validate_email_fields(self, fields: Dict[str, str]) -> None:
        """Validate email fields"""
        for field, value in fields.items():
            if value:
                Validator.validate_email(value, field)
    
    def validate_phone_fields(self, fields: Dict[str, str]) -> None:
        """Validate phone fields"""
        for field, value in fields.items():
            if value:
                Validator.validate_phone(value, field)

# ==================== EXPORTS ====================

__all__ = [
    'Validator',
    'ValidationMixin',
]