from typing import Optional, Dict, Any
from mongodb_config import get_mongodb_database
from passlib.context import CryptContext
from datetime import datetime
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for managing users in MongoDB"""

    def __init__(self):
        self._users_collection = None

    @property
    def users_collection(self):
        """Get users collection (lazy initialization)"""
        if self._users_collection is None:
            db = get_mongodb_database()
            if db is not None:
                self._users_collection = db.users
                # Create unique index on email
                try:
                    self._users_collection.create_index("email", unique=True)
                except Exception:
                    pass  # Index might already exist
        return self._users_collection

    def create_user(self, email: str, password: str) -> Dict[str, Any]:
        """Create a new user"""
        if self.users_collection is None:
            raise Exception("MongoDB is not available")

        # Check if user already exists
        existing_user = self.users_collection.find_one({"email": email})
        if existing_user:
            raise ValueError("User with this email already exists")

        # Hash password and create user document
        hashed_password = pwd_context.hash(password)
        user_doc = {
            "email": email,
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = self.users_collection.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        user_doc["id"] = str(result.inserted_id)  # For compatibility

        logger.info(f"Created user: {email}")
        return user_doc

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        if self.users_collection is None:
            return None

        user = self.users_collection.find_one({"email": email})
        if user:
            user["_id"] = str(user["_id"])
            user["id"] = str(user["_id"])  # For compatibility
        return user

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if self.users_collection is None:
            return None

        try:
            user = self.users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                user["id"] = str(user["_id"])  # For compatibility
            return user
        except Exception:
            return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user = self.get_user_by_email(email)
        if not user:
            return None

        if not self.verify_password(password, user["hashed_password"]):
            return None

        return user


# Global user service instance
user_service = UserService()