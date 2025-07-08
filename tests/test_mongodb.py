import pytest
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def mongodb_client():
    """Create MongoDB client for testing"""
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        pytest.skip("MONGODB_URL not configured")

    client = MongoClient(
        mongodb_url,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
    )
    yield client
    client.close()


def test_mongodb_connection(mongodb_client):
    """Test MongoDB Atlas connection"""
    # Test ping
    result = mongodb_client.admin.command("ping")
    assert result["ok"] == 1


def test_mongodb_database_operations(mongodb_client):
    """Test basic database operations"""
    database_name = os.getenv("MONGODB_DATABASE", "easydo_test")
    db = mongodb_client[database_name]
    collection = db.test_collection

    # Insert test document
    test_doc = {"test": "Hello MongoDB!", "pytest": True}
    result = collection.insert_one(test_doc)
    assert result.inserted_id is not None

    # Read it back
    found_doc = collection.find_one({"_id": result.inserted_id})
    assert found_doc is not None
    assert found_doc["test"] == "Hello MongoDB!"
    assert found_doc["pytest"] is True

    # Clean up
    delete_result = collection.delete_one({"_id": result.inserted_id})
    assert delete_result.deleted_count == 1
