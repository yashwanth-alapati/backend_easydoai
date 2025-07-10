import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from agents import EasydoAgent
from langchain.schema import HumanMessage, AIMessage
from chat_service import ChatService
from user_service import user_service
from mongodb_config import (
    close_mongodb_connection,
    is_mongodb_available,
)
from auth_endpoints import router as auth_router
from gmail_endpoints import router as gmail_router


# The new lifespan context manager to handle startup and shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    print(">>> [LIFESPAN] Starting up application...")
    try:
        # Check required environment variables
        required_env_vars = [
            "EASYDOAI_GOOGLE_CLIENT_ID",
            "EASYDOAI_GOOGLE_CLIENT_SECRET",
            "EASYDOAI_GOOGLE_REDIRECT_URI",
        ]

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            print(f">>> [LIFESPAN] ⚠️ Missing environment variables: {missing_vars}")
        else:
            print(">>> [LIFESPAN] ✅ All required OAuth environment variables found")

        # Initialize MongoDB connection
        print(">>> [LIFESPAN] Initializing MongoDB connection...")
        if is_mongodb_available():
            print(">>> [LIFESPAN] ✅ MongoDB connection appears to be available.")
        else:
            print(
                ">>> [LIFESPAN] ⚠️ MongoDB not available - application will be limited."
            )

    except Exception as e:
        print(f">>> [LIFESPAN] ❌ An unexpected error occurred during startup: {str(e)}")

    print(">>> [LIFESPAN] Startup complete.")
    yield
    # --- SHUTDOWN LOGIC ---
    print(">>> [LIFESPAN] Shutting down application...")
    try:
        close_mongodb_connection()
        print(">>> [LIFESPAN] ✅ MongoDB connection closed.")
    except Exception as e:
        print(f">>> [LIFESPAN] ❌ Error closing MongoDB connection: {e}")


app = FastAPI(lifespan=lifespan)

# Read CORS origins from environment variable - UPDATE FOR PRODUCTION
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,https://tachyfy.com"
).split(",")
allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(gmail_router)


# Root endpoint for Elastic Beanstalk health checks
@app.get("/")
def read_root():
    return {"status": "ok", "version": "1.0", "services": ["gmail_mcp", "chat", "auth"]}


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChatRequest(BaseModel):
    message: str
    email: EmailStr


class TaskMessageRequest(BaseModel):
    message: str
    email: EmailStr


@app.post("/signup")
def signup(req: SignupRequest):
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="User service is currently unavailable"
        )

    try:
        user = user_service.create_user(req.email, req.password)
        return {"message": "Signup successful", "user_id": user["id"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/login")
def login(req: LoginRequest):
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="User service is currently unavailable"
        )

    user = user_service.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user_id": user["id"]}


@app.get("/tasks")
def list_tasks(email: str = Query(None)):
    """List chat sessions (MongoDB) instead of PostgreSQL tasks"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    if email:
        user = user_service.get_user_by_email(email)
        if not user:
            return []

        chat_service = ChatService()
        sessions = chat_service.get_user_sessions(user["id"])

        # Convert MongoDB sessions to task-like format for frontend compatibility
        return [
            {
                "id": session["_id"],
                "title": session["title"],
                "status": "complete",
                "messages": [],
                "user_id": session["user_id"],
                "created_at": (
                    session["created_at"].isoformat()
                    if session.get("created_at")
                    else None
                ),
                "session_id": session["_id"],
            }
            for session in sessions
        ]
    else:
        return []


@app.post("/tasks")
async def create_task_with_message(
    req: TaskMessageRequest,
    session_id: str = Query(
        None, description="Existing session ID to continue, or None for new"
    ),
):
    """Homepage chat logic: continue existing session or create new"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    user = user_service.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()

    if session_id:
        # Continue existing session
        session = chat_service.get_session_by_id(session_id)
        if not session or session["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Session not found")

        print(f">>> Continuing existing session: {session_id}")

        # Get conversation history
        session_messages = chat_service.get_session_messages(session_id)
        conversation_history = []
        for msg in session_messages:
            role = msg.get("role")
            content = msg.get("message")
            if role == "user":
                conversation_history.append(HumanMessage(content=content))
            elif role == "assistant":
                conversation_history.append(AIMessage(content=content))

        print(f">>> Loaded {len(conversation_history)} messages from history")

    else:
        # Create new session
        title = " ".join(req.message.split()[:7])
        session_id = chat_service.create_chat_session(user["id"], title)
        conversation_history = []
        print(f">>> Created NEW session: {session_id}")

    # Add the user message
    chat_service.add_message(session_id, user["id"], "user", req.message)

    # Process with agent WITH conversation history AND user_id
    agent = EasydoAgent()
    reply = await agent.process_message(
        req.message,
        conversation_history=conversation_history,
        user_id=user["id"],  # Pass user_id to agent
    )

    # Add agent response
    chat_service.add_message(session_id, user["id"], "assistant", reply)

    # Get all messages to return
    all_messages = chat_service.get_session_messages(session_id)
    formatted_messages = [
        {"role": msg["role"], "message": msg["message"]} for msg in all_messages
    ]

    # Get session details
    session = chat_service.get_session_by_id(session_id)

    return {
        "id": session_id,
        "title": session.get("title", "Chat Session"),
        "status": "complete",
        "messages": formatted_messages,
        "user_id": user["id"],
        "created_at": (
            session["created_at"].isoformat() if session.get("created_at") else None
        ),
        "session_id": session_id,
    }


@app.post("/tasks/{task_id}/messages")
async def add_message(task_id: str, req: Request):
    """Add message to existing MongoDB chat session WITH conversation history"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    data = await req.json()
    user_message = data.get("message")
    email = data.get("email")

    if not user_message or not email:
        raise HTTPException(status_code=400, detail="Message and email required")

    user = user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()

    # Verify session exists and belongs to user
    session = chat_service.get_session_by_id(task_id)
    if not session or session["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get conversation history before adding new message
    session_messages = chat_service.get_session_messages(task_id)
    conversation_history = []
    for msg in session_messages:
        role = msg.get("role")
        content = msg.get("message")
        if role == "user":
            conversation_history.append(HumanMessage(content=content))
        elif role == "assistant":
            conversation_history.append(AIMessage(content=content))

    print(
        f">>> Continuing session {task_id} with {len(conversation_history)} previous messages"
    )

    # Add user message
    chat_service.add_message(task_id, user["id"], "user", user_message)

    # Get assistant reply WITH conversation history AND user_id
    agent = EasydoAgent()
    reply = await agent.process_message(
        user_message,
        conversation_history=conversation_history,
        user_id=user["id"],  # Pass user_id to agent
    )

    # Add assistant response
    chat_service.add_message(task_id, user["id"], "assistant", reply)

    # Get all messages for this session
    messages = chat_service.get_session_messages(task_id)

    # Convert to expected format
    formatted_messages = [
        {"role": msg["role"], "message": msg["message"]} for msg in messages
    ]

    return {"messages": formatted_messages}


@app.get("/tasks/{task_id}/messages")
def get_task_messages(task_id: str):
    """Get messages from MongoDB chat session"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    chat_service = ChatService()

    # Verify session exists
    session = chat_service.get_session_by_id(task_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages for this session
    messages = chat_service.get_session_messages(task_id)

    # Convert to expected format
    formatted_messages = [
        {"role": msg["role"], "message": msg["message"]} for msg in messages
    ]

    return {"messages": formatted_messages}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mongodb_available": is_mongodb_available(),
        "services": {
            "gmail_mcp": "available",
            "auth": "available",
            "chat": "available" if is_mongodb_available() else "limited",
        },
    }
