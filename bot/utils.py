import os
from typing import Optional

OWNER_ID = int(os.getenv('OWNER_ID', '1735522859'))

def is_admin(user_id: int) -> bool:
    """Check if user is admin (owner)"""
    return user_id == OWNER_ID

def format_price(price: int) -> str:
    """Format price in MMK"""
    return f"{price:,} MMK"

def format_user_mention(username: str) -> str:
    """Format username with @ prefix"""
    if username and not username.startswith('@'):
        return f"@{username}"
    return username or "Unknown"

def validate_positive_integer(text: str) -> Optional[int]:
    """Validate and return positive integer, None if invalid"""
    try:
        value = int(text)
        return value if value > 0 else None
    except ValueError:
        return None

def format_order_status(status: str) -> str:
    """Format order status with emoji"""
    status_map = {
        'pending': '⏳ Pending',
        'confirmed': '✅ Confirmed',
        'rejected': '❌ Rejected'
    }
    return status_map.get(status, status)
