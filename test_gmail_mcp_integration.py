"""
Test Gmail MCP Lambda integration with OAuth flow
"""
import asyncio
import requests
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from services.gmail_lambda_service import gmail_lambda_service

async def test_gmail_integration():
    """Test the complete Gmail MCP integration"""
    
    print("🧪 Testing Gmail MCP Lambda Integration")
    print("=" * 50)
    
    # Check environment variables
    client_id = os.getenv('EASYDOAI_GOOGLE_CLIENT_ID')
    print(f"🔑 OAuth Client ID: {client_id[:20]}..." if client_id else "❌ No OAuth Client ID found")
    
    # Test user ID (you can create a test user or use existing)
    test_user_id = "test_user_123"
    
    # Test 1: List available tools
    print("\n1. 📋 Listing available Gmail tools...")
    tools_result = await gmail_lambda_service.list_available_tools()
    print(f"   Result: {tools_result}")
    
    # Test 2: Try to get messages (should trigger auth flow)
    print("\n2. 📧 Attempting to get Gmail messages...")
    messages_result = await gmail_lambda_service.get_gmail_messages(
        user_id=test_user_id,
        query="",
        max_results=5
    )
    print(f"   Result: {messages_result}")
    
    # If authentication required, show the OAuth URL
    if messages_result.get('status') == 'authentication_required':
        print(f"\n🔐 Authentication required!")
        print(f"📱 Visit this URL to authenticate:")
        print(f"   {messages_result['authorization_url']}")
        print(f"\n💡 After authentication, run this test again to see it work!")
    
    # Test 3: Try to send message (should also trigger auth if not authenticated)
    print("\n3. 📤 Attempting to send Gmail message...")
    send_result = await gmail_lambda_service.send_gmail_message(
        user_id=test_user_id,
        to="test@example.com",
        subject="Test from EasyDoAI",
        body="This is a test message from the Gmail MCP integration!"
    )
    print(f"   Result: {send_result}")

if __name__ == "__main__":
    asyncio.run(test_gmail_integration()) 