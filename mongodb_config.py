import os
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

load_dotenv()

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "easydo_chat")

# Global MongoDB client and database
_client: Optional[MongoClient] = None
_database: Optional[Database] = None

logger = logging.getLogger(__name__)


def get_mongodb_client() -> Optional[MongoClient]:
    """Get MongoDB client instance (singleton) - returns None if connection fails"""
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
            )
            # Test the connection
            _client.admin.command("ping")
            logger.info("✅ Connected to MongoDB successfully!")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB connection failed: {e}")
            logger.info("💡 Application will continue without MongoDB chat features")
            return None
    return _client


def get_mongodb_database() -> Optional[Database]:
    """Get MongoDB database instance"""
    global _database
    if _database is None:
        client = get_mongodb_client()
        if client is None:
            return None
        _database = client[MONGODB_DATABASE]
    return _database


def get_chat_collection() -> Optional[Collection]:
    """Get the chat messages collection"""
    db = get_mongodb_database()
    if db is None:
        return None
    return db.chat_messages


def get_chat_sessions_collection() -> Optional[Collection]:
    """Get the chat sessions collection"""
    db = get_mongodb_database()
    if db is None:
        return None
    return db.chat_sessions


def is_mongodb_available() -> bool:
    """Check if MongoDB is available"""
    try:
        client = get_mongodb_client()
        return client is not None
    except:
        return False


# Chat message document structure
class ChatMessage:
    """Chat message document structure for MongoDB"""

    @staticmethod
    def create_message(
        session_id: str,
        user_id: int,
        role: str,  # 'user' or 'assistant'
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a chat message document"""
        return {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        }


# Chat session document structure
class ChatSession:
    """Chat session document structure for MongoDB"""

    @staticmethod
    def create_session(
        user_id: int, title: str, session_type: str = "task_chat"
    ) -> Dict[str, Any]:
        """Create a chat session document"""
        return {
            "user_id": user_id,
            "title": title,
            "session_type": session_type,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 0,
        }


def close_mongodb_connection():
    """Close MongoDB connection"""
    global _client, _database
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")
