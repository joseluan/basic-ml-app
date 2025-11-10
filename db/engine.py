import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

def get_mongo_collection(collection_name: str):
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    # TODO: Retirar esse if depois, para nao ficar verificando sempre
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
    
    return db[collection_name]


if __name__ == "__main__":
    ENV = os.getenv("ENV", "prod").lower()
    collection = get_mongo_collection(f"{ENV.upper()}_intent_logs")
