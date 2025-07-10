# easydo_backend/test_full_oauth_flow.py
"""
Test the complete OAuth flow with real Google credentials
"""
import asyncio
import requests
import json
import webbrowser
import time
from urllib.parse import parse_qs, urlparse

BASE_URL = "http://localhost:8000"

class FullOAuthTester:
    def __init__(self):
        self.test_user_id = None
        self.auth_url = None
        self.state = None
        
    async def test_full_oauth_flow(self):
        """Test the complete OAuth flow end-to-end"""
        
        print("🚀 FULL OAUTH FLOW TEST WITH REAL GOOGLE")
        print("=" * 60)
        
        # Step 1: Create/Get Test User
        print("1. 👤 Setting up test user...")
        if not await self.setup_test_user():
            return False
        
        # Step 2: Test Gmail OAuth Flow
        print("\n2. 📧 Testing Gmail OAuth Flow...")
        if not await self.test_service_oauth('gmail'):
            return False
            
        # Step 3: Test Google Calendar OAuth Flow  
        print("\n3. 📅 Testing Google Calendar OAuth Flow...")
        if not await self.test_service_oauth('google_calendar'):
            return False
            
        # Step 4: Test Token Management
        print("\n4. 🔧 Testing Token Management...")
        if not await self.test_token_management():
            return False
            
        print("\n" + "=" * 60)
        print("🎉 FULL OAUTH FLOW TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        return True
    
    async def setup_test_user(self):
        """Create or get existing test user"""
        test_email = "oauth_test@easydoai.com"
        test_password = "testpass123"
        
        try:
            # Try to create user
            response = requests.post(f"{BASE_URL}/signup", json={
                "email": test_email,
                "password": test_password
            })
            
            if response.status_code == 200:
                self.test_user_id = response.json().get('user_id')
                print(f"   ✅ Created new test user: {self.test_user_id}")
            elif "already exists" in response.text:
                # Login existing user
                login_response = requests.post(f"{BASE_URL}/login", json={
                    "email": test_email,
                    "password": test_password
                })
                if login_response.status_code == 200:
                    self.test_user_id = login_response.json().get('user_id')
                    print(f"   ✅ Using existing test user: {self.test_user_id}")
                else:
                    print(f"   ❌ Failed to login: {login_response.status_code}")
                    return False
            else:
                print(f"   ❌ Failed to create user: {response.status_code}")
                return False
                
            return True
            
        except Exception as e:
            print(f"   ❌ User setup failed: {e}")
            return False
    
    async def test_service_oauth(self, service):
        """Test OAuth flow for a specific service"""
        print(f"   🔐 Testing {service} OAuth...")
        
        # Step 1: Check initial authorization status (should be False)
        print(f"   📊 Checking initial {service} authorization...")
        check_response = requests.get(
            f"{BASE_URL}/auth/check-authorization/{service}?user_id={self.test_user_id}"
        )
        
        if check_response.status_code == 200:
            auth_status = check_response.json()
            if not auth_status.get('authorized'):
                print(f"   ✅ {service} not authorized initially (expected)")
            else:
                print(f"   ⚠️  {service} already authorized")
        else:
            print(f"   ❌ Authorization check failed: {check_response.status_code}")
            return False
        
        # Step 2: Initiate OAuth
        print(f"   🚀 Initiating {service} OAuth...")
        auth_response = requests.get(
            f"{BASE_URL}/auth/google/authorize/{service}?user_id={self.test_user_id}"
        )
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            self.auth_url = auth_data['authorization_url']
            self.state = auth_data['state']
            print(f"   ✅ Authorization URL generated")
            print(f"   🔗 URL: {self.auth_url[:100]}...")
            
            # Step 3: Open browser for user authorization
            print(f"\n   🌐 MANUAL STEP REQUIRED:")
            print(f"   📋 I will open your browser to authorize {service}")
            print(f"   ⚠️  IMPORTANT: After authorization, Google will redirect to:")
            print(f"       http://localhost:8000/auth/google/callback?code=...&state=...")
            print(f"   📝 Copy the 'code' parameter from the URL and enter it below")
            
            proceed = input(f"\n   ❓ Ready to authorize {service}? (y/n): ")
            if proceed.lower() != 'y':
                print(f"   ⏭️  Skipping {service} OAuth test")
                return True
            
            # Open browser
            webbrowser.open(self.auth_url)
            
            # Get authorization code from user
            auth_code = input(f"\n   📝 Enter the authorization code from Google: ")
            if not auth_code.strip():
                print(f"   ⏭️  No code provided, skipping {service}")
                return True
            
            # Step 4: Test the callback
            print(f"   🔄 Testing OAuth callback...")
            callback_response = requests.get(
                f"{BASE_URL}/auth/google/callback?code={auth_code}&state={self.state}"
            )
            
            if callback_response.status_code == 200:
                callback_data = callback_response.json()
                print(f"   ✅ OAuth callback successful")
                print(f"   📝 Message: {callback_data.get('message', 'No message')}")
                
                # Step 5: Verify authorization status changed
                print(f"   🔍 Verifying {service} authorization...")
                time.sleep(1)  # Brief wait for token storage
                
                verify_response = requests.get(
                    f"{BASE_URL}/auth/check-authorization/{service}?user_id={self.test_user_id}"
                )
                
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if verify_data.get('authorized'):
                        print(f"   🎉 {service} successfully authorized!")
                        print(f"   ⏰ Expires: {verify_data.get('expires_at', 'Unknown')}")
                        return True
                    else:
                        print(f"   ❌ {service} still not authorized after callback")
                        return False
                else:
                    print(f"   ❌ Authorization verification failed: {verify_response.status_code}")
                    return False
            else:
                print(f"   ❌ OAuth callback failed: {callback_response.status_code}")
                print(f"   📝 Error: {callback_response.text}")
                return False
        else:
            print(f"   ❌ OAuth initiation failed: {auth_response.status_code}")
            return False
    
    async def test_token_management(self):
        """Test token management features"""
        print("   🔧 Testing token management...")
        
        # Test 1: List user services
        services_response = requests.get(f"{BASE_URL}/auth/user/{self.test_user_id}/services")
        
        if services_response.status_code == 200:
            services_data = services_response.json()
            authorized_services = services_data.get('authorized_services', [])
            print(f"   📋 User has {len(authorized_services)} authorized services:")
            
            for service in authorized_services:
                print(f"       - {service['service']} (expires: {service['expires_at']})")
            
            # Test 2: Test revocation (optional)
            if authorized_services:
                test_revoke = input(f"\n   ❓ Test token revocation for one service? (y/n): ")
                if test_revoke.lower() == 'y':
                    service_to_revoke = authorized_services[0]['service']
                    
                    revoke_response = requests.delete(
                        f"{BASE_URL}/auth/revoke/{service_to_revoke}?user_id={self.test_user_id}"
                    )
                    
                    if revoke_response.status_code == 200:
                        print(f"   ✅ Successfully revoked {service_to_revoke}")
                        
                        # Verify revocation
                        check_response = requests.get(
                            f"{BASE_URL}/auth/check-authorization/{service_to_revoke}?user_id={self.test_user_id}"
                        )
                        
                        if check_response.status_code == 200:
                            auth_status = check_response.json()
                            if not auth_status.get('authorized'):
                                print(f"   ✅ {service_to_revoke} authorization successfully revoked")
                            else:
                                print(f"   ❌ {service_to_revoke} still authorized after revocation")
                        
                    else:
                        print(f"   ❌ Revocation failed: {revoke_response.status_code}")
            
            return True
        else:
            print(f"   ❌ Failed to list user services: {services_response.status_code}")
            return False

async def main():
    """Run the full OAuth flow test"""
    tester = FullOAuthTester()
    success = await tester.test_full_oauth_flow()
    
    if success:
        print("\n🚀 READY FOR PHASE 2!")
        print("   Next steps:")
        print("   1. Containerize Gmail MCP Server for Lambda")
        print("   2. Containerize Google Calendar MCP Server for Lambda")
        print("   3. Create Lambda functions with API Gateway")
        print("   4. Test MCP tool execution via Lambda")
    else:
        print("\n❌ OAuth flow test failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())