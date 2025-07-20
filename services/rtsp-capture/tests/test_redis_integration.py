"""
Test suite for Redis queue integration.

Tests cover:
- Frame publishing to Redis
- Low latency operations (<1ms)
- Connection resilience
- Message format compatibility
"""

import time

import numpy as np
import pytest
import redis

from src.frame_buffer import CircularFrameBuffer
from src.simple_redis_queue import SimpleRedisFrameQueue


class TestRedisIntegration:
    """Tests for Redis queue integration."""

    @pytest.fixture
    def redis_client(self):
        """Create Redis client for testing."""
        client = redis.Redis(
            host="127.0.0.1",
            port=6379,
            db=1,  # Use DB 1 for tests
            decode_responses=False,  # Keep bytes for compatibility
        )
        # Test connection
        client.ping()
        yield client
        # Cleanup
        client.flushdb()
        client.close()

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame."""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    def test_redis_connection(self, redis_client):
        """Test basic Redis connection."""
        # Ping test
        pong = redis_client.ping()
        assert pong is True

        # Set/get test
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        assert value == b"test_value"

    def test_frame_metadata_publish(self, redis_client, sample_frame):
        """Test publishing frame metadata to Redis queue."""
        queue = SimpleRedisFrameQueue(redis_client, stream_key="test:frames")

        # Create frame metadata
        frame_id = "frame_001"
        timestamp = time.time()
        metadata = {
            "frame_id": frame_id,
            "timestamp": timestamp,
            "width": sample_frame.shape[1],
            "height": sample_frame.shape[0],
            "channels": sample_frame.shape[2],
            "camera_id": "camera_01",
            "sequence_number": 1,
        }

        # Publish to Redis
        message_id = queue.publish(metadata)
        assert message_id is not None

        # Verify message in stream
        messages = redis_client.xread({queue.stream_key: 0}, count=1)
        assert len(messages) == 1
        assert messages[0][0] == queue.stream_key.encode()
        assert len(messages[0][1]) == 1

        # Verify message content
        msg_id, msg_data = messages[0][1][0]
        assert (
            msg_id == message_id.encode()
            if isinstance(message_id, str)
            else msg_id == message_id
        )
        for key, value in metadata.items():
            if isinstance(value, (int, float)):
                assert msg_data[key.encode()] == str(value).encode()
            else:
                assert msg_data[key.encode()] == value.encode()

    def test_frame_publish_latency(self, redis_client, sample_frame):
        """Test that frame publishing meets <1ms latency requirement."""
        queue = SimpleRedisFrameQueue(redis_client, stream_key="test:frames:latency")

        # Warm up connection
        queue.publish({"warmup": "true"})

        # Measure latency over multiple operations
        latencies = []
        for i in range(100):
            metadata = {
                "frame_id": f"frame_{i:04d}",
                "timestamp": time.time(),
                "sequence": i,
            }

            start = time.perf_counter()
            queue.publish(metadata)
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        print("\nRedis publish latency stats:")
        print(f"  Average: {avg_latency:.3f} ms")
        print(f"  Max: {max_latency:.3f} ms")
        print(f"  P99: {p99_latency:.3f} ms")

        # Verify <1ms requirement
        assert (
            avg_latency < 1.0
        ), f"Average latency {avg_latency:.3f}ms exceeds 1ms requirement"
        assert p99_latency < 2.0, f"P99 latency {p99_latency:.3f}ms too high"

    def test_consumer_groups(self, redis_client):
        """Test Redis consumer groups for multiple consumers."""
        queue = SimpleRedisFrameQueue(redis_client, stream_key="test:frames:groups")

        # Create consumer group
        queue.create_consumer_group("processors", "0")

        # Publish messages
        message_ids = []
        for i in range(10):
            msg_id = queue.publish({"frame_id": f"frame_{i}", "index": i})
            message_ids.append(msg_id)

        # Consume from group
        consumer1_messages = queue.read_as_consumer("processors", "consumer1", count=5)
        consumer2_messages = queue.read_as_consumer("processors", "consumer2", count=5)

        # Verify distribution
        assert len(consumer1_messages) == 5
        assert len(consumer2_messages) == 5

        # Verify no duplicate processing
        consumer1_ids = {msg[0] for msg in consumer1_messages}
        consumer2_ids = {msg[0] for msg in consumer2_messages}
        assert len(consumer1_ids & consumer2_ids) == 0  # No overlap

    def test_frame_buffer_redis_integration(self, redis_client, sample_frame):
        """Test CircularFrameBuffer integration with Redis queue."""
        buffer = CircularFrameBuffer(capacity=10)
        queue = SimpleRedisFrameQueue(
            redis_client, stream_key="test:buffer:integration"
        )

        # Simulate frame capture and buffering
        frame_ids = []
        for i in range(15):  # More than buffer capacity
            frame_id = f"frame_{i:04d}"
            frame_ids.append(frame_id)
            timestamp = time.time()

            # Add to buffer
            buffer.put(frame_id, sample_frame, timestamp)

            # Publish metadata to Redis
            metadata = {
                "frame_id": frame_id,
                "timestamp": timestamp,
                "buffer_size": buffer.size,
                "dropped_frames": buffer.get_statistics()["total_frames_dropped"],
            }
            queue.publish(metadata)

        # Verify buffer state
        stats = buffer.get_statistics()
        assert stats["total_frames_added"] == 15
        assert stats["total_frames_dropped"] == 5
        assert stats["current_size"] == 10

        # Verify Redis messages
        messages = redis_client.xrange(queue.stream_key)
        assert len(messages) == 15

        # Check metadata consistency
        last_msg = messages[-1]
        last_metadata = {k.decode(): v.decode() for k, v in last_msg[1].items()}
        assert last_metadata["frame_id"] == "frame_0014"
        assert last_metadata["buffer_size"] == "10"
        assert last_metadata["dropped_frames"] == "5"

    def test_connection_resilience(self, redis_client):
        """Test resilience to connection issues."""
        queue = SimpleRedisFrameQueue(redis_client, stream_key="test:resilience")

        # Test that queue works after connection reset
        queue.publish({"test": "before"})

        # Force connection reset
        redis_client.connection_pool.disconnect()

        # Should work again (connection pool auto-reconnects)
        queue.publish({"test": "after"})

        # Verify messages were stored
        messages = redis_client.xrange(queue.stream_key)
        assert len(messages) == 2

    def test_stream_trimming(self, redis_client):
        """Test automatic stream trimming to prevent memory growth."""
        queue = SimpleRedisFrameQueue(
            redis_client,
            stream_key="test:trimming",
            max_len=1000,  # Keep only last 1000 messages
        )

        # Publish many messages
        for i in range(1500):
            queue.publish({"frame_id": f"frame_{i}", "index": i})

        # Check stream length
        stream_info = queue.get_stream_info()
        assert stream_info["length"] <= 1000

    def test_batch_operations(self, redis_client):
        """Test batch publishing for efficiency."""
        queue = SimpleRedisFrameQueue(redis_client, stream_key="test:batch")

        # Prepare batch of messages
        batch = []
        for i in range(100):
            batch.append(
                {
                    "frame_id": f"frame_{i:04d}",
                    "timestamp": time.time(),
                    "batch_index": i,
                }
            )

        # Measure batch publish time
        start = time.perf_counter()
        message_ids = queue.publish_batch(batch)
        end = time.perf_counter()

        batch_time_ms = (end - start) * 1000
        per_message_ms = batch_time_ms / len(batch)

        print("\nBatch publish performance:")
        print(f"  Total time: {batch_time_ms:.3f} ms")
        print(f"  Per message: {per_message_ms:.3f} ms")

        assert len(message_ids) == 100
        assert per_message_ms < 0.1  # Should be much faster than individual publishes


@pytest.mark.parametrize("message_size", [100, 1000, 10000])
def test_message_size_impact(message_size):
    """Test impact of message size on latency."""
    client = redis.Redis(host="localhost", port=6379, db=1, decode_responses=False)

    try:
        queue = SimpleRedisFrameQueue(client, stream_key=f"test:size:{message_size}")

        # Create message of specified size
        metadata = {
            "frame_id": "test_frame",
            "data": "x" * message_size,  # Dummy data
            "size": message_size,
        }

        # Measure latency
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            queue.publish(metadata)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nMessage size {message_size}B: avg latency {avg_latency:.3f} ms")

        # Even large messages should be under 5ms
        assert avg_latency < 5.0

    finally:
        client.flushdb()
        client.close()
