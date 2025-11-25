from pymongo import MongoClient

try:
    client = MongoClient("mongodb://test:test123@localhost:27017/")
    client.admin.command("ping")
    print("MongoDB OK ✓")
except Exception as e:
    print("MongoDB ERROR:", e)
