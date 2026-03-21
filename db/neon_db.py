import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()   # 🔥 THIS IS THE MISSING PIECE
#
# DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None


async def get_pool():
    global _pool

    if _pool is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not set")

        print("DATABASE_URL:", DATABASE_URL)  # debug once

        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10
        )

    return _pool