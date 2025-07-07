import json
import os
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from agents import EasydoAgent
import models
import database
from models import AgentTask, User
from langchain.schema import HumanMessage, AIMessage, SystemMessage

app = FastAPI()

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


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    try:
        models.Base.metadata.create_all(bind=database.engine)
        print(">>> Tables creation attempted")
    except Exception as e:
        print(">>> Table creation error:", e)


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


@app.get("/tasks")
def list_tasks(email: str = Query(None), db: Session = Depends(get_db)):
    if email:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return []
        tasks = db.query(AgentTask).filter(AgentTask.user_id == user.id).all()
    else:
        tasks = db.query(AgentTask).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "messages": json.loads(t.messages) if t.messages else [],
            "user_id": t.user_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


class TaskMessageRequest(BaseModel):
    message: str
    email: EmailStr


@app.post("/tasks")
async def create_task_with_message(
    req: TaskMessageRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    agent = EasydoAgent()
    reply = await agent.process_message(req.message)
    messages = [
        {"role": "user", "message": req.message},
        {"role": "assistant", "message": reply},
    ]
    new_task = AgentTask(
        title=" ".join(req.message.split()[:7]),
        status="complete",
        messages=json.dumps(messages),
        user_id=user.id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {
        "id": new_task.id,
        "title": new_task.title,
        "status": new_task.status,
        "messages": messages,
        "user_id": new_task.user_id,
        "created_at": new_task.created_at.isoformat() if new_task.created_at else None,
    }


@app.post("/tasks/{task_id}/messages")
async def add_message(task_id: int, req: Request, db: Session = Depends(get_db)):
    data = await req.json()
    user_message = data.get("message")
    if not user_message:
        raise HTTPException(status_code=400, detail="Message required")
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    messages = json.loads(task.messages) if task.messages else []
    # Add user message
    messages.append({"role": "user", "message": user_message})
    # Get assistant reply
    agent = EasydoAgent()
    reply = await agent.process_message(user_message)
    messages.append({"role": "assistant", "message": reply})
    task.messages = json.dumps(messages)
    db.commit()
    return {"messages": messages}


@app.get("/tasks/{task_id}/messages")
def get_task_messages(task_id: int, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return json.loads(task.messages) if task.messages else []


# --- Your chat endpoint ---
agent = EasydoAgent()


@app.post("/chat")
async def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Get last n messages for context
    context_messages = get_last_n_task_messages(db, user.id, n=10)
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
    print("=== Conversation history being sent to agent ===")
    for i, m in enumerate(conversation_history):
        print(f"{i}: {type(m).__name__}: {getattr(m, 'content', '')}")
    print("===============================================")
    # Pass conversation_history to your LLM agent
    reply = await agent.process_message(
        req.message, conversation_history=conversation_history
    )
    return {"reply": reply}


@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "success", "message": "Database connection works!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_last_n_task_messages(db, user_id: int, n: int = 10):
    tasks = (
        db.query(AgentTask)
        .filter(AgentTask.user_id == user_id)
        .order_by(AgentTask.created_at.desc())
        .limit(n)
        .all()
    )
    # Flatten all messages from these tasks
    all_messages = []
    for task in reversed(tasks):  # reverse to get oldest first
        if task.messages:
            try:
                all_messages.extend(json.loads(task.messages))
            except Exception:
                pass
    return all_messages
