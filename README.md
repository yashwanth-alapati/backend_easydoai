[![Coverage Status](https://coveralls.io/repos/github/yashwanth-alapati/backend_easydoai/badge.svg)](https://coveralls.io/github/yashwanth-alapati/backend_easydoai)

# EasyDoAI Backend

A FastAPI-based backend service for the EasyDo AI application, providing intelligent task management and AI-powered assistance through various integrated tools including Gmail, Google Calendar, and web search capabilities.

## 🚀 Live Deployment

The application is deployed on AWS Elastic Beanstalk and accessible at:
- **Production URL**: `https://your-app-name.eba-kzi5p2rc.region.elasticbeanstalk.com`
- **API Documentation**: `https://your-app-name.eba-kzi5p2rc.region.elasticbeanstalk.com/docs`

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## ✨ Features

- **User Authentication**: Secure signup/login with bcrypt password hashing
- **Task Management**: Create, read, and manage AI-powered tasks
- **AI Chat Interface**: Interactive chat with conversation history
- **Tool Integration**: 
  - Gmail MCP integration for email management
  - Google Calendar integration for scheduling
  - Web search capabilities via Tavily API
- **Database Management**: PostgreSQL with Alembic migrations
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **CI/CD Pipeline**: Automated testing and deployment via GitHub Actions

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Passlib with bcrypt
- **AI/ML**: LangChain, LangGraph, Anthropic Claude
- **Tools**: Gmail MCP, Google Calendar API, Tavily Search
- **Testing**: Pytest with coverage reporting
- **Code Quality**: Black, Flake8
- **Deployment**: AWS Elastic Beanstalk
- **CI/CD**: GitHub Actions

## 📁 Project Structure

```
easydo_backend/
├── .ebextensions/              # Elastic Beanstalk configuration
│   └── 01_migrations.config    # Database migration config
├── .github/workflows/          # CI/CD pipeline
│   └── deploy.yml             # GitHub Actions workflow
├── alembic/                   # Database migrations
│   ├── versions/              # Migration files
│   └── env.py                # Alembic environment
├── available_tools/           # AI agent tools
│   ├── gmail_mcp.py          # Gmail integration
│   ├── google_calendar.py    # Calendar integration
│   └── websearch.py          # Web search tool
├── tests/                     # Test files
│   └── test_auth.py          # Authentication tests
├── utils/                     # Utility modules
│   └── tool_permissions.py   # Tool permission management
├── main.py                    # FastAPI application
├── models.py                  # Database models
├── database.py                # Database configuration
├── agents.py                  # AI agent implementation
├── tools.py                   # Tool management
├── requirements.txt           # Python dependencies
├── Procfile                   # Web server configuration
├── alembic.ini               # Alembic configuration
├── docker-compose.test.yml   # Test database setup
└── README.md                 # This file
```

## 🚀 Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd easydo_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env  # Create from template
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   # Start PostgreSQL and create database
   createdb easydo_db
   
   # Run migrations
   alembic upgrade head
   ```

6. **Run the application**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

The application will be available at `http://localhost:8000`

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost/easydo_db

# AI Services
ANTHROPIC_API_KEY=your_anthropic_api_key

# Tool APIs
TAVILY_API_KEY=your_tavily_api_key
GOOGLE_CALENDAR_CREDENTIALS=path/to/credentials.json

# Security
SECRET_KEY=your_secret_key_here

# CORS (for production)
ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:3000
```

### AWS Elastic Beanstalk Configuration

For production deployment, set these environment variables in EB:

```bash
eb setenv DATABASE_URL="postgresql://..." \
         ANTHROPIC_API_KEY="..." \
         TAVILY_API_KEY="..." \
         ALLOWED_ORIGINS="https://your-frontend.com"
```

## 📚 API Endpoints

### Authentication

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/signup` | Register new user | `{"email": "user@example.com", "password": "password"}` |
| POST | `/login` | User login | `{"email": "user@example.com", "password": "password"}` |

### Tasks

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/tasks` | List user tasks | `?email=user@example.com` |
| POST | `/tasks` | Create new task | `{"message": "task description", "email": "user@example.com"}` |
| GET | `/tasks/{task_id}/messages` | Get task messages | - |
| POST | `/tasks/{task_id}/messages` | Add message to task | `{"message": "new message"}` |

### Chat

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/chat` | Chat with AI agent | `{"message": "your message", "email": "user@example.com"}` |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/db-test` | Database connection test |

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

### 5. List User Tasks

```bash
curl "http://localhost:8000/tasks?email=john@example.com"
```

**Response:**
```json
[
  {
    "id": 1,
    "title": "Schedule a meeting with the",
    "status": "complete",
    "messages": [...],
    "user_id": 1,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
coverage run -m pytest
coverage report -m

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

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade migration
alembic downgrade -1
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

## 🧪 Testing

### Test Database Setup

```bash
# Start test database
docker compose -f docker-compose.test.yml up -d

# Run tests
pytest

# Stop test database
docker compose -f docker-compose.test.yml down
```

### Test Coverage

The project maintains >80% test coverage. Run coverage reports:

```bash
coverage run --source='.' -m pytest
coverage report -m
coverage html  # Generate HTML report
```

## 🚀 Deployment

### AWS Elastic Beanstalk

The application is configured for deployment on AWS Elastic Beanstalk with:

- **Platform**: Python 3.11 on Amazon Linux 2023
- **Database**: RDS PostgreSQL (production)
- **CI/CD**: GitHub Actions automated deployment

### Deployment Process

1. **Push to main branch** triggers GitHub Actions
2. **Tests run** with coverage reporting
3. **Code quality checks** (black, flake8)
4. **Build and deploy** to Elastic Beanstalk
5. **Database migrations** run automatically

### Manual Deployment

```bash
# Initialize EB (one-time)
eb init

# Deploy
eb deploy

# Check status
eb status

# View logs
eb logs
```

### Environment Variables in Production

Set in Elastic Beanstalk environment:
- `DATABASE_URL`: RDS connection string
- `ANTHROPIC_API_KEY`: AI service key
- `TAVILY_API_KEY`: Search API key
- `ALLOWED_ORIGINS`: Frontend domain(s)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Ensure CI/CD pipeline passes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- **Frontend**: [EasyDo Frontend Repository](link-to-frontend)
- **Gmail MCP Server**: [Gmail MCP Integration](link-to-gmail-mcp)
- **Google Calendar MCP**: [Calendar Integration](link-to-calendar-mcp)

## 📞 Support

For support and questions:
- Create an issue in this repository
- Contact: [ya2351@nyu.edu]

---

**Built with ❤️ using FastAPI and deployed on AWS Elastic Beanstalk**