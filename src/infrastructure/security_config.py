"""Security configuration and utilities for the Legal Engine.

Centralizes security best practices including input sanitization,
rate limiting configuration, and secure logging helpers.
"""

import re
import string
from typing import Any, Dict


class SecurityConfig:
    """Security configuration constants and utilities."""
    
    # Rate limiting
    DEFAULT_RATE_LIMIT_RPM = 30
    MAX_RATE_LIMIT_RPM = 1000
    RATE_LIMIT_WINDOW_SECONDS = 60
    
    # Input validation
    MAX_INPUT_LENGTH = 10000
    MAX_FILENAME_LENGTH = 255
    
    # Logging security
    SENSITIVE_FIELD_PATTERNS = [
        r'password', r'secret', r'token', r'key', r'credential',
        r'auth', r'session', r'cookie', r'jwt', r'bearer'
    ]
    
    @staticmethod
    def sanitize_for_logging(value: str, max_length: int = 200) -> str:
        """Sanitize string for safe logging by removing control characters."""
        if not isinstance(value, str):
            value = str(value)
            
        # Remove control characters except newlines and tabs
        sanitized = ''.join(
            char for char in value 
            if char in string.printable and char not in '\x0b\x0c\r'
        )
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "...[truncated]"
            
        return sanitized
    
    @staticmethod
    def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in a dictionary for safe logging."""
        masked = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            is_sensitive = any(
                re.search(pattern, key_lower) 
                for pattern in SecurityConfig.SENSITIVE_FIELD_PATTERNS
            )
            
            if is_sensitive:
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked[key] = "[MASKED]"
            else:
                masked[key] = value
                
        return masked
    
    @staticmethod
    def validate_input_length(value: str, field_name: str) -> str:
        """Validate input length and sanitize for security."""
        if len(value) > SecurityConfig.MAX_INPUT_LENGTH:
            raise ValueError(
                f"{field_name} exceeds maximum length of {SecurityConfig.MAX_INPUT_LENGTH} characters"
            )
        return SecurityConfig.sanitize_for_logging(value)


def create_secure_log_extra(
    user_id: str = None,
    tenant_id: str = None,
    action: str = None,
    **kwargs
) -> Dict[str, Any]:
    """Create secure extra data for structured logging."""
    extra = {}
    
    if user_id:
        extra["user_id"] = SecurityConfig.sanitize_for_logging(user_id)
    if tenant_id:
        extra["tenant_id"] = SecurityConfig.sanitize_for_logging(tenant_id)
    if action:
        extra["action"] = SecurityConfig.sanitize_for_logging(action)
        
    # Add other fields, masking sensitive ones
    for key, value in kwargs.items():
        if isinstance(value, str):
            extra[key] = SecurityConfig.sanitize_for_logging(value)
        else:
            extra[key] = value
            
    return extra