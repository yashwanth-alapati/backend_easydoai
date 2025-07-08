import os
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from agents import EasydoAgent
import models
import database
from models import User
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from chat_service import ChatService
from contextlib import asynccontextmanager
from mongodb_config import (
    close_mongodb_connection,
    is_mongodb_available,
)
from alembic.config import Config
from alembic import command


# The new lifespan context manager to handle startup and shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC (moved from on_startup) ---
    print(">>> [LIFESPAN] Starting up application...")
    try:
        # Check if DATABASE_URL is available
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print(">>> [LIFESPAN] WARNING: DATABASE_URL not found!")
        else:
            print(f">>> [LIFESPAN] DATABASE_URL found: {db_url[:50]}...")

            # Run migrations using the Alembic API - this is more reliable
            print(">>> [LIFESPAN] Running Alembic migrations...")
            try:
                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
                print(">>> [LIFESPAN] ✅ Migrations completed successfully!")
            except Exception as e:
                # Log the error but don't crash the app
                print(f">>> [LIFESPAN] ❌ Migration failed: {e}")

        # Initialize MongoDB connection
        print(">>> [LIFESPAN] Initializing MongoDB connection...")
        if is_mongodb_available():
            print(">>> [LIFESPAN] ✅ MongoDB connection appears to be available.")
        else:
            print(
                ">>> [LIFESPAN] ⚠️ MongoDB not available - chat features will be limited."
            )

    except Exception as e:
        # Log any other startup errors without crashing
        print(
            f">>> [LIFESPAN] ❌ An unexpected error occurred during startup: {str(e)}"
        )

    print(">>> [LIFESPAN] Startup complete.")
    yield
    # --- SHUTDOWN LOGIC (moved from on_shutdown) ---
    print(">>> [LIFESPAN] Shutting down application...")
    try:
        close_mongodb_connection()
        print(">>> [LIFESPAN] ✅ MongoDB connection closed.")
    except Exception as e:
        print(f">>> [LIFESPAN] ❌ Error closing MongoDB connection: {e}")


app = FastAPI(lifespan=lifespan)

# Read CORS origins from environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
# Strip whitespace from each origin
allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint for Elastic Beanstalk health checks
@app.get("/")
def read_root():
    return {"status": "ok"}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AgentTaskRequest(BaseModel):
    title: str


class ChatRequest(BaseModel):
    message: str


class TaskMessageRequest(BaseModel):
    message: str
    email: EmailStr


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = pwd_context.hash(req.password)
    new_user = models.User(email=req.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Signup successful"}


@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}


# Replace the existing /tasks endpoints with MongoDB versions


@app.get("/tasks")
def list_tasks(email: str = Query(None), db: Session = Depends(get_db)):
    """List chat sessions (MongoDB) instead of PostgreSQL tasks"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    if email:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return []

        chat_service = ChatService()
        sessions = chat_service.get_user_sessions(user.id)

        # Convert MongoDB sessions to task-like format for frontend compatibility
        return [
            {
                "id": session["_id"],  # Use MongoDB _id as task id
                "title": session["title"],
                "status": "complete",  # All sessions are "complete"
                "messages": [],  # Don't load messages here for performance
                "user_id": session["user_id"],
                "created_at": (
                    session["created_at"].isoformat()
                    if session.get("created_at")
                    else None
                ),
                "session_id": session["_id"],  # Include session_id for reference
            }
            for session in sessions
        ]
    else:
        return []  # Don't list all sessions without email filter


@app.post("/tasks")
async def create_task_with_message(
    req: TaskMessageRequest,
    session_id: str = Query(
        None, description="Existing session ID to continue, or None for new"
    ),
    db: Session = Depends(get_db),
):
    """
    Homepage chat logic:
    - If session_id provided: continue that session WITH history
    - If no session_id: create new session (for new chat)
    """
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()

    if session_id:
        # ✅ CONTINUE EXISTING SESSION
        session = chat_service.get_session_by_id(session_id)
        if not session or session["user_id"] != user.id:
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
        # ✅ CREATE NEW SESSION
        title = " ".join(req.message.split()[:7])
        session_id = chat_service.create_chat_session(user.id, title)
        conversation_history = []
        print(f">>> Created NEW session: {session_id}")

    # Add the user message
    chat_service.add_message(session_id, user.id, "user", req.message)

    # Process with agent WITH conversation history
    agent = EasydoAgent()
    reply = await agent.process_message(
        req.message, conversation_history=conversation_history
    )

    # Add agent response
    chat_service.add_message(session_id, user.id, "assistant", reply)

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
        "user_id": user.id,
        "created_at": (
            session["created_at"].isoformat() if session.get("created_at") else None
        ),
        "session_id": session_id,
    }


@app.post("/tasks/{task_id}/messages")
async def add_message(task_id: str, req: Request, db: Session = Depends(get_db)):
    """Add message to existing MongoDB chat session WITH conversation history"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    data = await req.json()
    user_message = data.get("message")
    email = data.get("email")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message required")

    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()

    # Verify session exists and belongs to user
    session = chat_service.get_session_by_id(task_id)
    if not session or session["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # ✅ GET CONVERSATION HISTORY BEFORE ADDING NEW MESSAGE
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
    chat_service.add_message(task_id, user.id, "user", user_message)

    # ✅ Get assistant reply WITH conversation history
    agent = EasydoAgent()
    reply = await agent.process_message(
        user_message, conversation_history=conversation_history
    )

    # Add assistant response
    chat_service.add_message(task_id, user.id, "assistant", reply)

    # Get all messages for this session
    messages = chat_service.get_session_messages(task_id)

    # Convert to expected format
    formatted_messages = [
        {"role": msg["role"], "message": msg["message"]} for msg in messages
    ]

    return {"messages": formatted_messages}


@app.get("/tasks/{task_id}/messages")
def get_task_messages(task_id: str, db: Session = Depends(get_db)):
    """Get messages from MongoDB chat session instead of PostgreSQL task"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    chat_service = ChatService()

    # Verify session exists
    session = chat_service.get_session_by_id(task_id)  # task_id is actually session_id
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages for this session
    messages = chat_service.get_session_messages(task_id)

    # Convert to expected format
    formatted_messages = [
        {"role": msg["role"], "message": msg["message"]} for msg in messages
    ]

    return {"messages": formatted_messages}


# --- Your chat endpoint ---
agent = EasydoAgent()


@app.post("/chat")
async def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    """Chat endpoint using MongoDB for conversation history"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get conversation history from MongoDB instead of PostgreSQL
    chat_service = ChatService()
    context_messages = get_last_n_chat_messages_from_mongodb(
        chat_service, user.id, n=10
    )

    # Convert dicts to BaseMessage objects
    conversation_history = []
    for msg in context_messages:
        role = msg.get("role")
        content = msg.get("message") or msg.get("content")
        if role == "user":
            conversation_history.append(HumanMessage(content=content))
        elif role == "assistant":
            conversation_history.append(AIMessage(content=content))
        elif role == "system":
            conversation_history.append(SystemMessage(content=content))

    # Print/log the conversation history for debugging
    print("=== Conversation history being sent to agent (from MongoDB) ===")
    for i, m in enumerate(conversation_history):
        print(f"{i}: {type(m).__name__}: {getattr(m, 'content', '')}")
    print("===============================================")

    # Pass conversation_history to your LLM agent
    reply = await agent.process_message(
        req.message, conversation_history=conversation_history
    )
    return {"reply": reply}


# NEW: Chat session endpoints
@app.post("/chat/sessions")
async def create_chat_session(req: TaskMessageRequest, db: Session = Depends(get_db)):
    """Create a new chat session"""
    if not is_mongodb_available():
        raise HTTPException(
            status_code=503, detail="Chat service is currently unavailable"
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create the session
    chat_service = ChatService()
    title = " ".join(req.message.split()[:7])  # Use first 7 words as title
    session_id = chat_service.create_chat_session(user.id, title)

    # Add the first message
    chat_service.add_message(session_id, user.id, "user", req.message)

    # Process with agent
    agent = EasydoAgent()
    reply = await agent.process_message(req.message)

    # Add agent response
    chat_service.add_message(session_id, user.id, "assistant", reply)

    return {
        "session_id": session_id,
        "title": title,
        "message": "Session created successfully",
    }


@app.get("/chat/sessions")
def get_user_chat_sessions(email: str = Query(...), db: Session = Depends(get_db)):
    """Get all chat sessions for a user"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()
    sessions = chat_service.get_user_sessions(user.id)
    return {"sessions": sessions}


@app.get("/chat/sessions/{session_id}/messages")
def get_chat_messages(
    session_id: str,
    email: str = Query(...),
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """Get messages for a specific chat session"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()

    # Verify session belongs to user
    session = chat_service.get_session_by_id(session_id)
    if not session or session["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = chat_service.get_session_messages(session_id, limit, skip)
    return {"session": session, "messages": messages}


@app.post("/chat/sessions/{session_id}/messages")
async def add_chat_message(
    session_id: str, req: Request, db: Session = Depends(get_db)
):
    """Add a message to an existing chat session"""
    data = await req.json()
    user_message = data.get("message")
    email = data.get("email")

    if not user_message or not email:
        raise HTTPException(status_code=400, detail="Message and email required")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()

    # Verify session belongs to user
    session = chat_service.get_session_by_id(session_id)
    if not session or session["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Add user message
    chat_service.add_message(session_id, user.id, "user", user_message)

    # Process with agent
    agent = EasydoAgent()
    reply = await agent.process_message(user_message)

    # Add agent response
    chat_service.add_message(session_id, user.id, "assistant", reply)

    return {"message": "Messages added successfully"}


@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str, email: str = Query(...), db: Session = Depends(get_db)
):
    """Delete a chat session"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()
    success = chat_service.delete_session(session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session deleted successfully"}


@app.get("/chat/search")
def search_chat_messages(
    query: str = Query(...),
    email: str = Query(...),
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Search chat messages"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_service = ChatService()
    messages = chat_service.search_messages(user.id, query, limit)
    return {"messages": messages}


@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "success", "message": "Database connection works!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Add helper function for MongoDB conversation history
def get_last_n_chat_messages_from_mongodb(
    chat_service: ChatService, user_id: int, n: int = 10
):
    """Get last n messages from MongoDB - SHOULD NOT MIX SESSIONS"""
    # ❌ This function should not be used for session-based chats
    # Return empty to force proper session management
    return []


# Remove the old PostgreSQL-based function (keep for now, but unused)
def get_last_n_task_messages(db, user_id: int, n: int = 10):
    """DEPRECATED: Old PostgreSQL-based function - no longer used"""
    return []  # Return empty list since we're using MongoDB now


# Add a health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mongodb_available": is_mongodb_available(),
        "database_available": True,  # PostgreSQL is required
    }
