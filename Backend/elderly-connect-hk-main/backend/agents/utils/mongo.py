import pymongo
from dotenv import load_dotenv
import os
from typing import Any, Dict, List

# Initializing the connection of MongoDB

class ElderDB:
    """Database utility class for MongoDB used in Elderly-Connect Project"""
    def __init__(self):
        load_dotenv()
        self.uri = os.getenv("MONGO_URI")
        # Instantiate connnection to Bakend DB
        try:
            self.client = pymongo.MongoClient(self.uri)
            print(f"Conected to ElderDB at {self.uri}")
        except Exception as e:
            print("Failed to connect to ElderDB : {e}")
    
    def connect_collection(self, db_name: str = None, collection_name: str = None):
        """Connects to MongoDB and returns the specified collection"""
        try:
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            print("Successfully connected to {db_name}'s {collection_name} collection!")
            return self.collection
        except Exception as e:
            print(f"Please check the db name or collection name again: {e}")
            return None
    
    # Connection Cleanup
    def close_connection(self):
        """Close ElderDB connection"""
        self.client.close()
        print("MongoDB Connection Closed.")


    

    
    
    

    






        



