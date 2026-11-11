import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load variables from the .env file
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

# Create the MongoDB client
client = AsyncIOMotorClient(MONGODB_URI)

# Select your database (MongoDB creates it automatically when you insert data)
database = client["oauth_app"]

# Select your collection for storing users
users_collection = database["users"]
