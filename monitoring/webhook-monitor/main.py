#!/usr/bin/env python3
"""GitHub Webhook Monitor - Tracks GitHub events and alerts on missing workflows."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configuration
WEBHOOK_PORT = 8888
LOG_FILE = Path("/var/log/github-webhook/events.json")
STATE_FILE = Path("/var/lib/github-webhook/state.json")
ALERT_THRESHOLD = timedelta(hours=1)  # Alert if no push events for 1 hour

# Setup logging
logger = structlog.get_logger()
app = FastAPI(title="GitHub Webhook Monitor")

# Ensure directories exist
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


class WebhookEvent(BaseModel):
    """GitHub webhook event structure."""

    event_type: str
    action: Optional[str] = None
    repository: str
    sender: str
    timestamp: datetime
    branch: Optional[str] = None
    workflow_run_id: Optional[int] = None


class MonitorState:
    """Maintains webhook monitoring state."""

    def __init__(self):
        """Initialize monitor state."""
        self.events: List[WebhookEvent] = []
        self.last_push_time: Optional[datetime] = None
        self.workflow_triggers: Dict[str, int] = {}
        self.load_state()

    def load_state(self):
        """Load state from persistent storage."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    data = json.load(f)
                    self.last_push_time = (
                        datetime.fromisoformat(data.get("last_push_time"))
                        if data.get("last_push_time")
                        else None
                    )
                    self.workflow_triggers = data.get("workflow_triggers", {})
            except Exception as e:
                logger.error("Failed to load state", error=str(e))

    def save_state(self):
        """Save state to persistent storage."""
        try:
            data = {
                "last_push_time": self.last_push_time.isoformat()
                if self.last_push_time
                else None,
                "workflow_triggers": self.workflow_triggers,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save state", error=str(e))

    def add_event(self, event: WebhookEvent):
        """Add event and update state."""
        self.events.append(event)

        # Keep only last 1000 events
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

        # Update push time
        if event.event_type == "push":
            self.last_push_time = event.timestamp
            self.workflow_triggers[event.branch or "unknown"] = (
                self.workflow_triggers.get(event.branch or "unknown", 0) + 1
            )

        # Log event
        self.log_event(event)
        self.save_state()

    def log_event(self, event: WebhookEvent):
        """Log event to file."""
        try:
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(event.dict(), default=str) + "\n")
        except Exception as e:
            logger.error("Failed to log event", error=str(e))

    def check_alerts(self) -> List[str]:
        """Check for alert conditions."""
        alerts = []

        # Check for missing push events
        if self.last_push_time:
            time_since_push = datetime.now() - self.last_push_time
            if time_since_push > ALERT_THRESHOLD:
                hours = time_since_push.total_seconds() / 3600
                alerts.append(f"No push events for {hours:.1f} hours")

        # Check for workflow failures pattern
        recent_workflow_runs = [
            e
            for e in self.events
            if e.event_type == "workflow_run"
            and e.timestamp > datetime.now() - timedelta(hours=1)
        ]
        failed_runs = [
            e
            for e in recent_workflow_runs
            if e.action == "completed"
            and hasattr(e, "conclusion")
            and e.conclusion == "failure"
        ]

        if len(failed_runs) >= 3:
            alerts.append(
                f"Multiple workflow failures detected: {len(failed_runs)} in last hour"
            )

        return alerts


# Initialize state
monitor_state = MonitorState()


@app.post("/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events."""
    try:
        # Get event type
        event_type = request.headers.get("X-GitHub-Event", "unknown")

        # Parse payload
        payload = await request.json()

        # Extract relevant information
        event = WebhookEvent(
            event_type=event_type,
            action=payload.get("action"),
            repository=payload.get("repository", {}).get("full_name", "unknown"),
            sender=payload.get("sender", {}).get("login", "unknown"),
            timestamp=datetime.now(),
            branch=payload.get("ref", "").replace("refs/heads/", "")
            if "ref" in payload
            else None,
            workflow_run_id=payload.get("workflow_run", {}).get("id")
            if "workflow_run" in payload
            else None,
        )

        # Add to state
        monitor_state.add_event(event)

        logger.info(
            "Webhook received",
            event_type=event_type,
            repository=event.repository,
            sender=event.sender,
        )

        return JSONResponse({"status": "ok", "event_id": str(event.timestamp)})

    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    alerts = monitor_state.check_alerts()

    status = {
        "status": "healthy" if not alerts else "warning",
        "last_push_time": monitor_state.last_push_time.isoformat()
        if monitor_state.last_push_time
        else None,
        "total_events": len(monitor_state.events),
        "workflow_triggers": monitor_state.workflow_triggers,
        "alerts": alerts,
    }

    return status


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    metrics_lines = []

    # Time since last push
    if monitor_state.last_push_time:
        seconds_since_push = (
            datetime.now() - monitor_state.last_push_time
        ).total_seconds()
        metrics_lines.append(
            "# HELP github_webhook_last_push_seconds Seconds since last push event"
        )
        metrics_lines.append("# TYPE github_webhook_last_push_seconds gauge")
        metrics_lines.append(f"github_webhook_last_push_seconds {seconds_since_push}")

    # Total events
    metrics_lines.append(
        "# HELP github_webhook_total_events Total number of webhook events"
    )
    metrics_lines.append("# TYPE github_webhook_total_events counter")
    metrics_lines.append(f"github_webhook_total_events {len(monitor_state.events)}")

    # Workflow triggers by branch
    for branch, count in monitor_state.workflow_triggers.items():
        metrics_lines.append(
            f'github_webhook_workflow_triggers{{branch="{branch}"}} {count}'
        )

    return "\n".join(metrics_lines)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=WEBHOOK_PORT)
