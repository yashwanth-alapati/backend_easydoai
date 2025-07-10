"""
Debug the exact authentication flow that Lambda uses
"""

import boto3
import os
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()


def debug_lambda_auth():
    """Test the exact same auth flow that Lambda uses"""

    print("🔍 Debugging Lambda Authentication Flow")
    print("=" * 50)

    user_id = "686da1e3e74f0d3ccd019830"

    # Use same DynamoDB logic as Lambda
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("easydoai-user-tokens-dev")

    print("1️⃣ Retrieving credentials for user {user_id}...")

    try:
        response = table.get_item(Key={"user_id": user_id, "service": "gmail"})

        if "Item" not in response:
            print("❌ No credentials found")
            return

        token_data = response["Item"]
        print("✅ Token data found: {list(token_data.keys())}")

        # Extract values (same logic as Lambda)
        def get_value(data, key):
            value = data.get(key)
            if isinstance(value, dict):
                if "S" in value:
                    return value["S"]
                elif "N" in value:
                    return value["N"]
                else:
                    return str(value)
            return value

        access_token = get_value(token_data, "access_token")
        refresh_token = get_value(token_data, "refresh_token")
        scope = get_value(token_data, "scope")
        expires_at = get_value(token_data, "expires_at")

        print("   Access Token: {access_token[:30]}...")
        print(f"   Refresh Token: {refresh_token[:30] if refresh_token else 'None'}...")
        print("   Expires At: {expires_at}")
        print("   Scope: {scope}")

        # Check expiry
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                now = (
                    datetime.now(expires_dt.tzinfo)
                    if expires_dt.tzinfo
                    else datetime.utcnow()
                )
                print("   Current Time: {now}")
                print(f"   Expired: {'Yes' if now >= expires_dt else 'No'}")
            except Exception:
                print("   ⚠️  Could not parse expiry: {e}")

        # Create credentials (same as Lambda)
        print("\n2️⃣ Creating Google credentials...")

        scopes_list = []
        if scope:
            scopes_list = scope.split(" ") if isinstance(scope, str) else scope

        client_id = os.getenv("EASYDOAI_GOOGLE_CLIENT_ID")
        client_secret = os.getenv("EASYDOAI_GOOGLE_CLIENT_SECRET")

        print("   Client ID: {client_id[:30]}...")
        print("   Client Secret: {client_secret[:10]}...")
        print("   Scopes: {scopes_list}")

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes_list,
        )

        print("   Credentials created: ✅")
        print(f"   Credentials valid: {'Yes' if credentials.valid else 'No'}")
        print(f"   Credentials expired: {'Yes' if credentials.expired else 'No'}")

        # Test Gmail API (same as Lambda)
        print("\n3️⃣ Testing Gmail API...")

        try:
            service = build("gmail", "v1", credentials=credentials)

            # Simple test - get profile
            profile = service.users().getProfile(userId="me").execute()
            print("   ✅ Gmail API working!")
            print(f"   Email: {profile.get('emailAddress')}")
            print(f"   Messages Total: {profile.get('messagesTotal')}")

            # Test messages list
            results = (
                service.users().messages().list(userId="me", maxResults=1).execute()
            )

            results.get("messages", [])
            print("   ✅ Messages accessible: {len(messages)} found")

        except Exception:
            print("   ❌ Gmail API error: {e}")

            # If expired, try refresh
            if credentials.expired and credentials.refresh_token:
                print("   🔄 Attempting token refresh...")
                try:
                    from google.auth.transport.requests import Request

                    credentials.refresh(Request())
                    print("   ✅ Token refreshed successfully")

                    # Retry Gmail API
                    service = build("gmail", "v1", credentials=credentials)
                    profile = service.users().getProfile(userId="me").execute()
                    print("   ✅ Gmail API working after refresh!")
                    print(f"   Email: {profile.get('emailAddress')}")

                except Exception:
                    print("   ❌ Token refresh failed: {refresh_error}")

    except Exception:
        print("❌ Error: {e}")


if __name__ == "__main__":
    debug_lambda_auth()
