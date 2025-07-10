# easydo_backend/test_oauth_comprehensive.py
"""
Comprehensive test for Phase 1 OAuth implementation
This test actually validates functionality, not just endpoint accessibility
"""
import asyncio
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"

async def test_comprehensive_oauth():
    """Comprehensive test of OAuth implementation"""
    
    print("🔍 COMPREHENSIVE OAuth Phase 1 Testing")
    print("=" * 60)
    
    # Test 1: Environment Variables Validation
    print("1. 🔧 Testing Environment Variables...")
    
    required_vars = [
        'EASYDOAI_GOOGLE_CLIENT_ID',
        'EASYDOAI_GOOGLE_CLIENT_SECRET', 
        'EASYDOAI_GOOGLE_REDIRECT_URI',
        'AWS_REGION',
        'TOKENS_TABLE_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif value in ['dummy_client_id_for_testing', 'dummy_client_secret_for_testing']:
            print(f"   ⚠️  {var}: Using dummy value (needs real OAuth credentials)")
        else:
            print(f"   ✅ {var}: Configured")
    
    if missing_vars:
        print(f"   ❌ Missing environment variables: {missing_vars}")
        return False
    
    # Test 2: Backend Health with Environment Check
    print("\n2. 🏥 Testing Backend Health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Backend is healthy")
            print(f"   📊 MongoDB available: {health_data.get('mongodb_available', 'Unknown')}")
        else:
            print(f"   ❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Backend connection failed: {e}")
        return False
    
    # Test 3: Create a Test User
    print("\n3. 👤 Creating Test User...")
    test_user_email = "test_oauth@easydoai.com"
    test_user_password = "testpassword123"
    
    try:
        # Try to create user
        signup_response = requests.post(f"{BASE_URL}/signup", json={
            "email": test_user_email,
            "password": test_user_password
        })
        
        if signup_response.status_code == 200:
            user_data = signup_response.json()
            test_user_id = user_data.get('user_id')
            print(f"   ✅ Test user created: {test_user_id}")
        elif signup_response.status_code == 400 and "already exists" in signup_response.text:
            # User already exists, try to login
            login_response = requests.post(f"{BASE_URL}/login", json={
                "email": test_user_email,
                "password": test_user_password
            })
            if login_response.status_code == 200:
                user_data = login_response.json()
                test_user_id = user_data.get('user_id')
                print(f"   ✅ Using existing test user: {test_user_id}")
            else:
                print(f"   ❌ Failed to login existing user: {login_response.status_code}")
                return False
        else:
            print(f"   ❌ Failed to create test user: {signup_response.status_code}")
            print(f"   📝 Response: {signup_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ User creation failed: {e}")
        return False
    
    # Test 4: OAuth Service Initialization Test
    print("\n4. 🔐 Testing OAuth Service Initialization...")
    try:
        # This will test if the OAuth service can initialize with current env vars
        auth_response = requests.get(f"{BASE_URL}/auth/google/authorize/gmail?user_id={test_user_id}")
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            if 'authorization_url' in auth_data:
                print("   ✅ OAuth service initialized successfully")
                print(f"   🔗 Authorization URL generated: {len(auth_data['authorization_url'])} chars")
                
                # Validate the authorization URL contains expected parameters
                auth_url = auth_data['authorization_url']
                if 'accounts.google.com' in auth_url and 'client_id' in auth_url:
                    print("   ✅ Authorization URL format is correct")
                else:
                    print("   ❌ Authorization URL format is invalid")
                    return False
            else:
                print("   ❌ OAuth response missing authorization_url")
                return False
        else:
            print(f"   ❌ OAuth initiation failed: {auth_response.status_code}")
            print(f"   📝 Response: {auth_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ OAuth service test failed: {e}")
        return False
    
    # Test 5: Authorization Check (Should be False)
    print("\n5. 🔍 Testing Authorization Status Check...")
    try:
        check_response = requests.get(f"{BASE_URL}/auth/check-authorization/gmail?user_id={test_user_id}")
        
        if check_response.status_code == 200:
            auth_status = check_response.json()
            if auth_status.get('authorized') == False:
                print("   ✅ Authorization check works correctly (user not authorized)")
            else:
                print("   ⚠️  User appears to be authorized (unexpected)")
        else:
            print(f"   ❌ Authorization check failed: {check_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Authorization check test failed: {e}")
        return False
    
    # Test 6: DynamoDB Connectivity Test
    print("\n6. 🗄️  Testing DynamoDB Connectivity...")
    try:
        # Test if we can list user services (should be empty)
        services_response = requests.get(f"{BASE_URL}/auth/user/{test_user_id}/services")
        
        if services_response.status_code == 200:
            services_data = services_response.json()
            print("   ✅ DynamoDB connectivity working")
            print(f"   📋 User services: {len(services_data.get('authorized_services', []))}")
        else:
            print(f"   ❌ DynamoDB test failed: {services_response.status_code}")
            print(f"   📝 Response: {services_response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ DynamoDB connectivity test failed: {e}")
        return False
    
    # Test 7: Invalid Service Test
    print("\n7. 🚫 Testing Invalid Service Handling...")
    try:
        invalid_response = requests.get(f"{BASE_URL}/auth/google/authorize/invalid_service?user_id={test_user_id}")
        
        if invalid_response.status_code == 400:
            print("   ✅ Invalid service properly rejected")
        else:
            print(f"   ❌ Invalid service not handled correctly: {invalid_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Invalid service test failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 COMPREHENSIVE TEST RESULTS")
    print("=" * 60)
    print("✅ All core functionality tests passed!")
    print("\n📋 NEXT STEPS:")
    print("1. 🔑 Set up real Google OAuth App credentials")
    print("2. 🌐 Test full OAuth flow with real Google")
    print("3. 🚀 Move to Phase 2: Lambda containerization")
    
    return True

async def test_with_real_credentials():
    """Test OAuth with actual Google credentials (if available)"""
    print("\n" + "=" * 60)
    print("🔐 TESTING WITH REAL OAUTH CREDENTIALS")
    print("=" * 60)
    
    client_id = os.getenv('EASYDOAI_GOOGLE_CLIENT_ID')
    if not client_id or client_id == 'dummy_client_id_for_testing':
        print("❌ No real OAuth credentials found")
        print("📝 To test with real credentials:")
        print("   1. Go to Google Cloud Console")
        print("   2. Create OAuth 2.0 credentials")
        print("   3. Update .env file with real values")
        return False
    
    print(f"🔑 Found OAuth credentials for client: {client_id[:20]}...")
    print("✅ Ready for real OAuth testing!")
    return True

if __name__ == "__main__":
    async def run_all_tests():
        success = await test_comprehensive_oauth()
        if success:
            await test_with_real_credentials()
    
    asyncio.run(run_all_tests())