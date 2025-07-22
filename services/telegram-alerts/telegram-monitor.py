#!/usr/bin/env python3
"""
Telegram monitoring alerts for Detektor system.
Monitors disk space, Redis memory, container health.
"""

import asyncio
import os
from datetime import datetime

import aiohttp
import docker
import psutil
from redis_sentinel import RedisSentinelClient


class TelegramMonitor:
    """Telegram monitoring alerts for Detektor system."""

    def __init__(self):
        """Initialize Telegram monitor."""
        # Telegram configuration from environment
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        # Alert thresholds
        self.disk_threshold = int(os.getenv("DISK_ALERT_THRESHOLD", "80"))
        self.redis_memory_threshold = float(
            os.getenv("REDIS_MEMORY_THRESHOLD_GB", "3.5")
        )
        self.postgres_disk_threshold = int(
            os.getenv("POSTGRES_DISK_THRESHOLD_GB", "80")
        )

        # Services
        # Fix for Docker socket connection in container
        try:
            # Try different connection methods
            self.docker_client = docker.DockerClient(
                base_url="unix:///var/run/docker.sock"
            )
        except Exception as e:
            print(f"[WARNING] Failed to connect to Docker daemon: {e}")
            print("[WARNING] Container monitoring will be disabled")
            self.docker_client = None

        # Initialize Redis client with Sentinel support
        self.redis_sentinel = RedisSentinelClient()
        self.redis_client = None

        # State tracking
        self.alerted_issues = set()

    async def send_telegram_message(self, message: str):
        """Send alert to Telegram."""
        if not self.bot_token or not self.chat_id:
            print(f"[WARNING] Telegram not configured. Message: {message}")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": f"🚨 *Detektor Alert*\n\n{message}",
            "parse_mode": "Markdown",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        print(f"Failed to send Telegram alert: {await response.text()}")
            except Exception as e:
                print(f"Error sending Telegram alert: {e}")

    async def check_disk_space(self):
        """Monitor disk space on all mount points."""
        alerts = []

        for partition in psutil.disk_partitions():
            if partition.mountpoint in [
                "/",
                "/data/redis",
                "/data/postgres",
                "/data/frames",
            ]:
                usage = psutil.disk_usage(partition.mountpoint)
                usage_percent = usage.percent

                if usage_percent > self.disk_threshold:
                    alert_key = f"disk_{partition.mountpoint}"
                    if alert_key not in self.alerted_issues:
                        alerts.append(
                            f"📁 *Disk Alert*: {partition.mountpoint}\n"
                            f"Usage: {usage_percent:.1f}% ({usage.used//1024//1024//1024}GB / {usage.total//1024//1024//1024}GB)\n"
                            f"Free: {usage.free//1024//1024//1024}GB"
                        )
                        self.alerted_issues.add(alert_key)
                elif (
                    alert_key in self.alerted_issues
                    and usage_percent < self.disk_threshold - 10
                ):
                    # Clear alert when usage drops 10% below threshold
                    self.alerted_issues.remove(alert_key)
                    alerts.append(
                        f"✅ Disk usage normalized: {partition.mountpoint} ({usage_percent:.1f}%)"
                    )

        return alerts

    async def check_redis_memory(self):
        """Monitor Redis memory usage."""
        try:
            # Get Redis client with HA support
            if not self.redis_client:
                self.redis_client = self.redis_sentinel.connect()

            client = self.redis_sentinel.get_client()
            info = client.info("memory")
            used_memory_gb = info["used_memory"] / 1024 / 1024 / 1024

            if used_memory_gb > self.redis_memory_threshold:
                alert_key = "redis_memory"
                if alert_key not in self.alerted_issues:
                    self.alerted_issues.add(alert_key)
                    return [
                        f"🔴 *Redis Memory Alert*\n"
                        f"Used: {used_memory_gb:.2f}GB / {self.redis_memory_threshold}GB limit\n"
                        f"Peak: {info['used_memory_peak_human']}"
                    ]
            elif (
                "redis_memory" in self.alerted_issues
                and used_memory_gb < self.redis_memory_threshold - 0.5
            ):
                self.alerted_issues.remove("redis_memory")
                return [f"✅ Redis memory normalized: {used_memory_gb:.2f}GB"]
        except Exception as e:
            return [f"⚠️ Redis monitoring error: {str(e)}"]

        return []

    async def check_containers(self):
        """Monitor container health and restarts."""
        alerts = []

        if not self.docker_client:
            return alerts

        try:
            containers = self.docker_client.containers.list(all=True)

            for container in containers:
                if container.name.startswith("detektor-"):
                    # Check if container is running
                    if container.status != "running":
                        alert_key = f"container_{container.name}_down"
                        if alert_key not in self.alerted_issues:
                            self.alerted_issues.add(alert_key)
                            alerts.append(
                                f"🐳 *Container Down*: {container.name}\n"
                                f"Status: {container.status}"
                            )
                    else:
                        alert_key = f"container_{container.name}_down"
                        if alert_key in self.alerted_issues:
                            self.alerted_issues.remove(alert_key)
                            alerts.append(f"✅ Container recovered: {container.name}")

                    # Check restart count
                    if container.attrs["RestartCount"] > 5:
                        alert_key = f"container_{container.name}_restarts"
                        if alert_key not in self.alerted_issues:
                            self.alerted_issues.add(alert_key)
                            alerts.append(
                                f"🔄 *Container Restart Alert*: {container.name}\n"
                                f"Restart count: {container.attrs['RestartCount']}"
                            )
        except Exception as e:
            alerts.append(f"⚠️ Docker monitoring error: {str(e)}")

        return alerts

    async def monitor_loop(self):
        """Main monitoring loop."""
        print("Starting Telegram monitoring...")
        print(f"Bot Token: {'✓' if self.bot_token else '✗'}")
        print(f"Chat ID: {'✓' if self.chat_id else '✗'}")

        while True:
            try:
                all_alerts = []

                # Run all checks
                all_alerts.extend(await self.check_disk_space())
                all_alerts.extend(await self.check_redis_memory())
                all_alerts.extend(await self.check_containers())

                # Send alerts
                for alert in all_alerts:
                    await self.send_telegram_message(alert)
                    await asyncio.sleep(1)  # Rate limit

                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(60)


if __name__ == "__main__":
    monitor = TelegramMonitor()
    asyncio.run(monitor.monitor_loop())
