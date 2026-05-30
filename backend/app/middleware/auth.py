"""
Authentication middleware for validating Supabase JWT tokens
"""
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from typing import Optional
from functools import lru_cache

from ..auth_config import auth_bypass_enabled, development_user

# JWT configuration
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
JWT_ALGORITHM = "HS256"

# Security scheme
security = HTTPBearer()


class AuthError(Exception):
    """Custom exception for authentication errors"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code


def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validate Supabase JWT token and return user_id
    
    Args:
        credentials: HTTP Authorization header with Bearer token
        
    Returns:
        str: User ID (sub claim from JWT)
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if auth_bypass_enabled():
        return str(development_user()["sub"])

    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured. Missing SUPABASE_JWT_SECRET.",
        )
    
    token = credentials.credentials
    
    try:
        # Decode/Parse Secret (Support for HS256 String or ES256 JWK Dict)
        import json
        jwt_secret = SUPABASE_JWT_SECRET
        jwt_algorithms = [JWT_ALGORITHM]
        
        if jwt_secret and jwt_secret.strip().startswith("{"):
            try:
                jwt_secret = json.loads(jwt_secret)
                jwt_algorithms = ["ES256"]
            except json.JSONDecodeError:
                print("SUPABASE_JWT_SECRET started with { but wasn't valid JSON. Falling back to string/HS256.")

        # Decode and validate JWT
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=jwt_algorithms,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,  # Supabase doesn't always set aud
            }
        )
        
        # Extract user ID from 'sub' claim
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        
        # Optional: Extract additional user info
        email = payload.get("email")
        role = payload.get("role", "authenticated")
        
        print(f"✅ Authenticated user: {user_id} ({email})")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
        )
    except jwt.JWTClaimsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {str(e)}",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate token: {str(e)}",
        )
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


async def get_current_user(user_id: str = Depends(verify_jwt_token)) -> dict:
    """
    Get current user information from validated JWT
    
    Args:
        user_id: Validated user ID from JWT
        
    Returns:
        dict: User information
    """
    if auth_bypass_enabled():
        return development_user()

    return {
        "sub": user_id,
        "user_id": user_id,
        "authenticated": True,
        "auth_bypassed": False,
    }


async def verify_admin_user(user_id: str = Depends(verify_jwt_token)) -> str:
    """
    Verify user has admin privileges
    
    Args:
        user_id: Validated user ID from JWT
        
    Returns:
        str: User ID if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    # TODO: Implement admin role check
    # For now, you can maintain a list of admin user IDs
    ADMIN_USERS = os.getenv("ADMIN_USER_IDS", "").split(",")
    
    if user_id not in ADMIN_USERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return user_id


class OptionalAuth:
    """Optional authentication - doesn't fail if no token provided"""
    
    async def __call__(self, request: Request) -> Optional[str]:
        """
        Try to extract and validate JWT, but don't fail if missing
        
        Returns:
            Optional[str]: User ID if authenticated, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        
        if auth_bypass_enabled():
            return str(development_user()["sub"])

        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            return payload.get("sub")
        except:
            return None


optional_auth = OptionalAuth()


def require_auth_for_production():
    """
    Helper to conditionally require auth based on environment
    Useful during development/testing
    """
    env = os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "production"
    if env.lower() == "production":
        return Depends(verify_jwt_token)
    return None


# Example usage in routes:
"""
from .middleware.auth import verify_jwt_token, get_current_user, verify_admin_user

# Require authentication
@app.post("/api/upload")
async def upload_document(
    file: UploadFile,
    user_id: str = Depends(verify_jwt_token)
):
    # user_id is validated
    pass

# Get full user info
@app.get("/api/profile")
async def get_profile(
    user: dict = Depends(get_current_user)
):
    return user

# Admin only
@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_id: str = Depends(verify_admin_user)
):
    pass

# Optional auth (public endpoint but personalized if logged in)
@app.get("/api/documents/public")
async def get_public_documents(
    user_id: Optional[str] = Depends(optional_auth)
):
    if user_id:
        # Personalized results
        pass
    else:
        # Public results
        pass
"""
