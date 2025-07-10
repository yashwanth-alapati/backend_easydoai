from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import logging
from services.calendar_lambda_service import calendar_lambda_service
from user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])


# Request/Response Models
class CreateEventRequest(BaseModel):
    summary: str
    start_time: str  # ISO format
    end_time: str  # ISO format
    calendar_id: Optional[str] = "primary"
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


class UpdateEventRequest(BaseModel):
    event_id: str
    calendar_id: Optional[str] = "primary"
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class DeleteEventRequest(BaseModel):
    event_id: str
    calendar_id: Optional[str] = "primary"


class CalendarResponse(BaseModel):
    status: str
    data: Optional[dict] = None
    message: Optional[str] = None
    authorization_url: Optional[str] = None


# Endpoints

@router.get("/status")
async def calendar_status():
    """Check Calendar service status"""
    return {"status": "Calendar MCP Lambda service is running"}


@router.get("/calendars")
async def get_calendars(
    user_id: str = Query(..., description="User ID to get calendars for")
):
    """Get all calendars for a user"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = await calendar_lambda_service.list_calendars(user_id)
        
        if result["status"] == "authentication_required":
            return CalendarResponse(
                status="authentication_required",
                message=result["message"],
                authorization_url=result["authorization_url"]
            )
        elif result["status"] == "success":
            return CalendarResponse(
                status="success",
                data=result["data"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error getting calendars: {e}")
        raise HTTPException(status_code=500, detail="Failed to get calendars")


@router.get("/events")
async def get_events(
    user_id: str = Query(..., description="User ID"),
    calendar_id: str = Query("primary", description="Calendar ID"),
    max_results: int = Query(10, description="Maximum number of events to return"),
    time_min: Optional[str] = Query(None, description="Start time filter (ISO format)"),
    time_max: Optional[str] = Query(None, description="End time filter (ISO format)")
):
    """Get events from a calendar"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = await calendar_lambda_service.list_events(
            user_id=user_id,
            calendar_id=calendar_id,
            max_results=max_results,
            time_min=time_min,
            time_max=time_max
        )
        
        if result["status"] == "authentication_required":
            return CalendarResponse(
                status="authentication_required",
                message=result["message"],
                authorization_url=result["authorization_url"]
            )
        elif result["status"] == "success":
            return CalendarResponse(
                status="success",
                data=result["data"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get events")


@router.post("/events")
async def create_event(
    request: CreateEventRequest,
    user_id: str = Query(..., description="User ID")
):
    """Create a new calendar event"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = await calendar_lambda_service.create_event(
            user_id=user_id,
            summary=request.summary,
            start_time=request.start_time,
            end_time=request.end_time,
            calendar_id=request.calendar_id,
            description=request.description,
            location=request.location,
            attendees=request.attendees
        )
        
        if result["status"] == "authentication_required":
            return CalendarResponse(
                status="authentication_required",
                message=result["message"],
                authorization_url=result["authorization_url"]
            )
        elif result["status"] == "success":
            return CalendarResponse(
                status="success",
                data=result["data"],
                message="Event created successfully"
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail="Failed to create event")


@router.put("/events")
async def update_event(
    request: UpdateEventRequest,
    user_id: str = Query(..., description="User ID")
):
    """Update an existing calendar event"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = await calendar_lambda_service.update_event(
            user_id=user_id,
            event_id=request.event_id,
            calendar_id=request.calendar_id,
            summary=request.summary,
            start_time=request.start_time,
            end_time=request.end_time,
            description=request.description,
            location=request.location
        )
        
        if result["status"] == "authentication_required":
            return CalendarResponse(
                status="authentication_required",
                message=result["message"],
                authorization_url=result["authorization_url"]
            )
        elif result["status"] == "success":
            return CalendarResponse(
                status="success",
                data=result["data"],
                message="Event updated successfully"
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail="Failed to update event")


@router.delete("/events")
async def delete_event(
    request: DeleteEventRequest,
    user_id: str = Query(..., description="User ID")
):
    """Delete a calendar event"""
    
    # Verify user exists
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = await calendar_lambda_service.delete_event(
            user_id=user_id,
            event_id=request.event_id,
            calendar_id=request.calendar_id
        )
        
        if result["status"] == "authentication_required":
            return CalendarResponse(
                status="authentication_required",
                message=result["message"],
                authorization_url=result["authorization_url"]
            )
        elif result["status"] == "success":
            return CalendarResponse(
                status="success",
                data=result["data"],
                message="Event deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete event")


@router.get("/tools")
async def get_available_tools():
    """Get list of available Calendar tools"""
    try:
        result = await calendar_lambda_service.list_available_tools()
        
        if result["status"] == "success":
            return CalendarResponse(
                status="success",
                data={"tools": result["tools"]}
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error getting Calendar tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Calendar tools") 