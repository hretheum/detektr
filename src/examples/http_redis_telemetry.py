"""Example HTTP clients and Redis with OpenTelemetry instrumentation."""

import asyncio
import os
import sys
import time

import aiohttp
import redis
import requests

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.shared.telemetry import (  # noqa: E402
    setup_auto_instrumentation,
    setup_telemetry,
)

# Setup telemetry first
tracer, meter, _ = setup_telemetry("http-redis-example", "0.1.0")

# Enable auto-instrumentation
setup_auto_instrumentation()


def test_requests() -> None:
    """Test requests library instrumentation."""
    print("\n=== Testing requests instrumentation ===")

    with tracer.start_as_current_span("requests_test") as span:
        span.set_attribute("test.type", "http_client")

        # These requests will be auto-instrumented
        urls = [
            "https://httpbin.org/get",
            "https://httpbin.org/status/404",
            "https://httpbin.org/delay/1",
        ]

        for url in urls:
            try:
                print(f"Fetching: {url}")
                response = requests.get(url, timeout=5)
                print(f"Status: {response.status_code}")
            except Exception as e:
                print(f"Error: {e}")
                span.set_attribute("error", True)


async def test_aiohttp() -> None:
    """Test aiohttp client instrumentation."""
    print("\n=== Testing aiohttp instrumentation ===")

    with tracer.start_as_current_span("aiohttp_test") as span:
        span.set_attribute("test.type", "async_http_client")

        async with aiohttp.ClientSession() as session:
            # Parallel requests - all will be traced
            urls = [
                "https://httpbin.org/get",
                "https://httpbin.org/headers",
                "https://httpbin.org/user-agent",
            ]

            tasks = []
            for url in urls:
                tasks.append(fetch_url(session, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, result in zip(urls, results):
                if isinstance(result, Exception):
                    print(f"{url}: Error - {result}")
                else:
                    print(f"{url}: Status {result}")


async def fetch_url(session: aiohttp.ClientSession, url: str) -> int:
    """Fetch URL with aiohttp."""
    async with session.get(url) as response:
        await response.text()
        return response.status


def test_redis() -> None:
    """Test Redis instrumentation."""
    print("\n=== Testing Redis instrumentation ===")

    with tracer.start_as_current_span("redis_test") as span:
        span.set_attribute("test.type", "redis_operations")

        try:
            # Connect to Redis - this will be auto-instrumented
            r = redis.Redis(host="localhost", port=6379, decode_responses=True)

            # Test operations - all traced automatically
            operations = [
                ("SET", lambda: r.set("test_key", "test_value")),
                ("GET", lambda: r.get("test_key")),
                ("INCR", lambda: r.incr("counter")),
                ("LPUSH", lambda: r.lpush("test_list", "item1", "item2")),
                ("LRANGE", lambda: r.lrange("test_list", 0, -1)),
            ]

            for op_name, operation in operations:
                try:
                    result = operation()
                    print(f"{op_name}: {result}")
                except Exception as e:
                    print(f"{op_name}: Failed - {e}")

        except redis.ConnectionError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            print(f"Redis connection failed (expected if not running): {e}")


def test_nested_spans() -> None:
    """Test nested spans showing service communication."""
    print("\n=== Testing nested spans (service communication) ===")

    # Simulate a service handling a request
    with tracer.start_as_current_span("handle_user_request") as request_span:
        request_span.set_attribute("user.id", "user_123")
        request_span.set_attribute("request.type", "get_recommendations")

        # Fetch user data from cache
        with tracer.start_as_current_span("redis_get_user") as redis_span:
            redis_span.set_attribute("cache.key", "user:123")
            time.sleep(0.01)  # Simulate Redis latency

        # Fetch external data
        with tracer.start_as_current_span("fetch_external_data") as http_span:
            http_span.set_attribute("http.method", "GET")
            http_span.set_attribute("http.url", "https://api.example.com/data")
            time.sleep(0.05)  # Simulate HTTP latency

        # Process data
        with tracer.start_as_current_span("process_recommendations") as process_span:
            process_span.set_attribute("algorithm", "collaborative_filtering")
            time.sleep(0.02)  # Simulate processing

        # Store result in cache
        with tracer.start_as_current_span("redis_set_result") as cache_span:
            cache_span.set_attribute("cache.key", "recommendations:123")
            cache_span.set_attribute("cache.ttl", 3600)
            time.sleep(0.01)  # Simulate Redis latency

        print("Request processed with nested spans")


async def main() -> None:
    """Run all HTTP and Redis tests."""
    print("Starting HTTP clients and Redis telemetry examples...")
    print("Note: Redis operations will fail without Redis running")

    # Test synchronous HTTP client
    test_requests()

    # Test async HTTP client
    await test_aiohttp()

    # Test Redis
    test_redis()

    # Test nested spans
    test_nested_spans()

    print("\nHTTP and Redis tests completed!")
    print("Check traces in Jaeger (if exporter configured)")


if __name__ == "__main__":
    asyncio.run(main())
