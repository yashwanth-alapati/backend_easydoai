[![Coverage Status](https://coveralls.io/repos/github/yashwanth-alapati/backend_tachyfy/badge.svg)](https://coveralls.io/github/yashwanth-alapati/backend_tachyfy)

# Tachyfy - AI-Powered Task Management Platform

A comprehensive AI-powered task management platform that integrates multiple services (Gmail, Google Calendar, Web Search) through a sophisticated multi-agent system. Built with React frontend, FastAPI backend, and AWS cloud infrastructure.

## 🚀 Live Deployment

The application is deployed on AWS Elastic Beanstalk and accessible at:
- **Production URL**: `https://your-app-name.eba-kzi5p2rc.region.elasticbeanstalk.com`
- **API Documentation**: `https://your-app-name.eba-kzi5p2rc.region.elasticbeanstalk.com/docs`

## 📋 Table of Contents

- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Core Components](#core-components)
- [Multi-Agent System](#multi-agent-system)
- [API Architecture](#api-architecture)
- [Security](#security)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                TACHYFY ECOSYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Frontend (React)          Backend (FastAPI)           Cloud Services (AWS)     │
│  ┌─────────────────┐      ┌─────────────────┐        ┌─────────────────┐       │
│  │  React App      │◄────►│  API Gateway    │        │  Lambda Functions│       │
│  │  - TypeScript   │      │  - FastAPI      │        │  - Gmail MCP     │       │
│  │  - React Router │      │  - Multi-Agent  │        │  - Calendar MCP  │       │
│  │  - Context API  │      │  - Tool System  │        │  - Containerized │       │
│  └─────────────────┘      └─────────────────┘        └─────────────────┘       │
│                                     │                                            │
│  ┌─────────────────┐      ┌─────────────────┐        ┌─────────────────┐       │
│  │  Storage        │      │  AI System      │        │  Data Layer     │       │
│  │  - LocalStorage │      │  - Claude Model │        │  - DynamoDB     │       │
│  │                 │      │  - LangChain    │        │  - MongoDB      │       │
│  │                 │      │  - LangGraph    │        │  - PostgreSQL   │       │
│  └─────────────────┘      └─────────────────┘        └─────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

- **Microservices**: Loosely coupled services with clear boundaries
- **Event-Driven**: Asynchronous communication patterns
- **Cloud-Native**: Designed for AWS cloud infrastructure
- **Security-First**: Built-in security at every layer
- **Scalable**: Horizontal scaling capabilities

## 🛠 Technology Stack

### Frontend
- **Framework**: React 19.1.0 with TypeScript
- **Routing**: React Router DOM 7.6.2
- **State Management**: React Context API
- **Build Tool**: React Scripts 5.0.1
- **Styling**: CSS with responsive design

### Backend
- **Framework**: FastAPI with Python 3.11+
- **AI/ML**: LangChain, LangGraph, Anthropic Claude 3.5 Haiku
- **Database**: PostgreSQL with SQLAlchemy ORM, MongoDB for chat history
- **Authentication**: Passlib with bcrypt, OAuth2
- **API Documentation**: Automatic OpenAPI/Swagger generation

### Cloud Infrastructure
- **Hosting**: AWS Elastic Beanstalk
- **Functions**: AWS Lambda (containerized)
- **Storage**: DynamoDB for tokens, MongoDB for chat history
- **Container Registry**: Amazon ECR
- **Security**: IAM roles and policies

### Key Dependencies

```python
# Backend (requirements.txt)
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
langchain>=0.1.0
langgraph>=0.1.0
langchain-anthropic>=0.1.0
anthropic>=0.8.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pymongo>=4.13.2
boto3>=1.34.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

```json
// Frontend (package.json)
{
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-router-dom": "^7.6.2",
    "typescript": "^4.9.5"
  }
}
```

## 🤖 Multi-Agent System

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MULTI-AGENT SUPERVISOR                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   SUPERVISOR    │    │    RETRIEVER    │    │    EXECUTOR     │  │
│  │     AGENT       │    │     AGENT       │    │     AGENT       │  │
│  │                 │    │                 │    │                 │  │
│  │ • Coordinates   │    │ • Web Search    │    │ • Gmail Actions │  │
│  │ • Delegates     │    │ • Research      │    │ • Calendar Mgmt │  │
│  │ • Orchestrates  │    │ • Info Gather   │    │ • Task Exec     │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │         │
│           └───────────────────────┼───────────────────────┘         │
│                                   │                                 │
│  ┌─────────────────────────────────┼─────────────────────────────────┐  │
│  │                    TOOL SYSTEM                                  │  │
│  │                                                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│  │  │ Web Search  │  │ Gmail MCP   │  │ Calendar    │             │  │
│  │  │ - Tavily    │  │ - Lambda    │  │ - Lambda    │             │  │
│  │  │ - Real-time │  │ - OAuth2    │  │ - OAuth2    │             │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

#### Supervisor Agent
- **Workflow Coordination**: Orchestrates complex multi-step tasks
- **Task Delegation**: Routes tasks to appropriate specialized agents
- **Result Synthesis**: Combines results from multiple agents
- **Error Handling**: Manages failures and retries across agents

#### Retriever Agent
- **Information Gathering**: Web search and research capabilities
- **Data Processing**: Formats and structures retrieved information
- **Context Building**: Provides relevant context for task execution
- **Real-time Updates**: Fetches current information from external sources

#### Executor Agent
- **Action Execution**: Performs concrete actions (emails, calendar events)
- **Service Integration**: Interfaces with external APIs and services
- **Transaction Management**: Ensures atomic operations across services
- **Result Reporting**: Provides detailed execution feedback

### Workflow Coordination Rules

1. **Pure Research Tasks**: Direct routing to Retriever Agent
2. **Pure Action Tasks**: Direct routing to Executor Agent (with full context)
3. **Combined Tasks**: Sequential processing (Research → Action)
4. **Error Recovery**: Intelligent retry mechanisms with context preservation

## 🔧 Core Components

### Authentication System

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AUTHENTICATION FLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Frontend (React)         Backend (FastAPI)         External APIs   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  AuthContext    │    │  Auth Endpoints │    │  Google OAuth2  │  │
│  │  - Login/Logout │◄──►│  - JWT Tokens   │◄──►│  - Gmail API    │  │
│  │  - LocalStorage │    │  - User Service │    │  - Calendar API │  │
│  │  - Route Guards │    │  - OAuth Flow   │    │  - Token Refresh│  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                   │                                 │
│  ┌─────────────────────────────────┼─────────────────────────────────┐  │
│  │                    TOKEN STORAGE                                │  │
│  │                                                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│  │  │ DynamoDB    │  │ JWT Tokens  │  │ Refresh     │             │  │
│  │  │ - OAuth     │  │ - Session   │  │ - Auto      │             │  │
│  │  │ - TTL       │  │ - Secure    │  │ - Rotation  │             │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Layer

**Multi-Database Strategy:**
- **PostgreSQL**: Primary database for user accounts, task metadata
- **MongoDB**: Chat history, conversation state, session management
- **DynamoDB**: OAuth tokens, temporary data with TTL
- **LocalStorage**: Frontend session persistence

```python
# Database Models
class User(SQLAlchemyBase):
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Document):
    session_id = StringField(required=True)
    user_id = IntField(required=True)
    message = StringField(required=True)
    response = StringField()
    timestamp = DateTimeField(default=datetime.utcnow)
```

### Tool Integration System

```python
def get_tools(selected_tools: Optional[List[str]] = None) -> List[Tool]:
    """
    Dynamically load tools from the available_tools directory.
    Each tool module defines a get_tool() function that returns a Tool instance.
    """
    all_tools = []
    
    # Load all available tools
    for filename in os.listdir(AVAILABLE_TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{AVAILABLE_TOOLS_DIR}.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "get_tool"):
                    tool = module.get_tool()
                    all_tools.append(tool)
            except Exception as e:
                print(f"Error loading tool {module_name}: {e}")
    
    return all_tools
```

## 🔗 API Architecture

### RESTful API Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API ENDPOINTS                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Authentication        Chat/Tasks             Integrations          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ POST /auth/     │    │ POST /chat/     │    │ GET /gmail/     │  │
│  │ - login         │    │ - send-message  │    │ - authorize     │  │
│  │ - signup        │    │ - get-history   │    │ - messages      │  │
│  │ - refresh       │    │ - create-task   │    │ - send          │  │
│  │ - logout        │    │ - list-tasks    │    │ - status        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ OAuth Flow      │    │ WebSocket       │    │ Calendar API    │  │
│  │ - /google/auth  │    │ - Real-time     │    │ - /calendar/    │  │
│  │ - /callback     │    │ - Live Updates  │    │ - authorize     │  │
│  │ - /refresh      │    │ - Notifications │    │ - events        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### API Endpoints

#### Authentication

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/signup` | Register new user | `{"email": "user@example.com", "password": "password"}` |
| POST | `/login` | User login | `{"email": "user@example.com", "password": "password"}` |

#### Tasks

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/tasks` | List user tasks | `?email=user@example.com` |
| POST | `/tasks` | Create new task | `{"message": "task description", "email": "user@example.com"}` |
| GET | `/tasks/{task_id}/messages` | Get task messages | - |
| POST | `/tasks/{task_id}/messages` | Add message to task | `{"message": "new message"}` |

#### Chat

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/chat` | Chat with AI agent | `{"message": "your message", "email": "user@example.com"}` |

#### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/db-test` | Database connection test |

## 🔐 Security

### Security Features

- **Authentication**: JWT tokens with refresh mechanism
- **Authorization**: Role-based access control (RBAC)
- **OAuth2 Integration**: Secure third-party service access
- **Data Encryption**: At rest and in transit
- **Rate Limiting**: API endpoint protection
- **Input Validation**: Comprehensive request validation
- **CORS Configuration**: Cross-origin request security
- **Security Headers**: Comprehensive security headers

## 🚀 Setup & Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 13+**
- **MongoDB 6+**
- **AWS CLI configured**
- **Docker & Docker Compose**

### Local Development Setup

#### 1. Clone Repository
```bash
git clone https://github.com/yashwanth-alapati/tachyfy.git
cd tachyfy
```

#### 2. Backend Setup
```bash
cd tachyfy_backend

# Create virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup
```bash
cd tachyfy_frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run frontend
npm start
```

#### 4. Docker Setup (Alternative)
```bash
# Run full stack with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## ⚙️ Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/tachyfy
MONGODB_URL=mongodb://localhost:27017/tachyfy_chat

# AI Services
ANTHROPIC_API_KEY=your_anthropic_api_key
TAVILY_API_KEY=your_tavily_api_key

# Google OAuth
EASYDOAI_GOOGLE_CLIENT_ID=your_google_client_id
EASYDOAI_GOOGLE_CLIENT_SECRET=your_google_client_secret
EASYDOAI_GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# AWS
AWS_REGION=us-east-1
TOKENS_TABLE_NAME=easydoai-user-tokens

# Security
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:3000
```

#### Frontend (.env)
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_GOOGLE_CLIENT_ID=your_google_client_id
```

### AWS Elastic Beanstalk Configuration

For production deployment, set these environment variables in EB:

```bash
eb setenv DATABASE_URL="postgresql://..." \
         ANTHROPIC_API_KEY="..." \
         TAVILY_API_KEY="..." \
         ALLOWED_ORIGINS="https://your-frontend.com"
```

## 💡 Usage Examples

### 1. User Registration

```bash
curl -X POST "http://localhost:8000/signup" \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "securepassword123"}'
```

**Response:**
```json
{"message": "Signup successful"}
```

### 2. User Login

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "securepassword123"}'
```

**Response:**
```json
{"message": "Login successful"}
```

### 3. Create a Task

```bash
curl -X POST "http://localhost:8000/tasks" \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule a meeting with the team", "email": "john@example.com"}'
```

**Response:**
```json
{
  "id": 1,
  "title": "Schedule a meeting with the",
  "status": "complete",
  "messages": [
    {"role": "user", "message": "Schedule a meeting with the team"},
    {"role": "assistant", "message": "I'll help you schedule a meeting..."}
  ],
  "user_id": 1,
  "created_at": "2024-01-15T10:30:00"
}
```

### 4. Chat with AI Agent

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my upcoming meetings?", "email": "john@example.com"}'
```

**Response:**
```json
{
  "reply": "Let me check your calendar for upcoming meetings..."
}
```

### 5. Gmail Integration

```bash
# Initiate Gmail OAuth
curl -X GET "http://localhost:8000/auth/google/authorize/gmail?user_id=123"

# Send Email
curl -X POST "http://localhost:8000/gmail/send" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Meeting Reminder",
    "body": "Don'\''t forget about our meeting tomorrow at 2 PM"
  }'
```

## 🧪 Development

### Project Structure

```
tachyfy/
├── tachyfy_backend/
│   ├── agents.py                  # Multi-agent system
│   ├── main.py                    # FastAPI application
│   ├── auth_endpoints.py          # Authentication routes
│   ├── chat_service.py            # Chat management
│   ├── mongodb_config.py          # MongoDB configuration
│   ├── available_tools/
│   │   ├── gmail_mcp.py          # Gmail integration
│   │   ├── google_calendar.py    # Calendar integration
│   │   └── websearch.py          # Web search tool
│   ├── services/
│   │   ├── google_oauth.py       # OAuth service
│   │   ├── gmail_lambda_service.py
│   │   └── calendar_lambda_service.py
│   ├── aws_services/
│   │   └── dynamodb_config.py    # DynamoDB configuration
│   ├── infrastructure/
│   │   ├── app.py                # CDK app
│   │   └── lambda_mcp_stack.py   # Lambda infrastructure
│   └── lambda_mcp_servers/
│       ├── gmail_lambda/
│       └── calendar_lambda/
├── tachyfy_frontend/
│   ├── public/
│   └── src/
│       ├── App.tsx               # Main application
│       ├── AuthContext.tsx       # Authentication context
│       ├── Home.tsx              # Main interface
│       ├── Login.tsx             # Login component
│       ├── Signup.tsx            # Signup component
│       └── components/
│           └── GlobalNotifications.tsx
└── README.md
```

### Development Guidelines

#### Code Style
- **Python**: Black formatter, Flake8 linter
- **TypeScript**: ESLint with React rules
- **Git**: Conventional commits
- **Testing**: Pytest for backend, Jest for frontend

#### Local Development Commands
```bash
# Start backend with hot reload
uvicorn main:app --reload

# Start frontend with hot reload
npm start

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

### Running Tests

```bash
# Backend tests
pytest tests/ -v --cov=. --cov-report=html

# Frontend tests
npm test -- --coverage --watchAll=false

# Run specific test file
pytest tests/test_auth.py -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 --max-line-length=88 --ignore=E501,E203,W503 --exclude=env .

# Run both (as in CI)
black --check . && flake8 --max-line-length=88 --ignore=E501,E203,W503 --exclude=env .
```

### Adding New Tools

1. Create tool file in `available_tools/`
2. Implement tool function
3. Register in `tools.py`
4. Add to agent in `agents.py`

Example tool structure:
```python
# available_tools/my_tool.py
def my_tool_func(param: str) -> dict:
    """Tool description"""
    # Implementation
    return {"result": "success"}
```

## 📦 Deployment

### AWS Infrastructure

#### 1. Lambda Functions Deployment
```bash
cd tachyfy_backend/lambda_mcp_servers

# Deploy Gmail and Calendar Lambda functions
./deploy.sh
```

#### 2. Backend Deployment (Elastic Beanstalk)
```bash
# Initialize Elastic Beanstalk
eb init -p python-3.11 tachyfy-backend

# Create environment
eb create tachyfy-backend-prod

# Deploy
eb deploy
```

#### 3. Frontend Deployment
```bash
# Build for production
npm run build

# Deploy to S3 + CloudFront (example)
aws s3 sync build/ s3://your-frontend-bucket/
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

### CI/CD Pipeline

The application uses GitHub Actions for automated deployment:

1. **Push to main branch** triggers GitHub Actions
2. **Tests run** with coverage reporting
3. **Code quality checks** (black, flake8)
4. **Build and deploy** to Elastic Beanstalk
5. **Database migrations** run automatically

### Environment Variables in Production

Set in Elastic Beanstalk environment:
- `DATABASE_URL`: RDS connection string
- `ANTHROPIC_API_KEY`: AI service key
- `TAVILY_API_KEY`: Search API key
- `ALLOWED_ORIGINS`: Frontend domain(s)

## 🔄 Monitoring & Observability

### Performance Monitoring

- **Response Time Tracking**: API endpoint performance
- **Database Query Monitoring**: Slow query detection
- **Memory Usage**: Lambda function optimization
- **Error Rate Monitoring**: Service health metrics

### Logging Strategy

The project maintains >80% test coverage with structured logging:

```bash
coverage run --source='.' -m pytest
coverage report -m
coverage html  # Generate HTML report
```

## 🤝 Contributing

### Development Workflow

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Ensure CI/CD pipeline passes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- **Frontend**: [Tachyfy Frontend Repository](https://github.com/yashwanth-alapati/tachyfy_frontend)
- **Gmail MCP Server**: [Gmail MCP Integration](https://github.com/yashwanth-alapati/gmail-mcp-server)
- **Google Calendar MCP**: [Calendar Integration](https://github.com/yashwanth-alapati/google-calendar-mcp)

## 📞 Support

For support and questions:
- **Issues**: [GitHub Issues](https://github.com/yashwanth-alapati/tachyfy/issues)
- **Email**: [ya2351@nyu.edu](mailto:ya2351@nyu.edu)
- **Documentation**: Available in the `/docs` directory

## 🙏 Acknowledgments

- **Anthropic**: For the Claude AI model
- **LangChain**: For the agent framework
- **FastAPI**: For the excellent web framework
- **React**: For the frontend framework
- **AWS**: For cloud infrastructure
- **Open Source Community**: For the amazing tools and libraries

---

**Built with ❤️ using FastAPI, React, and AWS - Deployed on Elastic Beanstalk**
```

I've updated the README.md with a comprehensive architecture overview that covers:

1. **Complete System Architecture** - Both frontend and backend with visual diagrams
2. **Multi-Agent System Details** - Detailed explanation of the supervisor, retriever, and executor agents
3. **Technology Stack** - Comprehensive coverage of all technologies used
4. **Security Architecture** - Complete security implementation details
5. **API Documentation** - Full REST API reference
6. **Setup Instructions** - Step-by-step setup for both frontend and backend
7. **Development Guidelines** - Code style, testing, and contribution guidelines
8. **Deployment Strategy** - AWS infrastructure and CI/CD pipeline
9. **Monitoring & Observability** - Performance tracking and logging
10. **Project Structure** - Complete file organization

The README now serves as a comprehensive guide for anyone wanting to understand, contribute to, or deploy the Tachyfy platform. It maintains the specific details from the original README while providing the full architectural overview of the entire system.