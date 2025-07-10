"""
Gmail-specific API endpoints for frontend integration
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, EmailStr
from services.gmail_lambda_service import gmail_lambda_service
from user_service import user_service
import logging

logger = logging.getLogger(__name__)

# Create router for Gmail endpoints
router = APIRouter(prefix="/gmail", tags=["gmail"])

class GmailMessageRequest(BaseModel):
    user_id: str
    query: str = ""
    max_results: int = 10

class GmailSendRequest(BaseModel):
    user_id: str
    to: EmailStr
    subject: str
    body: str

class GmailAuthResponse(BaseModel):
    authenticated: bool
    authorization_url: str = None
    message: str

@router.get("/status/{user_id}")
async def check_gmail_status(user_id: str):
    """Check if user is authenticated for Gmail"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Try to get a Gmail message (this will trigger auth check)
        result = await gmail_lambda_service.get_gmail_messages(
            user_id=user_id,
            query="",
            max_results=1
        )
        
        if result.get('status') == 'authentication_required':
            return GmailAuthResponse(
                authenticated=False,
                authorization_url=result['authorization_url'],
                message="Gmail authentication required"
            )
        elif result.get('status') == 'success':
            return GmailAuthResponse(
                authenticated=True,
                message="Gmail authenticated and ready"
            )
        else:
            return GmailAuthResponse(
                authenticated=False,
                message=result.get('message', 'Unknown error')
            )
            
    except Exception as e:
        logger.error(f"Error checking Gmail status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check Gmail status")

@router.post("/messages")
async def get_gmail_messages(request: GmailMessageRequest):
    """Get Gmail messages for a user"""
    
    # Verify user exists
    user = user_service.get_user_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        result = await gmail_lambda_service.get_gmail_messages(
            user_id=request.user_id,
            query=request.query,
            max_results=request.max_results
        )
        
        if result.get('status') == 'authentication_required':
            raise HTTPException(
                status_code=401, 
                detail={
                    "message": "Gmail authentication required",
                    "authorization_url": result['authorization_url']
                }
            )
        elif result.get('status') == 'success':
            return result['data']
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Gmail messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Gmail messages")

@router.post("/send")
async def send_gmail_message(request: GmailSendRequest):
    """Send a Gmail message"""
    
    # Verify user exists
    user = user_service.get_user_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        result = await gmail_lambda_service.send_gmail_message(
            user_id=request.user_id,
            to=request.to,
            subject=request.subject,
            body=request.body
        )
        
        if result.get('status') == 'authentication_required':
            raise HTTPException(
                status_code=401, 
                detail={
                    "message": "Gmail authentication required",
                    "authorization_url": result['authorization_url']
                }
            )
        elif result.get('status') == 'success':
            return result['data']
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending Gmail message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send Gmail message")

@router.get("/tools")
async def list_gmail_tools():
    """List available Gmail tools"""
    
    try:
        result = await gmail_lambda_service.list_available_tools()
        
        if result.get('status') == 'success':
            return result['tools']
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
            
    except Exception as e:
        logger.error(f"Error listing Gmail tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Gmail tools") 