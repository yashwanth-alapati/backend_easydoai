# easydo_backend/lambda_mcp_servers/calendar_lambda/calendar_server.py
"""
Google Calendar MCP Server for AWS Lambda
Transforms the stdio Calendar MCP server to HTTP using FastMCP
"""
import os
import json
import asyncio
from typing import Dict, Any, List
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# DynamoDB client for token retrieval
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
table = dynamodb.Table(os.getenv('TOKENS_TABLE_NAME', 'easydoai-user-tokens'))

class CalendarTokenManager:
    """Manages Calendar tokens from DynamoDB"""
    
    @staticmethod
    async def get_user_token(user_id: str) -> Credentials:
        """Retrieve user's Calendar token from DynamoDB"""
        try:
            response = table.get_item(
                Key={'user_id': user_id, 'service': 'gmail'}  # Using same token since we requested calendar scope
            )
            
            if 'Item' not in response:
                raise ValueError(f"No Calendar tokens found for user {user_id}")
            
            token_data = response['Item']
            
            credentials = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=os.getenv('EASYDOAI_GOOGLE_CLIENT_ID'),
                client_secret=os.getenv('EASYDOAI_GOOGLE_CLIENT_SECRET'),
                scopes=token_data.get('scope', '').split(' ')
            )
            
            # Refresh token if expired
            if credentials.expired:
                credentials.refresh(Request())
                
                # Update token in DynamoDB
                table.update_item(
                    Key={'user_id': user_id, 'service': 'gmail'},
                    UpdateExpression='SET access_token = :access_token, expires_at = :expires_at',
                    ExpressionAttributeValues={
                        ':access_token': credentials.token,
                        ':expires_at': credentials.expiry.isoformat() if credentials.expiry else None
                    }
                )
            
            return credentials
            
        except ClientError as e:
            logger.error(f"DynamoDB error: {e}")
            raise ValueError(f"Failed to retrieve tokens for user {user_id}")

# Create FastMCP server
mcp = FastMCP(name="calendar-mcp-lambda", version="1.0.0")

@mcp.tool()
async def list_calendars(user_id: str) -> str:
    """List all user's calendars"""
    
    credentials = await CalendarTokenManager.get_user_token(user_id)
    service = build('calendar', 'v3', credentials=credentials)
    
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get('items', [])
    
    result = f"Found {len(calendars)} calendars:\n\n"
    for calendar in calendars:
        result += f"ID: {calendar['id']}\n"
        result += f"Name: {calendar['summary']}\n"
        result += f"Access Role: {calendar.get('accessRole', 'N/A')}\n"
        result += f"Primary: {calendar.get('primary', False)}\n\n"
    
    return result

@mcp.tool()
async def list_events(
    user_id: str,
    calendar_id: str = 'primary',
    max_results: int = 10,
    time_min: str = None,
    time_max: str = None
) -> str:
    """List events from a calendar"""
    
    credentials = await CalendarTokenManager.get_user_token(user_id)
    service = build('calendar', 'v3', credentials=credentials)
    
    # Default to today if no time range specified
    if not time_min:
        time_min = datetime.utcnow().isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    if not events:
        return 'No upcoming events found.'
    
    result = f"Found {len(events)} events:\n\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        result += f"Event: {event['summary']}\n"
        result += f"Start: {start}\n"
        result += f"ID: {event['id']}\n"
        if 'description' in event:
            result += f"Description: {event['description']}\n"
        result += "\n"
    
    return result

@mcp.tool()
async def create_event(
    user_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = 'primary',
    description: str = None,
    location: str = None,
    attendees: List[str] = None
) -> str:
    """Create a new calendar event"""
    
    credentials = await CalendarTokenManager.get_user_token(user_id)
    service = build('calendar', 'v3', credentials=credentials)
    
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
    }
    
    if description:
        event['description'] = description
    if location:
        event['location'] = location
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
    
    return f"Event created successfully. ID: {created_event['id']}\nLink: {created_event.get('htmlLink', 'N/A')}"

@mcp.tool()
async def update_event(
    user_id: str,
    event_id: str,
    calendar_id: str = 'primary',
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    location: str = None
) -> str:
    """Update an existing calendar event"""
    
    credentials = await CalendarTokenManager.get_user_token(user_id)
    service = build('calendar', 'v3', credentials=credentials)
    
    # Get current event
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    
    # Update fields if provided
    if summary:
        event['summary'] = summary
    if start_time:
        event['start']['dateTime'] = start_time
    if end_time:
        event['end']['dateTime'] = end_time
    if description:
        event['description'] = description
    if location:
        event['location'] = location
    
    updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
    
    return f"Event updated successfully. ID: {updated_event['id']}"

@mcp.tool()
async def delete_event(user_id: str, event_id: str, calendar_id: str = 'primary') -> str:
    """Delete a calendar event"""
    
    credentials = await CalendarTokenManager.get_user_token(user_id)
    service = build('calendar', 'v3', credentials=credentials)
    
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    
    return f"Event {event_id} deleted successfully"

# Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler for Calendar MCP server"""
    
    # Extract HTTP method and body
    http_method = event.get('httpMethod', 'POST')
    body = event.get('body', '{}')
    
    if isinstance(body, str):
        body = json.loads(body)
    
    # Handle MCP request
    try:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'tools': [
                    'list_calendars',
                    'list_events', 
                    'create_event',
                    'update_event',
                    'delete_event'
                ]
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

if __name__ == "__main__":
    # For local testing
    mcp.run(transport="http", port=8002)