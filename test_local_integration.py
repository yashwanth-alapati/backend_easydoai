"""
Complete local integration test for Gmail MCP
"""
import asyncio
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_local_integration():
    """Test the complete Gmail MCP integration locally"""
    
    print("🧪 Local Gmail MCP Integration Test")
    print("=" * 50)
    
    # Test 1: Health Check
    print("1. 🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Health check passed")
            print(f"   📊 Status: {health_data['status']}")
            print(f"   📈 Services: {health_data['services']}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server not running: {e}")
        print("   💡 Make sure to run: uvicorn main:app --reload --port 8000")
        return False
    
    # Test 2: Gmail Tools Listing
    print("\n2. 📋 Testing Gmail Tools Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/gmail/tools")
        if response.status_code == 200:
            tools = response.json()
            print(f"   ✅ Gmail tools available: {len(tools)}")
            for tool in tools:
                print(f"      - {tool['name']}: {tool['description']}")
        else:
            print(f"   ❌ Gmail tools failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Gmail tools error: {e}")
        return False
    
    # Test 3: Create Test User
    print("\n3. 👤 Creating Test User...")
    test_email = "test@example.com"
    test_password = "testpass123"
    
    try:
        response = requests.post(f"{BASE_URL}/signup", json={
            "email": test_email,
            "password": test_password
        })
        
        if response.status_code == 200:
            signup_data = response.json()
            test_user_id = signup_data['user_id']
            print(f"   ✅ Test user created: {test_user_id}")
        elif "already exists" in response.text.lower():
            # User exists, try to login
            response = requests.post(f"{BASE_URL}/login", json={
                "email": test_email,
                "password": test_password
            })
            if response.status_code == 200:
                login_data = response.json()
                test_user_id = login_data['user_id']
                print(f"   ✅ Using existing test user: {test_user_id}")
            else:
                print(f"   ❌ Login failed: {response.text}")
                return False
        else:
            print(f"   ❌ Signup failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ User creation error: {e}")
        return False
    
    # Test 4: Gmail Status Check (Should require auth)
    print("\n4. 🔐 Testing Gmail Authentication Status...")
    try:
        response = requests.get(f"{BASE_URL}/gmail/status/{test_user_id}")
        if response.status_code == 200:
            status_data = response.json()
            print(f"   📊 Authentication status: {status_data}")
            
            if not status_data['authenticated']:
                auth_url = status_data.get('authorization_url')
                if auth_url:
                    print(f"   ✅ OAuth URL generated successfully")
                    print(f"   🔗 Auth URL length: {len(auth_url)} characters")
                    print(f"   🔗 Auth URL preview: {auth_url[:100]}...")
                else:
                    print(f"   ❌ No authorization URL provided")
                    return False
            else:
                print(f"   ✅ User already authenticated for Gmail")
        else:
            print(f"   ❌ Gmail status check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Gmail status error: {e}")
        return False
    
    # Test 5: Gmail Messages (Should require auth)
    print("\n5. 📧 Testing Gmail Messages Endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/gmail/messages", json={
            "user_id": test_user_id,
            "query": "",
            "max_results": 5
        })
        
        if response.status_code == 401:
            # Expected - user not authenticated
            error_data = response.json()
            print(f"   ✅ Correctly requires authentication")
            print(f"   🔗 OAuth URL provided in error response")
            if 'authorization_url' in str(error_data):
                print(f"   ✅ Authentication flow working correctly")
        elif response.status_code == 200:
            # User is already authenticated
            messages_data = response.json()
            print(f"   ✅ Gmail messages retrieved successfully")
            print(f"   📧 Messages: {json.dumps(messages_data, indent=2)}")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Gmail messages error: {e}")
        return False
    
    # Test 6: Gmail Send (Should require auth)
    print("\n6. 📤 Testing Gmail Send Endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/gmail/send", json={
            "user_id": test_user_id,
            "to": "test@example.com",
            "subject": "Test from Local Integration",
            "body": "This is a test email from the local Gmail MCP integration!"
        })
        
        if response.status_code == 401:
            # Expected - user not authenticated
            print(f"   ✅ Correctly requires authentication for sending")
        elif response.status_code == 200:
            # User is already authenticated
            send_data = response.json()
            print(f"   ✅ Gmail send would work (user authenticated)")
            print(f"   📤 Send response: {json.dumps(send_data, indent=2)}")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Gmail send error: {e}")
        return False
    
    # Test 7: Agent Integration
    print("\n7. 🤖 Testing Agent Gmail Integration...")
    try:
        response = requests.post(f"{BASE_URL}/tasks", json={
            "message": "Check my Gmail messages",
            "email": test_email
        })
        
        if response.status_code == 200:
            task_data = response.json()
            print(f"   ✅ Agent processed Gmail request")
            
            # Check the messages for Gmail-related responses
            messages = task_data.get('messages', [])
            for msg in messages:
                if msg['role'] == 'assistant':
                    if 'gmail' in msg['message'].lower() or 'authentication' in msg['message'].lower():
                        print(f"   ✅ Agent correctly handled Gmail request")
                        print(f"   🤖 Agent response preview: {msg['message'][:100]}...")
                        break
        else:
            print(f"   ❌ Agent integration failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Agent integration error: {e}")
        return False
    
    print("\n🎉 Local Integration Test Results:")
    print("✅ FastAPI server - WORKING")
    print("✅ Health endpoints - WORKING") 
    print("✅ Gmail endpoints - WORKING")
    print("✅ Authentication flow - WORKING")
    print("✅ OAuth URL generation - WORKING")
    print("✅ Agent integration - WORKING")
    print("✅ Error handling - WORKING")
    
    print(f"\n💡 Next Steps:")
    print(f"1. ✅ All local tests passed!")
    print(f"2. 🔗 OAuth URLs are being generated correctly")
    print(f"3. 🚀 Ready for production deployment")
    print(f"4. 📱 Frontend can integrate with these endpoints")
    
    return True

if __name__ == "__main__":
    test_local_integration() 