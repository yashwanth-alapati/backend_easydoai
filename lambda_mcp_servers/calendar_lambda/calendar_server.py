"""
Google Calendar MCP Server for AWS Lambda using simplified stdio adapter - WITH CREATE_EVENT
"""

import os
import sys
import json
import subprocess
import tempfile
from typing import Dict, Any


def simple_stdio_adapter(
    command: list, event: Dict[str, Any], context
) -> Dict[str, Any]:
    """
    Simplified stdio adapter for MCP servers in Lambda
    Based on AWS Labs approach but without external dependency
    """

    try:
        # Start the MCP server process
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
        )

        # Send the MCP request to the server
        request_json = json.dumps(event) + "\n"
        stdout, stderr = process.communicate(
            input=request_json, timeout=25
        )  # Lambda timeout buffer

        # ALWAYS log stderr to CloudWatch for debugging
        if stderr:
            print(f"Calendar MCP Server Debug Output: {stderr}", file=sys.stderr)

        # Parse the response
        if process.returncode == 0:
            try:
                response = json.loads(stdout.strip())
                # Include debug info for troubleshooting
                if stderr and event.get("method") == "tools/call":
                    response["_debug"] = {"stderr": stderr}
                return response
            except json.JSONDecodeError as e:
                return {
                    "jsonrpc": "2.0",
                    "id": event.get("id", "error"),
                    "error": {
                        "code": -32603,
                        "message": f"Invalid JSON response from MCP server: {e}",
                        "data": {"stdout": stdout, "stderr": stderr},
                    },
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": event.get("id", "error"),
                "error": {
                    "code": -32603,
                    "message": f"MCP server process failed with code {process.returncode}",
                    "data": {"stderr": stderr},
                },
            }

    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "jsonrpc": "2.0",
            "id": event.get("id", "error"),
            "error": {"code": -32603, "message": "MCP server process timed out"},
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": event.get("id", "error"),
            "error": {
                "code": -32603,
                "message": f"Failed to execute MCP server: {str(e)}",
            },
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler using simplified stdio adapter
    """

    # Print event for debugging
    print(f"Calendar Lambda received event: {json.dumps(event)}", file=sys.stderr)

    # Create temporary stdio MCP server script - WITH CREATE_EVENT
    mcp_server_script = """#!/usr/bin/env python3
import json
import os
import sys
import logging
from typing import Optional, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import boto3
from datetime import datetime

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

logger.info("=== Calendar MCP Server Starting ===")

try:
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    table = dynamodb.Table(os.environ.get('TOKENS_TABLE_NAME', 'easydoai-user-tokens'))
    logger.info(f"DynamoDB initialized - Table: {os.environ.get('TOKENS_TABLE_NAME', 'easydoai-user-tokens')}")
except Exception as e:
    logger.error(f"Failed to initialize DynamoDB: {e}")
    table = None

def get_user_credentials(user_id):
    if not table:
        logger.error("DynamoDB table not initialized")
        return None

    try:
        logger.info(f"Looking for Calendar credentials for user: {user_id}")
        # Try google_calendar service first, then fallback to gmail
        response = table.get_item(Key={'user_id': user_id, 'service': 'google_calendar'})
        if 'Item' not in response:
            logger.info(f"No google_calendar tokens found, trying gmail tokens for user {user_id}")
            response = table.get_item(Key={'user_id': user_id, 'service': 'gmail'})
        logger.info(f"DynamoDB response status: {'Found' if 'Item' in response else 'Not Found'}")

        if 'Item' not in response:
            logger.warning(f"No Calendar credentials found for user {user_id}")
            return None

        token_data = response['Item']
        logger.info(f"Token data keys: {list(token_data.keys())}")

        # Enhanced token retrieval with better error handling
        def get_value(data, key):
            value = data.get(key)
            if isinstance(value, dict):
                # Handle DynamoDB type descriptors
                if 'S' in value:
                    return value['S']
                elif 'N' in value:
                    return value['N']
                else:
                    return str(value)
            return value

        access_token = get_value(token_data, 'access_token')
        refresh_token = get_value(token_data, 'refresh_token')
        scope = get_value(token_data, 'scope')
        expires_at = get_value(token_data, 'expires_at')

        logger.info(f"Access token length: {len(access_token) if access_token else 0}")
        logger.info(f"Refresh token available: {bool(refresh_token)}")
        logger.info(f"Expires at: {expires_at}")

        if not access_token:
            logger.error(f"No access token found for user {user_id}")
            return None

        # Check if token has calendar scope
        scopes_list = []
        if scope:
            scopes_list = scope.split(' ') if isinstance(scope, str) else scope
            has_calendar_scope = any('calendar' in s for s in scopes_list)
            logger.info(f"Has calendar scope: {has_calendar_scope}")
            if not has_calendar_scope:
                logger.warning(f"Token does not have calendar scope: {scopes_list}")

        # Check if token is expired (basic check)
        if expires_at:
            try:
                from datetime import datetime
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                now = datetime.now(expires_dt.tzinfo) if expires_dt.tzinfo else datetime.utcnow()
                is_expired = now >= expires_dt
                logger.info(f"Token expired check: {is_expired} (expires: {expires_dt}, now: {now})")
                if is_expired:
                    logger.warning(f"Token expired at {expires_at}")
            except Exception as e:
                logger.warning(f"Could not parse expiry time: {e}")

        logger.info(f"Creating credentials with scopes: {scopes_list}")

        client_id = os.environ.get('EASYDOAI_GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('EASYDOAI_GOOGLE_CLIENT_SECRET')

        logger.info(f"Using client_id: {client_id[:20] if client_id else 'MISSING'}...")
        logger.info(f"Using client_secret: {bool(client_secret)}")

            credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes_list
        )

        logger.info("Credentials created successfully")
        logger.info(f"Credentials valid: {credentials.valid}")
        logger.info(f"Credentials expired: {credentials.expired}")

        # Test credentials validity
        if credentials.expired and credentials.refresh_token:
            logger.info("Token expired, attempting refresh...")
            try:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                logger.info("Token refreshed successfully")

                # Update DynamoDB with new token (use the same service we found the token in)
                service_name = 'google_calendar' if 'google_calendar' in str(response) else 'gmail'
                table.update_item(
                    Key={'user_id': user_id, 'service': service_name},
                    UpdateExpression='SET access_token = :token, expires_at = :expires, updated_at = :updated',
                    ExpressionAttributeValues={
                        ':token': credentials.token,
                        ':expires': credentials.expiry.isoformat() if credentials.expiry else None,
                        ':updated': datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                return None

        logger.info("Credentials ready for Calendar API")
            return credentials
    except Exception as e:
        logger.error(f"Error getting credentials for user {user_id}: {e}")
        return None

def handle_tools_list():
    logger.info("Handling tools/list request for Calendar")
    return {
        "jsonrpc": "2.0",
        "id": "tools_list",
        "result": {
            "tools": [
                {
                    "name": "list_calendars",
                    "description": "List all user's calendars",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"}
                        },
                        "required": ["user_id"]
                    }
                },
                {
                    "name": "list_events",
                    "description": "List events from a calendar",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"},
                            "max_results": {"type": "integer", "description": "Max results", "default": 10},
                            "time_min": {"type": "string", "description": "Start time filter (ISO format)"},
                            "time_max": {"type": "string", "description": "End time filter (ISO format)"}
                        },
                        "required": ["user_id"]
                    }
                },
                {
                    "name": "create_event",
                    "description": "Create a new calendar event",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "summary": {"type": "string", "description": "Event title"},
                            "start_time": {"type": "string", "description": "Start time (ISO format)"},
                            "end_time": {"type": "string", "description": "End time (ISO format)"},
                            "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"},
                            "description": {"type": "string", "description": "Event description"},
                            "location": {"type": "string", "description": "Event location"},
                            "attendees": {"type": "array", "items": {"type": "string"}, "description": "Attende emails"}
                        },
                        "required": ["user_id", "summary", "start_time", "end_time"]
                    }
                },
                {
                    "name": "update_event",
                    "description": "Update an existing calendar event",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "event_id": {"type": "string", "description": "Event ID to update"},
                            "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"},
                            "summary": {"type": "string", "description": "New event title"},
                            "start_time": {"type": "string", "description": "New start time (ISO format)"},
                            "end_time": {"type": "string", "description": "New end time (ISO format)"},
                            "description": {"type": "string", "description": "New event description"},
                            "location": {"type": "string", "description": "New event location"}
                        },
                        "required": ["user_id", "event_id"]
                    }
                },
                {
                    "name": "delete_event",
                    "description": "Delete a calendar event",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "event_id": {"type": "string", "description": "Event ID to delete"},
                            "calendar_id": {"type": "string", "description": "Calendar ID", "default": "primary"}
                        },
                        "required": ["user_id", "event_id"]
                    }
                }
            ]
        }
    }

def handle_tool_call(tool_name, arguments, request_id):
    logger.info(f"Handling Calendar tool call: {tool_name}")
    try:
        user_id = arguments.get("user_id")
        if not user_id:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "user_id is required"}
            }

        credentials = get_user_credentials(user_id)
        if not credentials:
            logger.error("Failed to get credentials - authentication required")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": "User not authenticated for Google Calendar"}
            }

        logger.info("Credentials obtained, calling Calendar API...")
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("Calendar service built successfully")

        if tool_name == "list_calendars":
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get("items", [])
            calendar_list = []
    for calendar in calendars:
                calendar_list.append({
                    'id': calendar['id'],
                    'name': calendar['summary'],
                    'access_role': calendar.get('accessRole', 'N/A'),
                    'primary': calendar.get('primary', False)
                })

            logger.info(f"Successfully retrieved {len(calendar_list)} calendars")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "calendars": calendar_list,
                            "total": len(calendar_list)
                        })
                    }]
                }
            }

        elif tool_name == "create_event":
            # Get required parameters
            summary = arguments.get("summary")
            start_time = arguments.get("start_time")
            end_time = arguments.get("end_time")
            calendar_id = arguments.get("calendar_id", "primary")
            # Optional parameters
            description = arguments.get("description")
            location = arguments.get("location")
            attendees = arguments.get("attendees", [])

            # Validate required parameters
            if not all([summary, start_time, end_time]):
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": "summary, start_time, and end_time are required"}
                }

            logger.info(f"Creating event: {summary} from {start_time} to {end_time}")

            # Build event object
    event = {
        "summary": summary,
                "start": {"dateTime": start_time, "timeZone": "UTC"},
                "end": {"dateTime": end_time, "timeZone": "UTC"}
            }

            # Add optional fields
    if description:
        event["description"] = description
    if location:
        event["location"] = location
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]

            logger.info(f"Event object: {json.dumps(event)}")

            # Create the event
            created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

            logger.info(f"Event created successfully with ID: {created_event['id']}")
        return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "success": True,
                            "event_id": created_event['id'],
                            "html_link": created_event.get('htmlLink', ''),
                            "summary": summary,
                            "start_time": start_time,
                            "end_time": end_time,
                            "calendar_id": calendar_id
                        })
                    }]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Calendar tool '{tool_name}' not implemented yet"}
            }

    except Exception as e:
        logger.error(f"Calendar tool execution error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": f"Calendar tool execution failed: {str(e)}"}
        }

def main():
    try:
        request_line = sys.stdin.read().strip()
        logger.info(f"Calendar MCP received request: {request_line}")
        request = json.loads(request_line)

        method = request.get("method")
        request_id = request.get("id", "unknown")

        logger.info(f"Processing Calendar method: {method}")

        if method == "tools/list":
            response = handle_tools_list()
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            response = handle_tool_call(tool_name, arguments, request_id)
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

        logger.info(f"Calendar sending response: {json.dumps(response)[:200]}...")
        print(json.dumps(response))

    except Exception as e:
        logger.error(f"Calendar main loop error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": "error",
            "error": {"code": -32603, "message": f"Internal Calendar error: {str(e)}"}
        }
        print(json.dumps(error_response))

if __name__ == "__main__":
    main()
"""

    # Write script to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(mcp_server_script)
        script_path = f.name

    # Make it executable
    os.chmod(script_path, 0o755)

    # Run the MCP server with our simplified adapter
    command = [sys.executable, script_path]

    return simple_stdio_adapter(command, event, context)
