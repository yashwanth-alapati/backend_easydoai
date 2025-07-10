# Gmail MCP Server on AWS Lambda - Complete Setup Guide

A FastAPI-based backend service with serverless Gmail MCP (Model Context Protocol) integration on AWS Lambda, enabling AI agents to securely access and manage user Gmail data through OAuth2 authentication.

## Architecture Overview

This implementation provides a complete Gmail MCP server running on AWS Lambda with the following components:

- **FastAPI Backend**: Main application server on AWS Elastic Beanstalk
- **Gmail MCP Lambda**: Serverless MCP server for Gmail operations
- **DynamoDB**: OAuth token storage with TTL-based cleanup
- **Google OAuth2**: Secure authentication flow
- **AWS CDK**: Infrastructure as Code for deployment

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Component Setup](#component-setup)
- [AWS Infrastructure Setup](#aws-infrastructure-setup)
- [Google OAuth Configuration](#google-oauth-configuration)
- [Lambda MCP Server Deployment](#lambda-mcp-server-deployment)
- [Backend Integration](#backend-integration)
- [Production Deployment](#production-deployment)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.11+
- Docker for Lambda container builds
- Node.js and AWS CDK for infrastructure deployment
- Google Cloud Console project with Gmail API enabled

## Component Setup

### 1. Core Components

```
easydo_backend/
├── lambda_mcp_servers/           # Lambda MCP implementations
│   ├── gmail_lambda/            # Gmail MCP server
│   │   ├── gmail_server.py      # Main Lambda handler
│   │   ├── Dockerfile           # Container configuration
│   │   └── requirements.txt     # Python dependencies
│   └── deploy.sh               # Deployment script
├── infrastructure/              # AWS CDK infrastructure
│   ├── lambda_mcp_stack.py     # CDK stack definition
│   ├── app.py                  # CDK app entry point
│   └── dynamodb-tokens.yaml    # DynamoDB table config
├── services/                    # Backend service integrations
│   ├── gmail_lambda_service.py # Lambda invocation service
│   └── google_oauth.py         # OAuth2 flow management
├── aws_services/               # AWS service configurations
│   └── dynamodb_config.py      # DynamoDB token storage
└── gmail_endpoints.py          # FastAPI Gmail endpoints
```

## AWS Infrastructure Setup

### 1. DynamoDB Table Creation

Create the OAuth tokens table:

```bash
aws dynamodb create-table \
    --table-name your-user-tokens-table \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=service,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=service,KeyType=RANGE \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region your-aws-region
```

### 2. ECR Repository Setup

Create ECR repositories for Lambda containers:

```bash
aws ecr create-repository --repository-name your-gmail-mcp-repo --region your-aws-region
aws ecr create-repository --repository-name your-calendar-mcp-repo --region your-aws-region
```

### 3. CDK Infrastructure Deployment

Deploy the Lambda MCP stack:

```bash
cd infrastructure/
npm install -g aws-cdk
pip install aws-cdk-lib constructs
cdk bootstrap
cdk deploy YourMCPStack
```

## Google OAuth Configuration

### 1. Google Cloud Console Setup

1. Create a new project in Google Cloud Console
2. Enable Gmail API
3. Create OAuth2 credentials (Web application)
4. Configure authorized redirect URIs:
   - `http://localhost:8000/auth/google/callback` (development)
   - `https://your-domain.com/auth/google/callback` (production)

### 2. Required OAuth Scopes

Configure these scopes in your Google OAuth consent screen:

```
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.readonly
```

### 3. Environment Variables

Set these environment variables in your deployment:

```env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback
TOKENS_TABLE_NAME=your-user-tokens-table
AWS_REGION=your-aws-region
```

## Lambda MCP Server Deployment

### 1. Build and Deploy Gmail Lambda

```bash
cd lambda_mcp_servers/
chmod +x deploy.sh
./deploy.sh
```

### 2. Lambda Configuration

The Gmail Lambda function includes:

- **Runtime**: Python 3.11 container
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `TOKENS_TABLE_NAME`: DynamoDB table name
  - `GOOGLE_CLIENT_ID`: Google OAuth client ID
  - `GOOGLE_CLIENT_SECRET`: Google OAuth client secret

### 3. IAM Permissions

The Lambda execution role requires:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:PutItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/your-user-tokens-*"
        }
    ]
}
```

## Backend Integration

### 1. Elastic Beanstalk Configuration

Add environment variables to your EB environment:

```bash
eb setenv GOOGLE_CLIENT_ID="your_client_id" \
         GOOGLE_CLIENT_SECRET="your_client_secret" \
         GOOGLE_REDIRECT_URI="https://your-domain.com/auth/google/callback"
```

### 2. Lambda Invoke Permissions

Grant Elastic Beanstalk permission to invoke Lambda:

```yaml
# .ebextensions/lambda_permissions.config
Resources:
  LambdaInvokePolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: EBLambdaInvokePolicy
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - lambda:InvokeFunction
            Resource: 
              - "arn:aws:lambda:your-region:*:function:your-gmail-lambda-function*"
      Roles:
        - Ref: AWS::IAM::Role
```

## Production Deployment

### 1. Environment Setup

For production deployment on Elastic Beanstalk:

1. Set all required environment variables
2. Configure proper CORS origins
3. Enable HTTPS with SSL certificates
4. Set up monitoring and logging

### 2. OAuth Production Configuration

Update Google OAuth settings for production:

1. Add production domain to authorized origins
2. Update redirect URIs for production URLs
3. Submit app for Google verification (for public use)

## API Endpoints

### Gmail Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google` | Initiate OAuth flow |
| GET | `/auth/google/callback` | Handle OAuth callback |
| GET | `/gmail/status` | Check authentication status |

### Gmail Operations

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| GET | `/gmail/messages` | Get Gmail messages | `?query=search&max_results=10` |
| POST | `/gmail/send` | Send email | `{"to": "email", "subject": "text", "body": "text"}` |
| GET | `/gmail/tools` | List available tools | - |

## Usage Examples

### 1. OAuth Authentication Flow

```bash
# Step 1: Initiate OAuth
curl "http://localhost:8000/auth/google?user_id=123&service=gmail"

# Response: {"authorization_url": "https://accounts.google.com/..."}

# Step 2: User visits URL and authorizes
# Step 3: Google redirects to callback with code
# Step 4: Backend exchanges code for tokens and stores in DynamoDB
```

### 2. Send Email via MCP

```bash
curl -X POST "http://localhost:8000/gmail/send" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Hello from MCP",
    "body": "This email was sent via Gmail MCP Lambda!"
  }'
```

### 3. Get Gmail Messages

```bash
curl "http://localhost:8000/gmail/messages?query=from:sender@example.com&max_results=5"
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "messages": [
      {
        "id": "msg_123",
        "subject": "Important Update",
        "sender": "sender@example.com",
        "date": "2024-01-15",
        "snippet": "Please review the attached document..."
      }
    ],
    "total": 5
  }
}
```

## Troubleshooting

### Common Issues

1. **"User not authenticated for Gmail"**
   - Verify OAuth tokens in DynamoDB
   - Check token expiration
   - Ensure proper Google OAuth scopes

2. **Lambda InvokeFunction permission denied**
   - Verify IAM roles and policies
   - Check Lambda function name in service configuration

3. **Google OAuth "access_denied" error**
   - Verify OAuth consent screen configuration
   - Check if app is in testing mode (add test users)
   - Ensure proper redirect URI configuration

### Debug Steps

1. Check CloudWatch logs for Lambda execution
2. Verify DynamoDB table access and data
3. Test OAuth flow manually
4. Validate environment variable configuration

## Security Considerations

### 1. Token Security

- OAuth tokens stored in DynamoDB with TTL
- Automatic token refresh when expired
- Secure token transmission via HTTPS only

### 2. Access Control

- User-specific token isolation
- IAM least-privilege principles
- VPC configuration for enhanced security (optional)

### 3. Monitoring

- CloudWatch logging for all operations
- DynamoDB access patterns monitoring
- Lambda execution metrics tracking

### 4. Security Best Practices

**Critical Security Guidelines:**

- **Never commit credentials to version control**
- Use environment variables for all sensitive data
- Add `.env` files to `.gitignore`
- Use AWS Secrets Manager or Parameter Store for production secrets
- Rotate credentials regularly
- Follow principle of least privilege for IAM roles
- Enable MFA for AWS accounts
- Use HTTPS for all communications
- Implement proper input validation
- Monitor for unusual access patterns

## Development and Testing

### Local Development

```bash
# Set up environment
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# Run local server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing OAuth Flow

```python
# Test DynamoDB token storage
from aws_services.dynamodb_config import token_storage

# Store test tokens
tokens = {
    "access_token": "test_token",
    "refresh_token": "refresh_token",
    "expires_in": 3600,
    "scope": "gmail.modify gmail.send"
}
token_storage.store_tokens("test_user", "gmail", tokens)

# Retrieve tokens
stored_tokens = token_storage.get_tokens("test_user", "gmail")
```

### Environment Variables Template

Create a `.env.template` file for contributors:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# AWS Configuration
AWS_REGION=us-east-1
TOKENS_TABLE_NAME=your-tokens-table-name

# Application Configuration
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key-here
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Implement changes with tests
4. Update documentation
5. Ensure all tests pass and no security vulnerabilities
6. Submit pull request

### Development Guidelines

- Follow security best practices
- Write comprehensive tests
- Update documentation for any changes
- Use meaningful commit messages
- Ensure code formatting with Black and Flake8

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create GitHub issue with detailed description
- Check existing issues before creating new ones
- Follow the issue template when reporting bugs

---

**Security Notice**: This documentation contains placeholder values. Replace all placeholder credentials and configuration values with your actual values, but never commit real credentials to version control.
