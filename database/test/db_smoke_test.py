import os
import asyncio
from dotenv import load_dotenv
import libsql_client

load_dotenv()

DB_URL = os.environ["TURSO_DATABASE_URL"]
TOKEN = os.environ["TURSO_AUTH_TOKEN"]


async def main():
    client = libsql_client.create_client(DB_URL, auth_token=TOKEN)
    try:
        rs = await client.execute("select 1")
        print(rs.rows)
    finally:
        # important on Windows to avoid aiohttp warnings
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
