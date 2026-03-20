from db.neon_db import get_pool


async def get_cached_resume(resume_url):
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT resume_text, embedding
            FROM resume_cache
            WHERE resume_url = $1
            """,
            resume_url
        )

        if row:
            return {
                "resume_text": row["resume_text"],
                "embedding": row["embedding"]
            }

    return None


async def store_resume_cache(resume_url, resume_text, embedding):
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO resume_cache(resume_url, resume_text, embedding)
            VALUES($1, $2, $3)
            ON CONFLICT (resume_url) DO NOTHING
            """,
            resume_url,
            resume_text,
            embedding
        )