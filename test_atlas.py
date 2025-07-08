import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def test_atlas_connection():
    try:
        # Get connection string from environment
        mongodb_url = os.getenv("MONGODB_URL")
        database_name = os.getenv("MONGODB_DATABASE", "easydo_chat")
        
        print(f"Testing connection to: {mongodb_url[:50]}...")
        
        # Create client with timeout
        client = MongoClient(
            mongodb_url,
            serverSelectionTimeoutMS=10000,  # 10 second timeout
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        # Test connection
        print("Testing ping...")
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        # Test database operations
        db = client[database_name]
        collection = db.test_collection
        
        # Insert a test document
        test_doc = {"test": "Hello Atlas!", "timestamp": "2024-01-01"}
        result = collection.insert_one(test_doc)
        print(f"✅ Inserted test document with ID: {result.inserted_id}")
        
        # Read it back
        found_doc = collection.find_one({"_id": result.inserted_id})
        print(f"✅ Retrieved document: {found_doc}")
        
        # Clean up
        collection.delete_one({"_id": result.inserted_id})
        print("✅ Cleaned up test document")
        
        client.close()
        print("✅ All tests passed! Atlas connection is working.")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your connection string in .env")
        print("2. Verify your username/password")
        print("3. Check Network Access settings in Atlas")
        print("4. Make sure your cluster is running")

if __name__ == "__main__":
    test_atlas_connection() 