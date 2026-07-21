# core/validators.py
import re
from datetime import date, datetime
from typing import Optional
from decimal import Decimal


def validate_phone_number(phone: str) -> bool:
    """Validate Indonesian phone number."""
    pattern = r'^(\+62|62|08)\d{8,13}$'
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """Validate email address."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_license_plate(plate: str) -> bool:
    """Validate Indonesian license plate."""
    pattern = r'^[A-Z]{1,2}\s?\d{1,4}\s?[A-Z]{1,3}$'
    return bool(re.match(pattern, plate))


def validate_year(year: int, min_year: int = 1950, max_year: Optional[int] = None) -> bool:
    """Validate year."""
    if max_year is None:
        max_year = datetime.now().year + 1
    return min_year <= year <= max_year


def validate_decimal(value: Decimal, min_value: Optional[Decimal] = None, max_value: Optional[Decimal] = None) -> bool:
    """Validate decimal value."""
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def validate_date_range(start_date: date, end_date: date) -> bool:
    """Validate date range."""
    return start_date <= end_date


def sanitize_string(value: str) -> str:
    """Sanitize string input."""
    # Remove leading/trailing whitespace
    value = value.strip()
    # Remove multiple spaces
    value = re.sub(r'\s+', ' ', value)
    return value
