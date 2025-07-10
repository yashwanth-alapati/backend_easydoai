# easydo_backend/auth_endpoints.py
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel
from services.google_oauth import oauth_service
from aws_services.dynamodb_config import token_storage
from user_service import user_service
import logging

logger = logging.getLogger(__name__)

# Create router for authentication endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])

class AuthStatusResponse(BaseModel):
    authorized: bool
    service: str
    user_id: str
    expires_at: str = None
    scope: str = None

class AuthInitiateResponse(BaseModel):
    authorization_url: str
    state: str
    service: str

class AuthCallbackResponse(BaseModel):
    status: str
    message: str
    user_id: str = None
    service: str = None

@router.get("/google/authorize/{service}")
async def initiate_google_oauth(
    service: str,
    user_id: str = Query(..., description="User ID requesting authorization")
):
    """Initiate Google OAuth2 flow for Gmail or Calendar"""
    
    # Validate service
    if service not in ['gmail', 'google_calendar']:
        raise HTTPException(
            status_code=400, 
            detail="Invalid service. Must be 'gmail' or 'google_calendar'"
        )
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Generate authorization URL
        auth_data = oauth_service.get_authorization_url(service, user_id)
        
        logger.info(f"Generated OAuth URL for user {user_id}, service {service}")
        
        return AuthInitiateResponse(
            authorization_url=auth_data["authorization_url"],
            state=auth_data["state"],
            service=service
        )
        
    except ValueError as e:
        logger.error(f"OAuth initiation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error initiating OAuth: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth")

@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for security"),
    error: str = Query(None, description="Error from OAuth provider")
):
    """Handle Google OAuth2 callback"""
    
    # Check for OAuth errors
    if error:
        logger.error(f"OAuth error: {error}")
        raise HTTPException(
            status_code=400, 
            detail=f"OAuth error: {error}"
        )
    
    try:
        # Exchange code for tokens
        result = oauth_service.exchange_code_for_tokens(code, state)
        
        # Store tokens in DynamoDB
        success = token_storage.store_tokens(
            result['user_id'],
            result['service'],
            result['tokens']
        )
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to store authentication tokens"
            )
        
        logger.info(f"Successfully stored tokens for user {result['user_id']}, service {result['service']}")
        
        return AuthCallbackResponse(
            status="success",
            message=f"Successfully authorized {result['service']} for user {result['user_id']}",
            user_id=result['user_id'],
            service=result['service']
        )
        
    except ValueError as e:
        logger.error(f"OAuth callback validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="OAuth callback failed")

@router.get("/check-authorization/{service}")
async def check_authorization(
    service: str,
    user_id: str = Query(..., description="User ID to check authorization for")
):
    """Check if user has valid tokens for a service"""
    
    # Validate service
    if service not in ['gmail', 'google_calendar']:
        raise HTTPException(
            status_code=400, 
            detail="Invalid service. Must be 'gmail' or 'google_calendar'"
        )
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for valid tokens
    tokens = token_storage.get_tokens(user_id, service)
    
    if tokens:
        return AuthStatusResponse(
            authorized=True,
            service=service,
            user_id=user_id,
            expires_at=tokens.get('expires_at'),
            scope=tokens.get('scope')
        )
    else:
        return AuthStatusResponse(
            authorized=False,
            service=service,
            user_id=user_id
        )

@router.get("/user/{user_id}/services")
async def list_user_services(user_id: str):
    """List all services a user has authorized"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all services for user
    services = token_storage.list_user_services(user_id)
    
    return {
        "user_id": user_id,
        "authorized_services": services
    }

@router.delete("/revoke/{service}")
async def revoke_authorization(
    service: str,
    user_id: str = Query(..., description="User ID to revoke authorization for")
):
    """Revoke authorization for a service"""
    
    # Validate service
    if service not in ['gmail', 'google_calendar']:
        raise HTTPException(
            status_code=400, 
            detail="Invalid service. Must be 'gmail' or 'google_calendar'"
        )
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get tokens before revoking
    tokens = token_storage.get_tokens(user_id, service)
    
    if tokens:
        # Revoke token with Google
        if 'access_token' in tokens:
            oauth_service.revoke_token(tokens['access_token'])
        
        # Delete from our storage
        success = token_storage.delete_tokens(user_id, service)
        
        if success:
            return {
                "status": "success",
                "message": f"Successfully revoked {service} authorization for user {user_id}"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to revoke authorization"
            )
    else:
        raise HTTPException(
            status_code=404, 
            detail=f"No authorization found for {service}"
        )