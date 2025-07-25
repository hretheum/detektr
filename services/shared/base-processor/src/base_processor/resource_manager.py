"""Resource management for GPU/CPU allocation."""
import asyncio
import os
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import psutil

from .exceptions import ResourceError


@dataclass
class ResourceStats:
    """Resource usage statistics."""

    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    gpu_memory_used_mb: Optional[float] = None
    gpu_utilization: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceAllocation:
    """Resource allocation for a processing task."""

    allocation_id: str
    cpu_cores: Optional[Set[int]] = None
    memory_limit_mb: Optional[float] = None
    gpu_device_id: Optional[int] = None
    gpu_memory_limit_mb: Optional[float] = None
    allocated_at: datetime = field(default_factory=datetime.now)
    released_at: Optional[datetime] = None


class ResourceManager:
    """Manages CPU, memory, and GPU resources."""

    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 80.0,
        gpu_devices: Optional[List[int]] = None,
        max_gpu_memory_percent: float = 80.0,
    ):
        """Initialize resource manager.

        Args:
            max_cpu_percent: Maximum CPU usage allowed
            max_memory_percent: Maximum memory usage allowed
            gpu_devices: List of GPU device IDs to manage
            max_gpu_memory_percent: Maximum GPU memory usage allowed
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_gpu_memory_percent = max_gpu_memory_percent

        # Resource limits
        self.total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
        self.cpu_count = psutil.cpu_count()

        # GPU management
        self.gpu_devices = gpu_devices or []
        self._gpu_available = self._check_gpu_availability()
        self.gpu_memory_total = (
            self._get_gpu_memory_total() if self._gpu_available else {}
        )

        # Active allocations
        self._allocations: Dict[str, ResourceAllocation] = {}
        self._cpu_semaphore = asyncio.Semaphore(self.cpu_count)
        self._memory_lock = asyncio.Lock()
        self._gpu_locks = {gpu_id: asyncio.Lock() for gpu_id in self.gpu_devices}

        # Resource tracking
        self._allocated_memory_mb = 0.0
        self._allocated_cpus: Set[int] = set()
        self._allocated_gpu_memory: Dict[int, float] = {
            gpu_id: 0.0 for gpu_id in self.gpu_devices
        }

    def _check_gpu_availability(self) -> bool:
        """Check if GPU support is available."""
        try:
            import pynvml

            pynvml.nvmlInit()
            return True
        except (ImportError, Exception):
            return False

    def _get_gpu_memory_total(self) -> Dict[int, float]:
        """Get total GPU memory for each device."""
        if not self._gpu_available:
            return {}

        try:
            import pynvml

            memory_total = {}
            for gpu_id in self.gpu_devices:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_total[gpu_id] = info.total / (1024 * 1024)  # Convert to MB
            return memory_total
        except Exception:
            return {}

    async def get_current_stats(self) -> ResourceStats:
        """Get current resource usage statistics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        stats = ResourceStats(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
        )

        # Add GPU stats if available
        if self._gpu_available and self.gpu_devices:
            try:
                import pynvml

                # Use first GPU for overall stats
                handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_devices[0])
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)

                stats.gpu_memory_used_mb = mem_info.used / (1024 * 1024)
                stats.gpu_utilization = util_info.gpu
            except Exception:
                pass

        return stats

    async def check_resources_available(
        self,
        cpu_cores: Optional[int] = None,
        memory_mb: Optional[float] = None,
        gpu_required: bool = False,
    ) -> bool:
        """Check if requested resources are available.

        Args:
            cpu_cores: Number of CPU cores needed
            memory_mb: Memory required in MB
            gpu_required: Whether GPU is required

        Returns:
            True if resources are available
        """
        stats = await self.get_current_stats()

        # Check CPU
        if cpu_cores:
            available_cores = self.cpu_count - len(self._allocated_cpus)
            if available_cores < cpu_cores:
                return False

            if stats.cpu_percent > self.max_cpu_percent:
                return False

        # Check memory
        if memory_mb:
            available_memory = (
                self.total_memory_mb * (self.max_memory_percent / 100)
            ) - self._allocated_memory_mb
            if available_memory < memory_mb:
                return False

        # Check GPU
        if gpu_required and not self._gpu_available:
            return False

        return True

    @asynccontextmanager
    async def allocate_resources(
        self,
        allocation_id: str,
        cpu_cores: Optional[int] = None,
        memory_mb: Optional[float] = None,
        prefer_gpu: bool = False,
        gpu_memory_mb: Optional[float] = None,
    ):
        """Allocate resources for processing.

        Args:
            allocation_id: Unique allocation identifier
            cpu_cores: Number of CPU cores to allocate
            memory_mb: Memory to allocate in MB
            prefer_gpu: Whether to prefer GPU allocation
            gpu_memory_mb: GPU memory to allocate in MB

        Yields:
            ResourceAllocation object
        """
        allocation = ResourceAllocation(allocation_id=allocation_id)

        try:
            # Allocate CPU cores
            if cpu_cores:
                async with self._memory_lock:
                    # Find available CPU cores
                    available_cores = set(range(self.cpu_count)) - self._allocated_cpus
                    if len(available_cores) < cpu_cores:
                        raise ResourceError("Insufficient CPU cores available")

                    # Allocate cores
                    allocation.cpu_cores = set(list(available_cores)[:cpu_cores])
                    self._allocated_cpus.update(allocation.cpu_cores)

                    # Set CPU affinity if supported
                    if hasattr(os, "sched_setaffinity"):
                        try:
                            os.sched_setaffinity(0, allocation.cpu_cores)
                        except Exception:
                            pass

            # Allocate memory
            if memory_mb:
                async with self._memory_lock:
                    available_memory = (
                        self.total_memory_mb * (self.max_memory_percent / 100)
                    ) - self._allocated_memory_mb
                    if available_memory < memory_mb:
                        raise ResourceError("Insufficient memory available")

                    allocation.memory_limit_mb = memory_mb
                    self._allocated_memory_mb += memory_mb

            # Allocate GPU if requested and available
            if prefer_gpu and self._gpu_available and self.gpu_devices:
                # Find available GPU
                gpu_allocated = False
                for gpu_id in self.gpu_devices:
                    if not self._gpu_locks[gpu_id].locked():
                        async with self._gpu_locks[gpu_id]:
                            # Check GPU memory
                            if gpu_memory_mb:
                                available_gpu_mem = (
                                    self.gpu_memory_total[gpu_id]
                                    * (self.max_gpu_memory_percent / 100)
                                    - self._allocated_gpu_memory[gpu_id]
                                )
                                if available_gpu_mem >= gpu_memory_mb:
                                    allocation.gpu_device_id = gpu_id
                                    allocation.gpu_memory_limit_mb = gpu_memory_mb
                                    self._allocated_gpu_memory[gpu_id] += gpu_memory_mb
                                    gpu_allocated = True
                                    break
                            else:
                                allocation.gpu_device_id = gpu_id
                                gpu_allocated = True
                                break

                if prefer_gpu and not gpu_allocated:
                    raise ResourceError("No GPU available")

            # Store allocation
            self._allocations[allocation_id] = allocation

            # Set environment variable for GPU
            if allocation.gpu_device_id is not None:
                os.environ["CUDA_VISIBLE_DEVICES"] = str(allocation.gpu_device_id)

            yield allocation

        finally:
            # Release resources
            await self.release_resources(allocation_id)

    async def release_resources(self, allocation_id: str):
        """Release allocated resources.

        Args:
            allocation_id: Allocation identifier
        """
        if allocation_id not in self._allocations:
            return

        allocation = self._allocations[allocation_id]

        async with self._memory_lock:
            # Release CPU cores
            if allocation.cpu_cores:
                self._allocated_cpus -= allocation.cpu_cores

            # Release memory
            if allocation.memory_limit_mb:
                self._allocated_memory_mb -= allocation.memory_limit_mb

            # Release GPU memory
            if allocation.gpu_device_id is not None and allocation.gpu_memory_limit_mb:
                self._allocated_gpu_memory[
                    allocation.gpu_device_id
                ] -= allocation.gpu_memory_limit_mb

        # Mark as released
        allocation.released_at = datetime.now()

        # Remove from active allocations
        del self._allocations[allocation_id]

    def get_allocation_stats(self) -> Dict[str, Any]:
        """Get current allocation statistics."""
        return {
            "active_allocations": len(self._allocations),
            "allocated_cpus": len(self._allocated_cpus),
            "allocated_memory_mb": self._allocated_memory_mb,
            "allocated_gpu_memory_mb": dict(self._allocated_gpu_memory),
            "available_cpus": self.cpu_count - len(self._allocated_cpus),
            "available_memory_mb": (
                self.total_memory_mb * (self.max_memory_percent / 100)
            )
            - self._allocated_memory_mb,
        }

    async def wait_for_resources(
        self,
        cpu_cores: Optional[int] = None,
        memory_mb: Optional[float] = None,
        gpu_required: bool = False,
        timeout: Optional[float] = None,
    ) -> bool:
        """Wait for resources to become available.

        Args:
            cpu_cores: Number of CPU cores needed
            memory_mb: Memory required in MB
            gpu_required: Whether GPU is required
            timeout: Maximum time to wait in seconds

        Returns:
            True if resources became available
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            if await self.check_resources_available(cpu_cores, memory_mb, gpu_required):
                return True

            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                return False

            await asyncio.sleep(0.5)


class ResourceManagerMixin:
    """Mixin to add resource management to processors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Extract resource configuration
        self.cpu_cores = kwargs.get("cpu_cores", 1)
        self.memory_limit_mb = kwargs.get("memory_limit_mb", 512)
        self.prefer_gpu = kwargs.get("prefer_gpu", False)
        self.gpu_memory_mb = kwargs.get("gpu_memory_mb", 1024)

        # Create resource manager
        self.resource_manager = ResourceManager(
            gpu_devices=kwargs.get("gpu_devices", [])
        )

    @asynccontextmanager
    async def with_resources(self, frame_id: str):
        """Context manager for resource allocation."""
        async with self.resource_manager.allocate_resources(
            allocation_id=f"{self.name}_{frame_id}",
            cpu_cores=self.cpu_cores,
            memory_mb=self.memory_limit_mb,
            prefer_gpu=self.prefer_gpu,
            gpu_memory_mb=self.gpu_memory_mb if self.prefer_gpu else None,
        ) as allocation:
            # Log allocation
            self.log_with_context(
                "info",
                "Resources allocated",
                frame_id=frame_id,
                cpu_cores=len(allocation.cpu_cores) if allocation.cpu_cores else 0,
                memory_mb=allocation.memory_limit_mb,
                gpu_device=allocation.gpu_device_id,
            )

            yield allocation

            # Log release
            self.log_with_context("info", "Resources released", frame_id=frame_id)
