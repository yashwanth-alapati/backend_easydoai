# main rbanch Tachyfy Backend - AI-Powered Task Management Platform

[![Coverage Status](https://coveralls.io/repos/github/yashwanth-alapati/backend_tachyfy/badge.svg)](https://coveralls.io/github/yashwanth-alapati/backend_tachyfy)

## 🌟 High-Level Overview

**Tachyfy** is a sophisticated AI-powered task management platform that leverages a **multi-agent architecture** to intelligently coordinate complex workflows involving email management, calendar scheduling, and real-time information retrieval. Built with modern cloud-native principles, the system uses **FastAPI** as the core backend framework, **Anthropic's Claude 3.5 Haiku** for AI reasoning, and **AWS serverless infrastructure** for scalable tool execution.

### Core Value Proposition

- **🤖 Multi-Agent Intelligence**: Specialized agents (Supervisor, Retriever, Executor) coordinate seamlessly to handle complex multi-step tasks
- **🔗 Unified API Gateway**: Single interface for email, calendar operations through standardized MCP (Model Context Protocol) servers
- **☁️ Cloud-Native Architecture**: AWS ECR containers + Serverless Lambda functions with automatic scaling and cost optimization for mcp server tools.
- **🔐 Enterprise-Grade Security**: Google OAuth2 integration for gmail and calendar tool use.
- **🚀 Real-Time Processing**: Asynchronous task execution with live status updates and conversation history


## 🏗️ System Architecture(TO-dO add diagram)

### Multi-Agent Coordination Flow(To-do add agent diagram)


## 🛠 Technology Stack

### Core Backend Framework
```yaml
Framework: FastAPI 0.104.0+
Runtime: Python 3.11+
Server: Uvicorn with async support
Middleware: CORS, Authentication, Rate Limiting
LLM Provider: Anthropic Claude 3.5 Haiku
Framework: LangChain 0.1.0+ with LangGraph
Agent Architecture: Multi-agent supervisor pattern
Tool Integration: Dynamic tool loading system
Context Management: Conversation history + user context
Chat Storage: MongoDB 6+ (Conversation history, sessions)
Token Storage: DynamoDB (OAuth tokens with TTL)
Primary Hosting: AWS Elastic Beanstalk
Serverless Compute: AWS Lambda (Containerized for mcp tools)
Container Registry: Amazon ECR(for mcp tools)
Infrastructure as Code: AWS CDK (TypeScript)
Monitoring: CloudWatch + X-Ray tracing
Authentication: JWT tokens with refresh mechanism
OAuth2 Provider: Google (Gmail + Calendar scopes)
Token Management: Automatic refresh, secure storage
```

---

## 🤖 Multi-Agent System Deep Dive

### Agent Responsibilities Matrix

| Agent | Primary Role | Tools Available | Communication Pattern |
|-------|-------------|-----------------|----------------------|
| **Supervisor** | Orchestration & Coordination | `transfer_to_retriever`, `transfer_to_executor` | Delegates tasks, synthesizes results |
| **Retriever** | Information Gathering | `web_search`, `report_to_supervisor` | Researches, extracts, reports back |
| **Executor** | Action Execution | `gmail_send_email`, `google_calendar_mcp`, `report_to_supervisor` | Executes, confirms, reports status |

### Workflow Coordination Patterns

#### 1. Pure Research Tasks
```
User Request → Supervisor → Retriever Agent → Web Search → Results → User
```

#### 2. Pure Action Tasks (with complete context)
```
User Request → Supervisor → Executor Agent → Service API → Confirmation → User
```

#### 3. Complex Multi-Step Tasks (research +execution)
```
User Request → Supervisor → Retriever Agent → Research Results → 
             ↓
Supervisor → Executor Agent → Action Execution → Confirmation → User
```

### Agent Prompt Engineering

Each agent has specialized prompts optimized for their role:

- **Supervisor**: Decision-making, task decomposition, result synthesis
- **Retriever**: Search optimization, information extraction, context building
- **Executor**: Action validation, error handling, confirmation reporting

---

## 🔧 Core Components

### 1. Tool System Architecture(Hardcoded to use all tools for now since we have limited number anyways)

```python
# Dynamic Tool Loading System
class ToolLoader:
    def __init__(self):
        self.available_tools = self._discover_tools()
    
    def _discover_tools(self) -> List[Tool]:
        """Dynamically loads tools from available_tools/ directory"""
        tools = []
        for module in os.listdir("available_tools"):
            if module.endswith(".py"):
                tool_module = importlib.import_module(f"available_tools.{module[:-3]}")
                if hasattr(tool_module, "get_tool"):
                    tools.append(tool_module.get_tool())
        return tools
```

### 2. Available Tools

#### Web Search Tool (`websearch.py`)
- **Provider**: Tavily API
- **Capabilities**: Real-time search + content extraction
- **Features**: Intelligent query optimization, multi-source aggregation

#### Gmail MCP Tool (`gmail_mcp.py`)
- **Integration**: Google Gmail API via Lambda
- **Operations**: Send, read, search, manage emails
- **Security**: OAuth2 with automatic token refresh

#### Google Calendar Tool (`google_calendar.py`)
- **Integration**: Google Calendar API via Lambda
- **Operations**: Create, update, list, delete events
- **Features**: Multi-calendar support, attendee management

### 3. Authentication & Authorization System

```python
# Multi-Layer Security Architecture
class AuthenticationSystem:
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.oauth_manager = OAuth2Manager()
        self.token_store = DynamoDBTokenStore()
    
    async def authenticate_user(self, email: str, password: str) -> AuthResult:
        """Primary authentication with JWT generation"""
        
    async def refresh_oauth_token(self, user_id: str, service: str) -> TokenResult:
        """Automatic OAuth token refresh for external services"""
        
    async def validate_permissions(self, user_id: str, tool_name: str) -> bool:
        """Tool-level permission validation"""
```

### 4. Database Models & Schema

#### MongoDB Collections
```javascript
// Chat sessions and conversation history
{
  _id: ObjectId,
  session_id: String,
  user_id: Number,
  messages: [{
    role: String, // "user" | "assistant" | "system"
    message: String,
    timestamp: Date,
    metadata: Object
  }],
  status: String, // "active" | "complete" | "processing"
  created_at: Date,
  updated_at: Date
}
```

#### DynamoDB Schema
```json
{
  "TableName": "easydoai-user-tokens",
  "KeySchema": [
    {"AttributeName": "user_id", "KeyType": "HASH"},
    {"AttributeName": "service", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "user_id", "AttributeType": "S"},
    {"AttributeName": "service", "AttributeType": "S"}
  ],
  "TimeToLiveSpecification": {
    "AttributeName": "ttl",
    "Enabled": true
  }
}
```

---

## 🔗 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/signup` | User registration | `{"email": "user@example.com", "password": "secure123"}` | `{"message": "Signup successful"}` |
| POST | `/login` | User authentication | `{"email": "user@example.com", "password": "secure123"}` | `{"message": "Login successful", "token": "jwt_token"}` |
| POST | `/auth/refresh` | Token refresh | `{"refresh_token": "refresh_jwt"}` | `{"access_token": "new_jwt"}` |
| POST | `/logout` | User logout | `{}` | `{"message": "Logout successful"}` |

### Task Management Endpoints

| Method | Endpoint | Description | Parameters | Response Schema |
|--------|----------|-------------|------------|-----------------|
| GET | `/tasks` | List user tasks | `?email=user@example.com` | `{"tasks": [TaskObject]}` |
| POST | `/tasks` | Create new task | `{"message": "task description", "email": "user@example.com", "selected_tools": ["gmail_mcp"]}` | `TaskObject` |
| GET | `/tasks/{task_id}/messages` | Get conversation history | - | `{"messages": [MessageObject]}` |
| POST | `/tasks/{task_id}/messages` | Add message to conversation | `{"message": "new message", "email": "user@example.com"}` | `MessageObject` |

### Integration Endpoints

#### Gmail Integration
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/auth/google/authorize/gmail` | Initiate Gmail OAuth | Query param: `user_id` |
| GET | `/auth/google/callback` | OAuth callback handler | Auto-handled |
| GET | `/gmail/status` | Check Gmail connection | JWT token required |
| GET | `/gmail/tools` | List available Gmail tools | JWT token required |

#### Calendar Integration
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/auth/google/authorize/calendar` | Initiate Calendar OAuth | Query param: `user_id` |
| GET | `/calendar/tools` | List available Calendar tools | JWT token required |
| POST | `/calendar/execute` | Execute calendar operation | JWT token + request body |

### System Endpoints

| Method | Endpoint | Description | Purpose |
|--------|----------|-------------|---------|
| GET | `/health` | Health check | System monitoring |
| GET | `/db-test` | Database connectivity test | Infrastructure validation |
| GET | `/available-tools` | List all available tools | Tool discovery |
| POST | `/chat` | Direct chat with AI system | `{"message": "query", "email": "user@example.com"}` |

---

## ⚙️ Configuration & Setup

### Environment Variables

#### Core Application Settings
```bash
# Database Connections
DATABASE_URL=postgresql://user:password@localhost:5432/tachyfy
MONGODB_URL=mongodb://localhost:27017/tachyfy_chat

# AI Service Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
TAVILY_API_KEY=your_tavily_search_api_key

# JWT Security
JWT_SECRET_KEY=your_super_secure_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth2 Configuration
EASYDOAI_GOOGLE_CLIENT_ID=your_google_oauth_client_id
EASYDOAI_GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
EASYDOAI_GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback # for production use that url

# AWS Configuration
AWS_REGION=us-east-1
TOKENS_TABLE_NAME=your-table-name
GMAIL_LAMBDA_FUNCTION_NAME=your-gmail-lambda
CALENDAR_LAMBDA_FUNCTION_NAME=your-calendar-lambda

# CORS and Security
ALLOWED_ORIGINS=Your-allowed-origins
```

### Local Development Setup

#### 1. Prerequisites Installation
```bash
# Install Python 3.11+
brew install python@3.11  # macOS
sudo apt install python3.11 python3.11-venv  # Ubuntu

# Install MongoDB
brew install mongodb-community  # macOS
sudo apt install mongodb  # Ubuntu

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awsclip.zip"
unzip awsclip.zip && sudo ./aws/install
```

#### 2. Project Setup
```bash
# Clone and navigate
git clone https://github.com/yashwanth-alapati/tachyfy.git
cd tachyfy/tachyfy_backend

# Create virtual environment
python3.11 -m venv env
source env/bin/activate  # Linux/macOS
# env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks
pre-commit install
```

#### 3. Database Initialization
```bash

# MongoDB setup (auto-creates collections)
mongod --dbpath /usr/local/var/mongodb

```

#### 4. AWS Services Setup
```bash
# Configure AWS credentials
aws configure

# Deploy Lambda functions
cd lambda_mcp_servers
./deploy.sh

```

#### 5. Start Development Server
```bash
# Run with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Verify API is running
curl http://localhost:8000/health
```


## 🧪 Testing & Quality Assurance

### Test Suite Architecture



### Code Quality Tools

```bash
# Format code with Black
black . --line-length 88


# Lint with Flake8
flake8 . --max-line-length=88 --ignore=E203,W503 --exclude=env

---

## 🚀 Deployment & Infrastructure

### AWS Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION INFRASTRUCTURE                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Internet Gateway          Application Load Balancer        Auto Scaling        │
│  ┌─────────────────┐      ┌─────────────────┐             ┌─────────────────┐   │
│  │ Route 53        │─────►│ ALB + WAF       │────────────►│ Elastic         │   │
│  │ • DNS           │      │ • SSL/TLS       │             │ Beanstalk       │   │
│  │ • Health Checks │      │ • Rate Limiting │             │ • Auto Scaling  │   │
│  └─────────────────┘      └─────────────────┘             └─────────────────┘   │
│                                     │                              │            │
│  ┌─────────────────────────────────────────────────────────────────┼─────────┐  │
│  │                         COMPUTE & SERVERLESS LAYER               │         │  │
│  │                                                                   │         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │ Lambda      │  │ Lambda      │  │ ECR         │  │ CloudWatch  │       │  │
│  │  │ Gmail MCP   │  │ Calendar    │  │ Container   │  │ Monitoring  │       │  │
│  │  │ Function    │  │ MCP Function│  │ Registry    │  │ & Logging   │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA & STORAGE LAYER                           │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ RDS         │  │ DocumentDB  │  │ DynamoDB    │  │ S3 Buckets  │     │   │
│  │  │ PostgreSQL  │  │ MongoDB API │  │ Token Store │  │ Static      │     │   │
│  │  │ Multi-AZ    │  │ Cluster     │  │ Global      │  │ Assets      │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

 
```





## 🤝 Contributing

### Development Workflow

1. **Fork & Clone**
   ```bash
   git clone https://github.com/your-username/tachyfy.git
   cd tachyfy/tachyfy_backend
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/agent-memory-optimization
   ```

3. **Development Setup**
   ```bash
   python -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pre-commit install
   ```

4. **Code & Test**
   ```bash
   # Write code following style guide
   # Add comprehensive tests
   pytest tests/ -v --cov=.
   ```

5. **Quality Checks**
   ```bash
   black .
   flake8 .
   ```

6. **Commit & Push**
   ```bash
   git add .
   git commit -m "feat: optimize agent memory usage for large conversations"
   git push origin feature/agent-memory-optimization
   ```

7. **Create Pull Request**
   - Comprehensive description
   - Link related issues
   - Include test results
   - Request review from maintainers

### Contribution Guidelines

- **Code Review**: All changes require review from 2+ maintainers
- **Testing**: Minimum x% test coverage for new code
- **Documentation**: Update relevant documentation


**Built with ❤️ using FastAPI, Claude AI, and AWS - Deployed on Elastic Beanstalk**

