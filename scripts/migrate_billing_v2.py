"""Migration script: billing v1 (credits) -> v2 (free/purchased tokens).

Idempotent: safe to run multiple times.

Usage:
    MONGO_URI=mongodb://... python -m scripts.migrate_billing_v2
"""

import asyncio
from datetime import datetime, timezone

from beanie import init_beanie
from motor import motor_asyncio

from src.config import settings
from src.dto import UserCredits


async def migrate():
    client = motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(database=client["user_settings"], document_models=[UserCredits])

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    collection = UserCredits.get_motor_collection()

    # Find all documents that still have the old 'credits' field
    cursor = collection.find({"credits": {"$exists": True}})
    migrated = 0
    skipped = 0

    async for doc in cursor:
        old_credits = doc.get("credits", 0)

        # Skip if already migrated (has purchased_credits field with value)
        if "purchased_credits" in doc and doc.get("free_credits_month", ""):
            skipped += 1
            continue

        update = {
            "$set": {
                "purchased_credits": old_credits,
                "free_credits": settings.free_monthly_tokens,
                "free_credits_month": current_month,
                "total_tokens_used": doc.get("total_credits_spent", 0),
            },
            "$unset": {"credits": ""},
        }
        await collection.update_one({"_id": doc["_id"]}, update)
        migrated += 1

    print(f"Migration complete. Migrated: {migrated}, Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(migrate())
