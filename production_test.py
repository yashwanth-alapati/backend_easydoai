"""
Production readiness test for Gmail MCP integration
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_production_readiness():
    """Test that all components are ready for production"""
    
    print("🚀 Production Readiness Test")
    print("=" * 50)
    
    # Test 1: Environment Variables
    print("1. 🔐 Testing Environment Variables...")
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
        else:
            print(f"   ✅ {var}: {'*' * 10}{value[-4:]}")
    
    if missing_vars:
        print(f"   ❌ Missing: {missing_vars}")
        return False
    
    # Test 2: AWS Lambda Connection
    print("\n2. 🔗 Testing AWS Lambda Connection...")
    try:
        import boto3
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        # Test function exists
        response = lambda_client.get_function(
            FunctionName='LambdaMCPStack-GmailMCPLambdaD2EF2F90-M8OUb80rPJ9G'
        )
        print(f"   ✅ Lambda function found: {response['Configuration']['FunctionName']}")
        
    except Exception as e:
        print(f"   ❌ Lambda connection failed: {e}")
        return False
    
    # Test 3: DynamoDB Connection - USE ENVIRONMENT VARIABLE
    print("\n3. 📊 Testing DynamoDB Connection...")
    try:
        import boto3
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = os.getenv('TOKENS_TABLE_NAME')  # Use actual env var
        table = dynamodb.Table(table_name)
        
        print(f"   🔍 Looking for table: {table_name}")
        
        # Test table exists
        table.load()
        print(f"   ✅ DynamoDB table found: {table.table_name}")
        
        # Test table structure
        print(f"   📋 Table status: {table.table_status}")
        print(f"   🗝️  Key schema: {[key['AttributeName'] for key in table.key_schema]}")
        
    except Exception as e:
        print(f"   ❌ DynamoDB connection failed: {e}")
        
        # Try to list all tables to help debug
        try:
            print("   🔍 Available tables:")
            client = boto3.client('dynamodb', region_name='us-east-1')
            tables = client.list_tables()['TableNames']
            for t in tables:
                print(f"      - {t}")
        except:
            pass
        return False
    
    # Test 4: Gmail Lambda Function
    print("\n4. 📧 Testing Gmail Lambda Function...")
    try:
        from services.gmail_lambda_service import gmail_lambda_service
        
        # Test tools listing
        result = await gmail_lambda_service.list_available_tools()
        if result.get('status') == 'success':
            tools = result.get('tools', [])
            print(f"   ✅ Gmail tools available: {len(tools)}")
            for tool in tools:
                print(f"      - {tool['name']}: {tool['description']}")
        else:
            print(f"   ❌ Gmail tools test failed: {result}")
            return False
            
    except Exception as e:
        print(f"   ❌ Gmail Lambda test failed: {e}")
        return False
    
    # Test 5: OAuth Service
    print("\n5. 🔑 Testing OAuth Service...")
    try:
        from services.google_oauth import oauth_service
        
        # Test OAuth URL generation
        auth_data = oauth_service.get_authorization_url('gmail', 'test_user')
        if auth_data.get('authorization_url'):
            print(f"   ✅ OAuth URL generation working")
            print(f"      URL length: {len(auth_data['authorization_url'])} chars")
        else:
            print(f"   ❌ OAuth URL generation failed")
            return False
            
    except Exception as e:
        print(f"   ❌ OAuth service test failed: {e}")
        return False
    
    print("\n🎉 All Production Tests Passed!")
    print("✅ Ready for Elastic Beanstalk deployment")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_production_readiness())