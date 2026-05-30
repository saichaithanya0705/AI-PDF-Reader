"""
Authentication Middleware for Supabase JWT Verification
"""

import os
import requests
import json
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from typing import Optional
import logging

from .auth_config import auth_bypass_enabled, development_user

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)
security_optional = HTTPBearer(auto_error=False)

# Env vars
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_API_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

JWKS_CACHE = None

def get_supabase_jwks():
    global JWKS_CACHE
    if JWKS_CACHE:
        return JWKS_CACHE
    
    if not SUPABASE_URL:
        print("❌ SUPABASE_URL not set, cannot fetch JWKS")
        return None

    # Try common JWKS paths
    paths = ["/.well-known/jwks.json", "/auth/v1/.well-known/jwks.json"]
    headers = {}
    if SUPABASE_API_KEY:
        headers["apikey"] = SUPABASE_API_KEY
    
    for path in paths:
        try:
            url = f"{SUPABASE_URL}{path}"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                JWKS_CACHE = r.json()
                print("✅ JWKS fetched successfully")
                return JWKS_CACHE
        except Exception as e:
            print(f"DEBUG: Failed to fetch JWKS from {path}: {e}")
            
    print("❌ Failed to fetch JWKS from any endpoint")
    return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> dict:
    logger.debug("get_current_user called")
    if auth_bypass_enabled():
        logger.info("Using development auth bypass user")
        return development_user()

    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        token = credentials.credentials
        
        # Determine Algorithm
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg")
            logger.debug("Token algorithm: %s", alg)
        except JWTError:
            alg = "HS256"

        jwt_key = SUPABASE_JWT_SECRET
        algorithms = ["HS256"]
        
        if alg == "ES256":
            algorithms = ["ES256"]
            jwks_data = get_supabase_jwks()
            if not jwks_data:
                raise Exception("JWKS unavailable for ES256 verification")
                
            kid = header.get("kid")
            if not kid:
                raise Exception("Token missing 'kid' header")
                
            found_key = None
            for k in jwks_data.get("keys", []):
                if k.get("kid") == kid:
                    found_key = k
                    break
            
            if not found_key:
                raise Exception(f"Key {kid} not found in JWKS")
                
            # Construct public key
            jwt_key = jwk.construct(found_key)

        # Decode
        payload = jwt.decode(
            token,
            jwt_key,
            algorithms=algorithms,
            options={"verify_aud": False}
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
            
        return {
            "sub": user_id,
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
            "authenticated": True,
            "auth_bypassed": False,
        }
    except HTTPException:
        raise
    except JWTError as e:
        print(f"❌ JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional)) -> Optional[dict]:
    """
    Optional authentication - returns None if no token provided
    """
    logger.debug("get_optional_user called; credentials present=%s", bool(credentials))
    if auth_bypass_enabled():
        return development_user()

    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
