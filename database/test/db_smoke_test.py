import os
import asyncio
from dotenv import load_dotenv
import libsql_client

load_dotenv()

DB_URL = (os.getenv("DATABASE_URL") or "").strip()
TOKEN = (os.getenv("TURSO_AUTH_TOKEN") or "").strip() or None
if not DB_URL:
    raise RuntimeError("DATABASE_URL is required for db_smoke_test.py")


async def main():
    kwargs = {"auth_token": TOKEN} if TOKEN else {}
    client = libsql_client.create_client(DB_URL, **kwargs)
    try:
        rs = await client.execute("select 1")
        print(rs.rows)
    finally:
        # important on Windows to avoid aiohttp warnings
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
