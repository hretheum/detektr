"""Frame search utilities for finding and analyzing frame traces."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel, Field


class FrameTrace(BaseModel):
    """Model for frame trace data."""

    trace_id: str = Field(description="Trace ID")
    frame_id: str = Field(description="Frame ID")
    start_time: datetime = Field(description="Trace start time")
    duration_ms: float = Field(description="Total duration in milliseconds")
    services: List[str] = Field(default_factory=list, description="Services involved")
    span_count: int = Field(description="Number of spans in trace")
    has_errors: bool = Field(default=False, description="Whether trace contains errors")


class FrameSearchClient:
    """Client for searching frame traces in Jaeger."""

    def __init__(self, jaeger_url: str = "http://localhost:16686"):
        """
        Initialize search client.

        Args:
            jaeger_url: Base URL for Jaeger instance
        """
        self.jaeger_url = jaeger_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_by_frame_id(
        self, frame_id: str, limit: int = 10
    ) -> List[FrameTrace]:
        """
        Search for traces by frame ID.

        Args:
            frame_id: Frame ID to search for
            limit: Maximum number of traces to return

        Returns:
            List of matching frame traces
        """
        params = {
            "service": "rtsp-capture",
            "tags": f'{{"frame.id":"{frame_id}"}}',
            "limit": limit,
        }

        try:
            response = await self.client.get(
                f"{self.jaeger_url}/api/traces", params=params
            )
            response.raise_for_status()
            data = response.json()

            traces = []
            for trace_data in data.get("data", []):
                trace = self._parse_trace(trace_data)
                if trace:
                    traces.append(trace)

            return traces
        except Exception as e:
            print(f"Error searching traces: {e}")
            return []

    async def search_by_camera(
        self, camera_id: str, start_time: Optional[datetime] = None, hours: int = 1
    ) -> List[FrameTrace]:
        """
        Search for all frames from a specific camera.

        Args:
            camera_id: Camera ID to search for
            start_time: Start time for search (defaults to now - hours)
            hours: Number of hours to look back

        Returns:
            List of frame traces from camera
        """
        if not start_time:
            start_time = datetime.now() - timedelta(hours=hours)
        end_time = start_time + timedelta(hours=hours)

        params = {
            "service": "rtsp-capture",
            "tags": f'{{"camera.id":"{camera_id}"}}',
            "start": int(start_time.timestamp() * 1_000_000),
            "end": int(end_time.timestamp() * 1_000_000),
            "limit": 1000,
        }

        try:
            response = await self.client.get(
                f"{self.jaeger_url}/api/traces", params=params
            )
            response.raise_for_status()
            data = response.json()

            traces = []
            for trace_data in data.get("data", []):
                trace = self._parse_trace(trace_data)
                if trace:
                    traces.append(trace)

            return traces
        except Exception as e:
            print(f"Error searching camera traces: {e}")
            return []

    async def get_trace_details(self, trace_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific trace.

        Args:
            trace_id: Trace ID to fetch

        Returns:
            Detailed trace information or None
        """
        try:
            response = await self.client.get(f"{self.jaeger_url}/api/traces/{trace_id}")
            response.raise_for_status()
            data = response.json()
            traces = data.get("data", [])
            return traces[0] if traces else None
        except Exception as e:
            print(f"Error fetching trace details: {e}")
            return None

    def _parse_trace(self, trace_data: Dict) -> Optional[FrameTrace]:
        """Parse raw trace data into FrameTrace model."""
        try:
            spans = trace_data.get("spans", [])
            if not spans:
                return None

            # Find frame ID from tags
            frame_id = None
            for span in spans:
                for tag in span.get("tags", []):
                    if tag.get("key") == "frame.id":
                        frame_id = tag.get("value")
                        break
                if frame_id:
                    break

            if not frame_id:
                return None

            # Calculate trace metrics
            start_time = min(s.get("startTime", 0) for s in spans)
            end_time = max(s.get("startTime", 0) + s.get("duration", 0) for s in spans)
            duration_ms = (end_time - start_time) / 1000

            # Extract services
            services = list(
                {s.get("process", {}).get("serviceName", "unknown") for s in spans}
            )

            # Check for errors
            has_errors = any(
                tag.get("key") == "error" and tag.get("value")
                for span in spans
                for tag in span.get("tags", [])
            )

            return FrameTrace(
                trace_id=trace_data.get("traceID", ""),
                frame_id=frame_id,
                start_time=datetime.fromtimestamp(start_time / 1_000_000),
                duration_ms=duration_ms,
                services=services,
                span_count=len(spans),
                has_errors=has_errors,
            )
        except Exception as e:
            print(f"Error parsing trace: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def quick_search(frame_id: str, jaeger_url: str = "http://localhost:16686"):
    """
    Quick search function for frame traces.

    Args:
        frame_id: Frame ID to search for
        jaeger_url: Jaeger URL

    Returns:
        Search results summary
    """
    client = FrameSearchClient(jaeger_url)
    try:
        traces = await client.search_by_frame_id(frame_id)

        if not traces:
            return f"No traces found for frame {frame_id}"

        result = f"Found {len(traces)} traces for frame {frame_id}\n"
        for trace in traces[:5]:  # Show first 5
            result += f"\n- Trace {trace.trace_id[:8]}..."
            result += f"\n  Time: {trace.start_time.isoformat()}"
            result += f"\n  Duration: {trace.duration_ms:.2f}ms"
            result += f"\n  Services: {', '.join(trace.services)}"
            if trace.has_errors:
                result += "\n  ⚠️  Contains errors"

        if len(traces) > 5:
            result += f"\n\n... and {len(traces) - 5} more traces"

        return result
    finally:
        await client.close()


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python search.py <frame_id> [jaeger_url]")
        sys.exit(1)

    frame_id = sys.argv[1]
    jaeger_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:16686"

    result = asyncio.run(quick_search(frame_id, jaeger_url))
    print(result)
