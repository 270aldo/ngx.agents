"""
Celery Tasks Package for NGX Agents
Async task definitions for distributed processing
"""

from core.celery_app import app

__all__ = ["app"]
