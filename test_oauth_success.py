# easydo_backend/verify_oauth_success.py
"""
Verify that OAuth flow completed successfully
"""
import requests

BASE_URL = "http://localhost:8000"
USER_ID = "686e4455507bbb74a1e2dc6e"  # From your successful authorization


def verify_oauth_success():
    print("🔍 VERIFYING OAUTH SUCCESS")
    print("=" * 40)

    # Check if user is now authorized for Gmail
    print("1. 📧 Checking Gmail authorization...")
    gmail_response = requests.get(
        f"{BASE_URL}/auth/check-authorization/gmail?user_id={USER_ID}"
    )

    if gmail_response.status_code == 200:
        gmail_data = gmail_response.json()
        if gmail_data.get("authorized"):
            print("   ✅ Gmail successfully authorized!")
            print(f"   ⏰ Expires: {gmail_data.get('expires_at')}")
            print(f"   🔐 Scope: {gmail_data.get('scope', 'Not specified')}")
        else:
            print("   ❌ Gmail not authorized")
            return False
    else:
        print(f"   ❌ Failed to check Gmail auth: {gmail_response.status_code}")
        return False

    # Check user's authorized services
    print("\n2. 📋 Checking all authorized services...")
    services_response = requests.get(f"{BASE_URL}/auth/user/{USER_ID}/services")

    if services_response.status_code == 200:
        services_data = services_response.json()
        authorized_services = services_data.get("authorized_services", [])

        print(f"   📊 Total authorized services: {len(authorized_services)}")
        for service in authorized_services:
            print(f"   ✅ {service['service']}")
            print(f"      ⏰ Expires: {service['expires_at']}")
            print(f"      🔐 Scope: {service.get('scope', 'Not specified')}")
    else:
        print(f"   ❌ Failed to list services: {services_response.status_code}")
        return False

    print("\n🎉 OAuth flow verification completed successfully!")
    return True


if __name__ == "__main__":
    verify_oauth_success()
