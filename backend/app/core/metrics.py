import os
import time
from typing import Dict, List, Any

class MetricsTracker:
    """
    Tracks and formats system/application runtime telemetry and resource metrics.
    """
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.provider_usage: Dict[str, int] = {}
        self.completed_executions = 0
        self.failed_executions = 0
        self.cancelled_executions = 0
        self.execution_durations: List[float] = []

    @property
    def uptime(self) -> float:
        return time.time() - self.start_time

    def track_request(self) -> None:
        self.request_count += 1

    def track_provider(self, provider: str) -> None:
        self.provider_usage[provider] = self.provider_usage.get(provider, 0) + 1

    def track_execution(self, status: str, duration: float) -> None:
        status_upper = status.upper().strip()
        if status_upper == "COMPLETED":
            self.completed_executions += 1
        elif status_upper == "FAILED":
            self.failed_executions += 1
        elif status_upper == "CANCELLED":
            self.cancelled_executions += 1
        self.execution_durations.append(duration)

    def get_metrics(self, active_count: int) -> Dict[str, Any]:
        avg_duration = 0.0
        if self.execution_durations:
            avg_duration = sum(self.execution_durations) / len(self.execution_durations)

        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_bytes = process.memory_info().rss
        except Exception:
            memory_bytes = 0

        return {
            "uptime_seconds": self.uptime,
            "active_executions": active_count,
            "completed_executions": self.completed_executions,
            "failed_executions": self.failed_executions,
            "cancelled_executions": self.cancelled_executions,
            "memory_usage_bytes": memory_bytes,
            "request_count": self.request_count,
            "provider_usage": self.provider_usage,
            "average_execution_duration_seconds": avg_duration
        }

# Global metrics tracker instance
metrics_tracker = MetricsTracker()
