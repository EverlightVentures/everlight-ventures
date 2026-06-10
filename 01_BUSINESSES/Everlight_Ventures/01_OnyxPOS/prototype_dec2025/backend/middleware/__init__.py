"""
Middleware package for OnyxPOS
"""
from .subscription_guard import check_subscription_access

__all__ = ['check_subscription_access']
