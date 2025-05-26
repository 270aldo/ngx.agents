"""
Celery Application Configuration for NGX Agents
Distributed task queue system for async processing
"""

import os
from celery import Celery
from kombu import Queue, Exchange
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Broker Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# Redis Configuration (for results backend)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = os.getenv("REDIS_DB", "1")  # Use different DB for Celery results

# Create Celery instance
app = Celery("ngx_agents")

# Broker URL
broker_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"

# Result backend URL
if REDIS_PASSWORD:
    result_backend = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Celery Configuration
app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Define task queues
app.conf.task_queues = (
    # High priority queue for critical tasks
    Queue(
        "high_priority",
        Exchange("high_priority"),
        routing_key="high_priority",
        queue_arguments={"x-max-priority": 10},
    ),
    # Default queue for general tasks
    Queue(
        "default",
        Exchange("default"),
        routing_key="default",
        queue_arguments={"x-max-priority": 5},
    ),
    # Report generation queue
    Queue(
        "reports",
        Exchange("reports"),
        routing_key="reports",
        queue_arguments={"x-max-priority": 3},
    ),
    # Image processing queue
    Queue(
        "images",
        Exchange("images"),
        routing_key="images",
        queue_arguments={"x-max-priority": 3},
    ),
    # Analytics queue
    Queue(
        "analytics",
        Exchange("analytics"),
        routing_key="analytics",
        queue_arguments={"x-max-priority": 2},
    ),
    # Low priority queue for batch operations
    Queue(
        "low_priority",
        Exchange("low_priority"),
        routing_key="low_priority",
        queue_arguments={"x-max-priority": 1},
    ),
)

# Task routing
app.conf.task_routes = {
    # Report tasks
    "tasks.reports.*": {
        "queue": "reports",
        "routing_key": "reports",
        "priority": 3,
    },
    # Image processing tasks
    "tasks.images.*": {
        "queue": "images",
        "routing_key": "images",
        "priority": 3,
    },
    # Analytics tasks
    "tasks.analytics.*": {
        "queue": "analytics",
        "routing_key": "analytics",
        "priority": 2,
    },
    # High priority tasks
    "tasks.critical.*": {
        "queue": "high_priority",
        "routing_key": "high_priority",
        "priority": 10,
    },
    # Default routing
    "tasks.*": {
        "queue": "default",
        "routing_key": "default",
        "priority": 5,
    },
}

# Task annotations for specific timeouts
app.conf.task_annotations = {
    "tasks.reports.generate_pdf_report": {
        "time_limit": 300,  # 5 minutes for PDF generation
        "soft_time_limit": 270,
    },
    "tasks.images.analyze_posture": {
        "time_limit": 180,  # 3 minutes for image analysis
        "soft_time_limit": 150,
    },
    "tasks.analytics.calculate_trends": {
        "time_limit": 600,  # 10 minutes for trend analysis
        "soft_time_limit": 540,
    },
}

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Clean up expired results every hour
    "cleanup-results": {
        "task": "tasks.maintenance.cleanup_expired_results",
        "schedule": 3600.0,  # Every hour
    },
    # Generate daily analytics summary
    "daily-analytics": {
        "task": "tasks.analytics.generate_daily_summary",
        "schedule": 86400.0,  # Every 24 hours
        "options": {
            "queue": "analytics",
            "priority": 2,
        },
    },
    # Health check for monitoring
    "health-check": {
        "task": "tasks.maintenance.health_check",
        "schedule": 60.0,  # Every minute
        "options": {
            "queue": "high_priority",
            "priority": 10,
        },
    },
}

# Auto-discover tasks
app.autodiscover_tasks(["tasks"])


# Monitoring hooks
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "worker": self.request.hostname}
