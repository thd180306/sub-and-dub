import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "videodub_db")

try:
    # Use certifi for TLS verification which is required by MongoDB Atlas
    if "+srv" in MONGO_URI:
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    else:
        client = MongoClient(MONGO_URI)
        
    db = client[DB_NAME]
    
    # Define collections
    users_collection = db["users"]
    licenses_collection = db["licenses"]
    
    # Create indexes for performance and uniqueness
    users_collection.create_index("email", unique=True)
    licenses_collection.create_index("license_key", unique=True)
    
    print(f"[OK] Da ket noi thanh cong toi MongoDB: {DB_NAME}")
except Exception as e:
    print(f"[ERROR] Loi ket noi MongoDB (Chua bat DB hoac sai URL): {e}")
