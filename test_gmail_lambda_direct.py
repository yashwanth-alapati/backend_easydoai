"""
Test Gmail Lambda directly without OAuth integration
"""

import asyncio
import boto3
import json


async def test_gmail_lambda_direct():
    """Test Gmail Lambda function directly"""

    print("🧪 Testing Gmail Lambda Function Directly")
    print("=" * 50)

    # Initialize Lambda client
    lambda_client = boto3.client("lambda", region_name="us-east-1")
    function_name = "LambdaMCPStack-GmailMCPLambdaD2EF2F90-M8OUb80rPJ9G"

    # Test 1: List available tools
    print("1. 📋 Testing tools/list...")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "test_list",
            "method": "tools/list",
            "params": {},
        }

        response = lambda_client.invoke(
            FunctionName=function_name, Payload=json.dumps(payload)
        )

        result = json.loads(response["Payload"].read())
        print(f"   Status Code: {response['StatusCode']}")
        print(f"   Result: {json.dumps(result, indent=2)}")

    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: Try to get messages (expect auth error)
    print("\n2. 📧 Testing get_gmail_messages (should show auth error)...")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "test_get_messages",
            "method": "tools/call",
            "params": {
                "name": "get_gmail_messages",
                "arguments": {
                    "user_id": "test_user_123",
                    "query": "",
                    "max_results": 5,
                },
            },
        }

        response = lambda_client.invoke(
            FunctionName=function_name, Payload=json.dumps(payload)
        )

        result = json.loads(response["Payload"].read())
        print(f"   Status Code: {response['StatusCode']}")
        print(f"   Result: {json.dumps(result, indent=2)}")

        # Check if it's the expected auth error
        if "error" in result and "not authenticated" in str(result["error"]):
            print("   ✅ Perfect! Lambda correctly detected missing authentication")
        else:
            print("   ⚠️  Unexpected response - check Lambda logs")

    except Exception as e:
        print(f"   Error: {e}")

    print("\n🎯 Lambda Function Test Complete!")
    print("Next step: Set up OAuth credentials to enable full flow")


if __name__ == "__main__":
    asyncio.run(test_gmail_lambda_direct())
