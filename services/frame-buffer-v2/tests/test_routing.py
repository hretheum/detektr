"""Tests for smart routing algorithms."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.models import FrameReadyEvent
from src.routing.algorithms import AffinityRouter, LoadBalancedRouter, SmartRouter


@pytest.mark.asyncio
async def test_affinity_routing():
    """Test camera affinity routing."""
    router = SmartRouter(strategy="affinity")

    # Register processors
    processors = {
        "proc1": {
            "capabilities": ["face_detection"],
            "assigned_cameras": ["cam1", "cam2"],
        },
        "proc2": {
            "capabilities": ["face_detection"],
            "assigned_cameras": ["cam3", "cam4"],
        },
        "proc3": {
            "capabilities": ["face_detection"],
            "assigned_cameras": [],
        },  # Fallback
    }

    for proc_id, info in processors.items():
        await router.register_processor(proc_id, info)

    # Test routing by camera affinity
    frame_cam1 = FrameReadyEvent(
        frame_id="f1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        metadata={"detection_type": "face_detection"},
    )

    proc = await router.route_frame(frame_cam1)
    assert proc == "proc1"  # Should route to proc1 (has cam1)

    # Test fallback for unknown camera
    frame_cam5 = FrameReadyEvent(
        frame_id="f2",
        camera_id="cam5",  # Unknown camera
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        metadata={"detection_type": "face_detection"},
    )

    proc = await router.route_frame(frame_cam5)
    assert proc == "proc3"  # Should route to fallback processor


@pytest.mark.asyncio
async def test_load_balanced_routing():
    """Test load-balanced routing."""
    router = SmartRouter(strategy="load_balanced")

    # Mock load stats
    load_stats = {
        "proc1": {"current_load": 20, "capacity": 100},  # 20% load
        "proc2": {"current_load": 80, "capacity": 100},  # 80% load
        "proc3": {"current_load": 50, "capacity": 100},  # 50% load
    }

    with patch.object(router, "get_processor_loads", return_value=load_stats):
        # Register processors
        for proc_id in load_stats:
            await router.register_processor(
                proc_id, {"capabilities": ["object_detection"]}
            )

        # Route multiple frames
        frames_routed = {"proc1": 0, "proc2": 0, "proc3": 0}

        for i in range(100):
            frame = FrameReadyEvent(
                frame_id=f"f{i}",
                camera_id="cam1",
                timestamp=datetime.now(),
                size_bytes=1024,
                width=1920,
                height=1080,
                format="jpeg",
                metadata={"detection_type": "object_detection"},
            )

            proc = await router.route_frame(frame)
            frames_routed[proc] += 1

        # proc1 (least loaded) should get most frames
        assert frames_routed["proc1"] > frames_routed["proc3"]
        assert frames_routed["proc3"] > frames_routed["proc2"]


@pytest.mark.asyncio
async def test_capability_filtering():
    """Test routing based on processor capabilities."""
    router = SmartRouter(strategy="capability_aware")

    # Register processors with different capabilities
    await router.register_processor(
        "face_proc", {"capabilities": ["face_detection", "face_recognition"]}
    )
    await router.register_processor(
        "object_proc", {"capabilities": ["object_detection", "tracking"]}
    )
    await router.register_processor(
        "multi_proc",
        {"capabilities": ["face_detection", "object_detection", "motion_detection"]},
    )

    # Test face detection routing
    face_frame = FrameReadyEvent(
        frame_id="face1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        metadata={"detection_type": "face_detection"},
    )

    possible_procs = await router.get_capable_processors(face_frame)
    assert "face_proc" in possible_procs
    assert "multi_proc" in possible_procs
    assert "object_proc" not in possible_procs


@pytest.mark.asyncio
async def test_priority_based_routing():
    """Test priority-aware routing."""
    router = SmartRouter(strategy="priority_aware")

    # Register processors
    await router.register_processor(
        "high_prio_proc", {"capabilities": ["critical_detection"], "priority": 10}
    )
    await router.register_processor(
        "normal_proc", {"capabilities": ["critical_detection"], "priority": 5}
    )

    # High priority frame
    critical_frame = FrameReadyEvent(
        frame_id="critical1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        priority=10,  # High priority
        metadata={"detection_type": "critical_detection"},
    )

    proc = await router.route_frame(critical_frame)
    assert proc == "high_prio_proc"  # Should route to high priority processor


@pytest.mark.asyncio
async def test_adaptive_routing():
    """Test adaptive routing based on performance history."""
    router = SmartRouter(strategy="adaptive")

    # Register processors
    processors = ["proc1", "proc2", "proc3"]
    for proc in processors:
        await router.register_processor(proc, {"capabilities": ["detection"]})

    # Simulate performance history
    # proc1 has best recent performance
    router.performance_history = {
        "proc1": {"avg_latency": 50, "success_rate": 0.99},
        "proc2": {"avg_latency": 100, "success_rate": 0.95},
        "proc3": {"avg_latency": 75, "success_rate": 0.90},
    }

    # Route frame
    frame = FrameReadyEvent(
        frame_id="f1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        metadata={"detection_type": "detection"},
    )

    # Should prefer proc1 due to best performance
    routed_counts = {"proc1": 0, "proc2": 0, "proc3": 0}
    for _ in range(100):
        proc = await router.route_frame(frame)
        routed_counts[proc] += 1

    assert routed_counts["proc1"] > routed_counts["proc2"]
    assert routed_counts["proc1"] > routed_counts["proc3"]


@pytest.mark.asyncio
async def test_round_robin_fallback():
    """Test round-robin fallback when no smart routing criteria."""
    router = SmartRouter(strategy="round_robin")

    # Register processors
    processors = ["proc1", "proc2", "proc3"]
    for proc in processors:
        await router.register_processor(proc, {"capabilities": ["detection"]})

    # Route frames
    routed = []
    for i in range(9):
        frame = FrameReadyEvent(
            frame_id=f"f{i}",
            camera_id="cam1",
            timestamp=datetime.now(),
            size_bytes=1024,
            width=1920,
            height=1080,
            format="jpeg",
            metadata={"detection_type": "detection"},
        )
        proc = await router.route_frame(frame)
        routed.append(proc)

    # Should distribute evenly
    assert routed.count("proc1") == 3
    assert routed.count("proc2") == 3
    assert routed.count("proc3") == 3


@pytest.mark.asyncio
async def test_routing_with_processor_failure():
    """Test routing handles processor failures gracefully."""
    router = SmartRouter(strategy="load_balanced")

    # Register processors
    processors = ["proc1", "proc2", "proc3"]
    for proc in processors:
        await router.register_processor(proc, {"capabilities": ["detection"]})

    # Mark proc1 as failed
    router.mark_processor_failed("proc1")

    # Route frame - should not route to failed processor
    frame = FrameReadyEvent(
        frame_id="f1",
        camera_id="cam1",
        timestamp=datetime.now(),
        size_bytes=1024,
        width=1920,
        height=1080,
        format="jpeg",
        metadata={"detection_type": "detection"},
    )

    routed_procs = set()
    for _ in range(10):
        proc = await router.route_frame(frame)
        routed_procs.add(proc)

    assert "proc1" not in routed_procs
    assert "proc2" in routed_procs
    assert "proc3" in routed_procs
