from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(
        Enum("processing", "needs_permission", "complete", name="status_enum"),
        default="processing",
    )
    messages = Column(
        Text
    )  # Store as JSON string or use a related table for production
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(
        DateTime, default=datetime.utcnow
    )  # <-- Make sure this line exists
    user = relationship("User")
