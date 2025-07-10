"""
Gmail MCP Server for AWS Lambda using simplified stdio adapter - WITH DEBUG CAPTURE
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
            print(f"MCP Server Debug Output: {stderr}", file=sys.stderr)

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
    print(f"Lambda received event: {json.dumps(event)}", file=sys.stderr)

    # Create temporary stdio MCP server script - ENHANCED DEBUG VERSION
    mcp_server_script = """#!/usr/bin/env python3
import json
import base64
import os
import sys
import logging
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import boto3
from datetime import datetime

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

logger.info("=== MCP Server Starting ===")

try:
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    table = dynamodb.Table(os.environ.get('TOKENS_TABLE_NAME', 'easydoai-user-tokens-dev'))
    logger.info(f"DynamoDB initialized - Table: {os.environ.get('TOKENS_TABLE_NAME', 'easydoai-user-tokens-dev')}")
except Exception as e:
    logger.error(f"Failed to initialize DynamoDB: {e}")
    table = None

def get_user_credentials(user_id):
    if not table:
        logger.error("DynamoDB table not initialized")
        return None

    try:
        logger.info(f"Looking for credentials for user: {user_id}")
        response = table.get_item(Key={'user_id': user_id, 'service': 'gmail'})
        logger.info(f"DynamoDB response status: {'Found' if 'Item' in response else 'Not Found'}")
            
            if 'Item' not in response:
            logger.warning(f"No Gmail credentials found for user {user_id}")
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

        scopes_list = []
        if scope:
            scopes_list = scope.split(' ') if isinstance(scope, str) else scope

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
                
                # Update DynamoDB with new token
                table.update_item(
                    Key={'user_id': user_id, 'service': 'gmail'},
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
            
        logger.info("Credentials ready for Gmail API")
            return credentials
    except Exception as e:
        logger.error(f"Error getting credentials for user {user_id}: {e}")
        return None

def handle_tools_list():
    logger.info("Handling tools/list request")
    return {
        "jsonrpc": "2.0",
        "id": "tools_list",
        "result": {
            "tools": [
                {
                    "name": "get_gmail_messages",
                    "description": "Get Gmail messages for a user",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "query": {"type": "string", "description": "Search query", "default": ""},
                            "max_results": {"type": "integer", "description": "Max results", "default": 10}
                        },
                        "required": ["user_id"]
                    }
                },
                {
                    "name": "send_gmail_message",
                    "description": "Send a Gmail message",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "User ID"},
                            "to": {"type": "string", "description": "Recipient"},
                            "subject": {"type": "string", "description": "Subject"},
                            "body": {"type": "string", "description": "Body"}
                        },
                        "required": ["user_id", "to", "subject", "body"]
                    }
                }
            ]
        }
    }

def handle_tool_call(tool_name, arguments, request_id):
    logger.info(f"Handling tool call: {tool_name}")
    try:
        if tool_name == "get_gmail_messages":
            user_id = arguments.get("user_id")
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 10)

            logger.info(f"Gmail messages request for user: {user_id}")

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
                    "error": {"code": -32603, "message": "User not authenticated for Gmail"}
                }

            logger.info("Credentials obtained, calling Gmail API...")
            try:
                service = build('gmail', 'v1', credentials=credentials)
                logger.info("Gmail service built successfully")

                results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
                messages = results.get('messages', [])
                logger.info(f"Retrieved {len(messages)} messages")
                detailed_messages = []

                for message in messages[:max_results]:
                    msg = service.users().messages().get(userId='me', id=message['id']).execute()

                    headers = msg['payload'].get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

                    detailed_messages.append({
                        'id': message['id'],
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'snippet': msg.get('snippet', '')
                    })

                logger.info(f"Successfully processed {len(detailed_messages)} messages")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "messages": detailed_messages,
                                "total": len(detailed_messages)
                            })
                        }]
                    }
                }

            except Exception as e:
                logger.error(f"Gmail API error: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Gmail API error: {str(e)}"}
                }

        elif tool_name == "send_gmail_message":
            # Similar debug logging for send message...
            user_id = arguments.get("user_id")
            to = arguments.get("to")
            subject = arguments.get("subject")
            body = arguments.get("body")

            logger.info(f"Send Gmail message request for user: {user_id}")

            if not all([user_id, to, subject, body]):
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32602, "message": "user_id, to, subject, and body are required"}
                }

            credentials = get_user_credentials(user_id)
            if not credentials:
                logger.error("Failed to get credentials - authentication required")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": "User not authenticated for Gmail"}
                }

            try:
                service = build('gmail', 'v1', credentials=credentials)

                message_content = f"To: {to}\\nSubject: {subject}\\n\\n{body}"

                raw_message = base64.urlsafe_b64encode(message_content.encode()).decode()
                result = service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

                logger.info(f"Message sent successfully with ID: {result['id']}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({
                                "success": True,
                                "message_id": result['id'],
                                "to": to,
                                "subject": subject
                            })
                        }]
                    }
                }

            except Exception as e:
                logger.error(f"Gmail send error: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Failed to send: {str(e)}"}
                }

        else:
        return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"}
        }

def main():
    try:
        request_line = sys.stdin.read().strip()
        logger.info(f"Received request: {request_line}")
        request = json.loads(request_line)

        method = request.get("method")
        request_id = request.get("id", "unknown")

        logger.info(f"Processing method: {method}")

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

        logger.info(f"Sending response: {json.dumps(response)[:200]}...")
        print(json.dumps(response))

    except Exception as e:
        logger.error(f"Main loop error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": "error",
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
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
