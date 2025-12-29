from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
from dotenv import load_dotenv
import os
import logging
load_dotenv()
logging.basicConfig(level=logging.INFO)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "Know_your_pay")  # fallback name

if not MONGO_URI:
    raise RuntimeError("❌ MONGO_URI environment variable is not set")

@asynccontextmanager
async def mongo_lifespan(app: FastAPI):
    # Startup
    app.state.mongo_client = AsyncIOMotorClient(MONGO_URI)
    app.state.db = app.state.mongo_client[DB_NAME]
    logging.info("✅ Connected to MongoDB")

    yield  # app runs here

    # Shutdown
    app.state.mongo_client.close()
    logging.info("🛑 MongoDB connection closed")
