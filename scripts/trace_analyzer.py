#!/usr/bin/env python3
"""
Frame Trace Analyzer - Search and analyze frame traces by ID.

Usage:
    python trace_analyzer.py search <frame_id> [--jaeger-url=<url>]
    python trace_analyzer.py analyze <frame_id> [--jaeger-url=<url>]
    python trace_analyzer.py stats [--service=<name>] [--hours=<n>]
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from tabulate import tabulate


class TraceAnalyzer:
    """Analyze frame traces from Jaeger."""

    def __init__(self, jaeger_url: str = "http://localhost:16686"):
        """Initialize with Jaeger URL."""
        self.jaeger_url = jaeger_url.rstrip("/")
        self.api_url = f"{self.jaeger_url}/api"

    def search_by_frame_id(self, frame_id: str) -> List[Dict]:
        """
        Search for traces containing a specific frame ID.

        Args:
            frame_id: Frame ID to search for

        Returns:
            List of matching traces
        """
        # Search using frame.id tag
        params = {
            "service": "rtsp-capture",
            "tags": json.dumps({"frame.id": frame_id}),
            "limit": 20,
        }

        try:
            response = requests.get(f"{self.api_url}/traces", params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error searching traces: {e}")
            return []

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict]:
        """Get full trace details by trace ID."""
        try:
            response = requests.get(f"{self.api_url}/traces/{trace_id}")
            response.raise_for_status()
            data = response.json()
            traces = data.get("data", [])
            return traces[0] if traces else None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching trace: {e}")
            return None

    def analyze_frame_journey(self, frame_id: str) -> Dict:
        """
        Analyze the complete journey of a frame through the system.

        Args:
            frame_id: Frame ID to analyze

        Returns:
            Analysis results including timing, services, and issues
        """
        traces = self.search_by_frame_id(frame_id)
        if not traces:
            return {"error": f"No traces found for frame {frame_id}"}

        # Get the most recent trace
        trace = traces[0]
        spans = trace.get("spans", [])

        # Sort spans by start time
        spans.sort(key=lambda s: s.get("startTime", 0))

        # Extract journey information
        journey = {
            "frame_id": frame_id,
            "trace_id": trace.get("traceID"),
            "total_duration_ms": 0,
            "services": set(),
            "operations": [],
            "errors": [],
            "timeline": [],
        }

        if spans:
            start_time = spans[0].get("startTime", 0)
            end_time = max(s.get("startTime", 0) + s.get("duration", 0) for s in spans)
            journey["total_duration_ms"] = (
                end_time - start_time
            ) / 1000  # Convert to ms

        for span in spans:
            service = span.get("process", {}).get("serviceName", "unknown")
            operation = span.get("operationName", "unknown")
            duration_ms = span.get("duration", 0) / 1000  # Convert to ms

            journey["services"].add(service)
            journey["operations"].append(
                {
                    "service": service,
                    "operation": operation,
                    "duration_ms": duration_ms,
                    "start_time": span.get("startTime", 0),
                }
            )

            # Check for errors
            tags = {tag["key"]: tag["value"] for tag in span.get("tags", [])}
            if tags.get("error") or tags.get("status.code") == "ERROR":
                journey["errors"].append(
                    {
                        "service": service,
                        "operation": operation,
                        "message": tags.get("error.message", "Unknown error"),
                    }
                )

            # Build timeline
            journey["timeline"].append(
                {
                    "time": datetime.fromtimestamp(
                        span.get("startTime", 0) / 1000000
                    ).isoformat(),
                    "service": service,
                    "operation": operation,
                    "duration_ms": duration_ms,
                }
            )

        journey["services"] = list(journey["services"])
        return journey

    def get_service_stats(self, service: Optional[str] = None, hours: int = 24) -> Dict:
        """
        Get statistics for frame processing.

        Args:
            service: Optional service name filter
            hours: Number of hours to look back

        Returns:
            Service statistics
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        params = {
            "start": int(start_time.timestamp() * 1000000),
            "end": int(end_time.timestamp() * 1000000),
            "limit": 1000,
        }

        if service:
            params["service"] = service

        try:
            response = requests.get(f"{self.api_url}/traces", params=params)
            response.raise_for_status()
            data = response.json()
            traces = data.get("data", [])

            stats = {
                "total_traces": len(traces),
                "services": {},
                "errors": 0,
                "avg_duration_ms": 0,
                "p95_duration_ms": 0,
                "p99_duration_ms": 0,
            }

            durations = []
            for trace in traces:
                spans = trace.get("spans", [])
                if spans:
                    # Calculate trace duration
                    start = min(s.get("startTime", 0) for s in spans)
                    end = max(
                        s.get("startTime", 0) + s.get("duration", 0) for s in spans
                    )
                    duration_ms = (end - start) / 1000
                    durations.append(duration_ms)

                    # Count services and errors
                    for span in spans:
                        svc = span.get("process", {}).get("serviceName", "unknown")
                        stats["services"][svc] = stats["services"].get(svc, 0) + 1

                        tags = {
                            tag["key"]: tag["value"] for tag in span.get("tags", [])
                        }
                        if tags.get("error"):
                            stats["errors"] += 1

            if durations:
                durations.sort()
                stats["avg_duration_ms"] = sum(durations) / len(durations)
                stats["p95_duration_ms"] = durations[int(len(durations) * 0.95)]
                stats["p99_duration_ms"] = durations[int(len(durations) * 0.99)]

            return stats
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats: {e}")
            return {}


def print_journey(journey: Dict) -> None:
    """Pretty print frame journey analysis."""
    if "error" in journey:
        print(f"❌ {journey['error']}")
        return

    print("\n🎯 Frame Journey Analysis")
    print("=" * 50)
    print(f"Frame ID: {journey['frame_id']}")
    print(f"Trace ID: {journey['trace_id']}")
    print(f"Total Duration: {journey['total_duration_ms']:.2f}ms")
    print(f"Services: {', '.join(journey['services'])}")

    if journey["errors"]:
        print("\n❌ Errors Found:")
        for error in journey["errors"]:
            print(f"  - {error['service']}/{error['operation']}: {error['message']}")

    print("\n📊 Operation Breakdown:")
    table_data = []
    for op in journey["operations"]:
        table_data.append(
            [op["service"], op["operation"], f"{op['duration_ms']:.2f}ms"]
        )
    print(
        tabulate(
            table_data, headers=["Service", "Operation", "Duration"], tablefmt="grid"
        )
    )

    print("\n🕐 Timeline:")
    for event in journey["timeline"][:10]:  # Show first 10 events
        time_str = event["time"]
        service = event["service"][:15].ljust(15)
        operation = event["operation"][:30].ljust(30)
        duration = f"{event['duration_ms']:.2f}ms"
        print(f"  {time_str} | {service} | {operation} | {duration}")
    if len(journey["timeline"]) > 10:
        print(f"  ... and {len(journey['timeline']) - 10} more events")


def print_stats(stats: Dict) -> None:
    """Pretty print service statistics."""
    print("\n📈 Service Statistics")
    print("=" * 50)
    print(f"Total Traces: {stats['total_traces']}")
    print(
        f"Errors: {stats['errors']} "
        f"({stats['errors'] / stats['total_traces'] * 100:.1f}%)"
    )
    print(f"Avg Duration: {stats['avg_duration_ms']:.2f}ms")
    print(f"P95 Duration: {stats['p95_duration_ms']:.2f}ms")
    print(f"P99 Duration: {stats['p99_duration_ms']:.2f}ms")

    print("\n🏢 Service Breakdown:")
    table_data = []
    for service, count in stats["services"].items():
        table_data.append(
            [service, count, f"{count / stats['total_traces'] * 100:.1f}%"]
        )
    print(
        tabulate(
            table_data,
            headers=["Service", "Span Count", "Percentage"],
            tablefmt="grid",
        )
    )


def main() -> None:
    """Run the main entry point."""
    parser = argparse.ArgumentParser(description="Frame Trace Analyzer")
    parser.add_argument(
        "--jaeger-url", default="http://localhost:16686", help="Jaeger URL"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for frame traces")
    search_parser.add_argument("frame_id", help="Frame ID to search for")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze frame journey")
    analyze_parser.add_argument("frame_id", help="Frame ID to analyze")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Get service statistics")
    stats_parser.add_argument("--service", help="Filter by service name")
    stats_parser.add_argument(
        "--hours", type=int, default=24, help="Hours to look back"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    analyzer = TraceAnalyzer(args.jaeger_url)

    if args.command == "search":
        traces = analyzer.search_by_frame_id(args.frame_id)
        print(f"\n🔍 Found {len(traces)} traces for frame {args.frame_id}")
        for i, trace in enumerate(traces[:5]):
            trace_id = trace.get("traceID", "unknown")
            span_count = len(trace.get("spans", []))
            print(f"  {i+1}. Trace {trace_id} ({span_count} spans)")

    elif args.command == "analyze":
        journey = analyzer.analyze_frame_journey(args.frame_id)
        print_journey(journey)

    elif args.command == "stats":
        stats = analyzer.get_service_stats(args.service, args.hours)
        print_stats(stats)


if __name__ == "__main__":
    main()
