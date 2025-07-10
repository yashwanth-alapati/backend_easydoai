"""
Debug token storage and retrieval
"""
import boto3
import json
from dotenv import load_dotenv

load_dotenv()

def debug_tokens():
    """Debug what's in DynamoDB vs what Lambda expects"""
    
    print("🔍 Debugging Token Storage")
    print("=" * 50)
    
    user_id = "686da1e3e74f0d3ccd019830"
    
    # Check DynamoDB directly
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('easydoai-user-tokens-dev')
    
    try:
        # Check what's stored
        response = table.get_item(Key={'user_id': user_id, 'service': 'gmail'})
        
        if 'Item' in response:
            item = response['Item']
            print(f"✅ Found tokens in DynamoDB:")
            print(f"   User ID: {item.get('user_id')}")
            print(f"   Service: {item.get('service')}")
            print(f"   Access Token: {item.get('access_token', 'MISSING')[:20]}...")
            print(f"   Refresh Token: {item.get('refresh_token', 'MISSING')[:20]}...")
            print(f"   Scope: {item.get('scope', 'MISSING')}")
            print(f"   Expires At: {item.get('expires_at', 'MISSING')}")
            print(f"   Created At: {item.get('created_at', 'MISSING')}")
            
            # Test Lambda directly with same user_id
            print(f"\n🧪 Testing Lambda with same user_id...")
            
            lambda_client = boto3.client('lambda', region_name='us-east-1')
            payload = {
                "jsonrpc": "2.0",
                "id": "debug_test",
                "method": "tools/call",
                "params": {
                    "name": "get_gmail_messages",
                    "arguments": {
                        "user_id": user_id,
                        "query": "",
                        "max_results": 1
                    }
                }
            }
            
            response = lambda_client.invoke(
                FunctionName='LambdaMCPStack-GmailMCPLambdaD2EF2F90-M8OUb80rPJ9G',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            print(f"   Lambda Response: {json.dumps(result, indent=2)}")
            
        else:
            print(f"❌ No tokens found for user {user_id}")
            
            # List all items in table
            print(f"\n📋 All items in table:")
            scan_response = table.scan()
            for item in scan_response['Items']:
                print(f"   {item.get('user_id')} / {item.get('service')}")
                
    except Exception as e:
        print(f"❌ Error checking DynamoDB: {e}")

if __name__ == "__main__":
    debug_tokens() 