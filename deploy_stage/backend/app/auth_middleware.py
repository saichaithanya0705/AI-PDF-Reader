"""
Authentication Middleware for Supabase JWT Verification
"""

import os
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Supabase JWT secret from environment
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verify JWT token and extract user information
    """
    try:
        token = credentials.credentials
        
        # Decode JWT token
        # For Supabase, we use the JWT secret from the project settings
        if not SUPABASE_JWT_SECRET:
            # In development, we can skip verification if no secret is set
            logger.warning("⚠️ SUPABASE_JWT_SECRET not set, skipping JWT verification")
            # Return a mock user for development
            return {"sub": "dev-user-id", "email": "dev@example.com"}
        
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Supabase doesn't use aud claim
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        return {
            "sub": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated")
        }
        
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(lambda: None)) -> Optional[dict]:
    """
    Optional authentication - returns None if no token provided
    """
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
