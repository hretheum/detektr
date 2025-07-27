import asyncio

import redis.asyncio as aioredis


async def test_redis():
    """Test Redis connection."""
    # Try different connection methods
    for url in [
        "redis://localhost:6379",
        "redis://127.0.0.1:6379",
        "redis://host.docker.internal:6379",
    ]:
        try:
            print(f"Trying {url}...")
            client = aioredis.from_url(url)
            result = await client.ping()
            print(f"Success with {url}: {result}")
            await client.close()
            return
        except Exception as e:
            print(f"Failed {url}: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(test_redis())
