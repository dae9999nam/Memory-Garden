import os, sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from mongo import ElderDB

def seed_database(collection):
    sample_data = [
        {
            "user_id": "001",
            "role": "elderly",
            "interests": ["tech", "social"],
            "location": "Sham Shui Po",
            "participation_score": 12
        },
        {
            "user_id": "002",
            "role": "youth",
            "interests": ["tech", "helping", "community"],
            "location": "Sham Shui Po",
            "participation_score": 5
        },
        {
            "user_id": "003",
            "role": "elderly",
            "interests": ["games", "social"],
            "location": "Tuen Mun",
            "participation_score": 8
        },
        {
            "user_id" : "004",
            "role" : "youth",
            "interests" : ["strength", "weight-lifting"],
            "location" : "Central",
            "participation_score" : 2
        }
    ]
    collection.insert_many(sample_data)
    print("✅ Sample data seeded successfully!")

def delete_database(collection):
    collection.delete_many({})
    print("Data deleted successfully.")

if __name__ == "__main__":
    db = ElderDB()
    collection = db.connect_collection(db_name = "community_platform", 
                                       collection_name = "users")
    collection.create_index("user_id", unique = True)
    collection.create_index("location")
    collection.create_index("interests")
    
    seed_database(collection)
    db.close_connection()
   