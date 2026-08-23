"""
Authentication and Authorization dependencies for LaporKita AI Service.
Enforces internal service-to-service API key authentication on protected /v1/* endpoints.
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.core.logging import logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_internal_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    Verify internal API Key for service-to-service communication.
    Accepts key via 'X-API-Key' header or 'Authorization: Bearer <key>'.
    
    Rules:
    - If INTERNAL_API_KEY is configured:
      - Missing key -> HTTP 401 Unauthorized
      - Invalid key -> HTTP 403 Forbidden
    - If INTERNAL_API_KEY is empty string (dev mode without auth):
      - Bypasses check with a warning log
    """
    expected_key = settings.INTERNAL_API_KEY

    # If no internal key is set in configuration, allow in development mode
    if not expected_key:
        return "dev-unprotected"

    # Extract provided key
    provided_key = x_api_key
    if not provided_key and authorization:
        if authorization.startswith("Bearer "):
            provided_key = authorization.split(" ", 1)[1]
        else:
            provided_key = authorization

    if not provided_key:
        logger.warning("Unauthorized access attempt: X-API-Key header is missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi gagal: Header 'X-API-Key' atau 'Authorization: Bearer <key>' wajib disertakan.",
        )

    if provided_key != expected_key:
        logger.warning("Forbidden access attempt: invalid X-API-Key provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: API Key yang diberikan tidak valid.",
        )

    return provided_key
