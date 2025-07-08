from typing import List, Dict, Any, Optional
from mongodb_config import (
    get_chat_collection,
    get_chat_sessions_collection,
    is_mongodb_available,
    ChatMessage,
    ChatSession,
)
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat history in MongoDB"""

    def __init__(self):
        # Don't initialize collections here - do it lazily
        self._chat_collection = None
        self._sessions_collection = None

    @property
    def chat_collection(self):
        """Get chat collection (lazy initialization)"""
        if self._chat_collection is None:
            self._chat_collection = get_chat_collection()
        return self._chat_collection

    @property
    def sessions_collection(self):
        """Get sessions collection (lazy initialization)"""
        if self._sessions_collection is None:
            self._sessions_collection = get_chat_sessions_collection()
        return self._sessions_collection

    def _check_mongodb_available(self):
        """Check if MongoDB is available and raise exception if not"""
        if not is_mongodb_available():
            raise Exception("MongoDB is not available. Please check your connection.")

    def create_chat_session(self, user_id: int, title: str) -> str:
        """Create a new chat session and return session_id"""
        try:
            self._check_mongodb_available()
            session_doc = ChatSession.create_session(user_id, title)
            result = self.sessions_collection.insert_one(session_doc)
            session_id = str(result.inserted_id)
            logger.info(f"Created chat session {session_id} for user {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            raise

    def add_message(
        self,
        session_id: str,
        user_id: int,
        role: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a message to a chat session"""
        try:
            self._check_mongodb_available()
            message_doc = ChatMessage.create_message(
                session_id, user_id, role, message, metadata
            )
            result = self.chat_collection.insert_one(message_doc)

            # Update session message count and timestamp
            self.sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$inc": {"message_count": 1},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )

            message_id = str(result.inserted_id)
            logger.info(f"Added message {message_id} to session {session_id}")
            return message_id
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    def get_session_messages(
        self, session_id: str, limit: int = 50, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages for a specific session"""
        try:
            cursor = (
                self.chat_collection.find({"session_id": session_id})
                .sort("timestamp", 1)
                .skip(skip)
                .limit(limit)
            )

            messages = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                messages.append(doc)

            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            raise

    def get_user_sessions(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all chat sessions for a user"""
        try:
            cursor = (
                self.sessions_collection.find({"user_id": user_id})
                .sort("updated_at", -1)
                .limit(limit)
            )

            sessions = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
                sessions.append(doc)

            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
        except Exception as e:
            logger.error(f"Error retrieving sessions: {e}")
            raise

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific session by ID"""
        try:
            session = self.sessions_collection.find_one({"_id": ObjectId(session_id)})
            if session:
                session["_id"] = str(session["_id"])
            return session
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            raise

    def update_session_title(self, session_id: str, title: str) -> bool:
        """Update session title"""
        try:
            result = self.sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {"$set": {"title": title, "updated_at": datetime.utcnow()}},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating session title: {e}")
            raise

    def delete_session(self, session_id: str, user_id: int) -> bool:
        """Delete a session and all its messages"""
        try:
            # Delete all messages in the session
            self.chat_collection.delete_many({"session_id": session_id})

            # Delete the session
            result = self.sessions_collection.delete_one(
                {
                    "_id": ObjectId(session_id),
                    "user_id": user_id,  # Ensure user owns the session
                }
            )

            logger.info(f"Deleted session {session_id} and its messages")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            raise

    def search_messages(
        self, user_id: int, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search messages by text content"""
        try:
            # Create text index if it doesn't exist
            try:
                self.chat_collection.create_index([("message", "text")])
            except:
                pass  # Index might already exist

            cursor = (
                self.chat_collection.find(
                    {"user_id": user_id, "$text": {"$search": query}}
                )
                .sort("timestamp", -1)
                .limit(limit)
            )

            messages = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                messages.append(doc)

            logger.info(
                f"Found {len(messages)} messages matching '{query}' for user {user_id}"
            )
            return messages
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            raise


# Global chat service instance
chat_service = ChatService()
