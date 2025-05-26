"""
Maintenance Tasks
System maintenance and health check tasks
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import Task
from core.celery_app import app
from clients.supabase_client import SupabaseClient
import redis
import psutil
import os

logger = logging.getLogger(__name__)


class BaseMaintenanceTask(Task):
    """Base class for maintenance tasks"""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2, "countdown": 10}
    track_started = True


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.health_check")
def health_check() -> Dict[str, Any]:
    """
    Perform system health check

    Returns:
        Dict with health status of various components
    """
    try:
        logger.info("Performing system health check")

        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
            "resources": {},
            "queues": {},
        }

        # Check database connection
        try:
            supabase = SupabaseClient()
            supabase.health_check()
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"

        # Check Redis connection
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", ""),
                decode_responses=True,
            )
            r.ping()
            health_status["services"]["redis"] = "healthy"
        except Exception as e:
            health_status["services"]["redis"] = f"unhealthy: {str(e)}"

        # Check system resources
        health_status["resources"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # Check Celery queues
        from celery import current_app

        inspector = current_app.control.inspect()

        active_queues = inspector.active_queues()
        if active_queues:
            for worker, queues in active_queues.items():
                health_status["queues"][worker] = len(queues)

        # Determine overall health
        all_healthy = all(
            status == "healthy" for status in health_status["services"].values()
        )

        resources_ok = (
            health_status["resources"]["cpu_percent"] < 90
            and health_status["resources"]["memory_percent"] < 90
            and health_status["resources"]["disk_percent"] < 90
        )

        health_status["overall"] = (
            "healthy" if all_healthy and resources_ok else "degraded"
        )

        logger.info(f"Health check completed: {health_status['overall']}")

        return health_status

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall": "error",
            "error": str(e),
        }


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.cleanup_expired_results")
def cleanup_expired_results() -> Dict[str, Any]:
    """
    Clean up expired Celery task results

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info("Starting cleanup of expired results")

        # Connect to Redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            db=int(os.getenv("REDIS_DB", "1")),
            decode_responses=True,
        )

        # Find expired keys
        expired_count = 0
        pattern = "celery-task-meta-*"

        for key in r.scan_iter(match=pattern):
            ttl = r.ttl(key)
            # If TTL is -1 (no expiry) or -2 (already expired)
            if ttl == -1:
                # Set expiry to 1 hour for keys without TTL
                r.expire(key, 3600)
                expired_count += 1
            elif ttl == -2:
                # Delete already expired keys
                r.delete(key)
                expired_count += 1

        logger.info(f"Cleanup completed: {expired_count} keys processed")

        return {
            "success": True,
            "expired_count": expired_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        raise


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.cleanup_old_files")
def cleanup_old_files(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old temporary files

    Args:
        days_old: Files older than this many days will be deleted

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info(f"Cleaning up files older than {days_old} days")

        # Initialize client
        supabase = SupabaseClient()

        # Define temporary file patterns
        temp_patterns = ["temp/", "cache/", "exports/temp/", "uploads/processing/"]

        deleted_count = 0
        deleted_size = 0

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        for pattern in temp_patterns:
            try:
                # List files in directory
                files = supabase.list_files(pattern)

                for file in files:
                    if file.get("created_at"):
                        created = datetime.fromisoformat(file["created_at"])
                        if created < cutoff_date:
                            # Delete old file
                            supabase.delete_file(file["path"])
                            deleted_count += 1
                            deleted_size += file.get("size", 0)

            except Exception as e:
                logger.warning(f"Error cleaning pattern {pattern}: {e}")

        logger.info(
            f"Cleanup completed: {deleted_count} files, {deleted_size/1024/1024:.2f} MB"
        )

        return {
            "success": True,
            "deleted_count": deleted_count,
            "deleted_size_mb": deleted_size / 1024 / 1024,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in file cleanup: {e}")
        raise


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.optimize_database")
def optimize_database() -> Dict[str, Any]:
    """
    Perform database optimization tasks

    Returns:
        Dict with optimization results
    """
    try:
        logger.info("Starting database optimization")

        # Initialize client
        supabase = SupabaseClient()

        optimization_results = {
            "tables_analyzed": 0,
            "indexes_rebuilt": 0,
            "space_reclaimed_mb": 0,
        }

        # Analyze tables for statistics update
        tables = ["workouts", "meals", "progress_records", "agent_interactions"]

        for table in tables:
            try:
                supabase.execute_raw_sql(f"ANALYZE {table}")
                optimization_results["tables_analyzed"] += 1
            except Exception as e:
                logger.warning(f"Failed to analyze table {table}: {e}")

        # Clean up old session data
        cutoff = datetime.utcnow() - timedelta(days=7)
        deleted = supabase.delete_old_sessions(cutoff)

        # Estimate space reclaimed (rough estimate)
        optimization_results["space_reclaimed_mb"] = (
            deleted * 0.1
        )  # Assume 100KB per session

        logger.info(f"Database optimization completed: {optimization_results}")

        return {
            "success": True,
            "results": optimization_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in database optimization: {e}")
        raise


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.monitor_task_performance")
def monitor_task_performance() -> Dict[str, Any]:
    """
    Monitor Celery task performance metrics

    Returns:
        Dict with performance metrics
    """
    try:
        logger.info("Monitoring task performance")

        from celery import current_app

        inspector = current_app.control.inspect()

        performance_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "workers": {},
            "queues": {},
            "failed_tasks": [],
        }

        # Get active workers
        active_workers = inspector.active()
        if active_workers:
            for worker, tasks in active_workers.items():
                performance_data["workers"][worker] = {
                    "active_tasks": len(tasks),
                    "task_types": {},
                }

                # Count task types
                for task in tasks:
                    task_name = task.get("name", "unknown")
                    if (
                        task_name
                        not in performance_data["workers"][worker]["task_types"]
                    ):
                        performance_data["workers"][worker]["task_types"][task_name] = 0
                    performance_data["workers"][worker]["task_types"][task_name] += 1

        # Get queue lengths
        reserved = inspector.reserved()
        if reserved:
            for worker, tasks in reserved.items():
                queue_lengths = {}
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "default")
                    queue_lengths[queue] = queue_lengths.get(queue, 0) + 1
                performance_data["queues"][worker] = queue_lengths

        # Check for failed tasks in Redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", ""),
            db=int(os.getenv("REDIS_DB", "1")),
        )

        # Look for failed task patterns
        for key in r.scan_iter(match="celery-task-meta-*"):
            try:
                result = r.get(key)
                if result and b'"status": "FAILURE"' in result:
                    performance_data["failed_tasks"].append(key.decode())
            except:
                pass

        # Calculate summary metrics
        total_active = sum(
            data["active_tasks"] for data in performance_data["workers"].values()
        )

        performance_data["summary"] = {
            "total_active_tasks": total_active,
            "worker_count": len(performance_data["workers"]),
            "failed_count": len(performance_data["failed_tasks"]),
        }

        logger.info(f"Performance monitoring completed: {performance_data['summary']}")

        return performance_data

    except Exception as e:
        logger.error(f"Error monitoring task performance: {e}")
        raise


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.backup_critical_data")
def backup_critical_data() -> Dict[str, Any]:
    """
    Backup critical application data

    Returns:
        Dict with backup statistics
    """
    try:
        logger.info("Starting critical data backup")

        # Initialize client
        supabase = SupabaseClient()

        backup_stats = {
            "tables_backed_up": 0,
            "total_records": 0,
            "backup_size_mb": 0,
            "backup_location": None,
        }

        # Define critical tables to backup
        critical_tables = [
            "users",
            "workouts",
            "nutrition_plans",
            "progress_records",
            "goals",
        ]

        backup_data = {}

        for table in critical_tables:
            try:
                # Export table data
                data = supabase.export_table(table)
                backup_data[table] = data
                backup_stats["tables_backed_up"] += 1
                backup_stats["total_records"] += len(data)

            except Exception as e:
                logger.error(f"Failed to backup table {table}: {e}")

        # Create backup file
        import json
        import gzip

        backup_filename = (
            f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json.gz"
        )
        backup_content = json.dumps(backup_data).encode()

        # Compress backup
        compressed = gzip.compress(backup_content)
        backup_stats["backup_size_mb"] = len(compressed) / 1024 / 1024

        # Upload backup
        backup_path = f"backups/{backup_filename}"
        backup_url = supabase.upload_file(compressed, backup_path)
        backup_stats["backup_location"] = backup_url

        # Store backup metadata
        backup_metadata = {
            "filename": backup_filename,
            "url": backup_url,
            "stats": backup_stats,
            "created_at": datetime.utcnow().isoformat(),
        }
        supabase.save_backup_metadata(backup_metadata)

        logger.info(f"Backup completed: {backup_stats}")

        return {
            "success": True,
            "stats": backup_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in data backup: {e}")
        raise


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.check_agent_health")
def check_agent_health() -> Dict[str, Any]:
    """
    Check health status of all agents

    Returns:
        Dict with agent health status
    """
    try:
        logger.info("Checking agent health status")

        # Initialize client
        supabase = SupabaseClient()

        agent_health = {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {},
            "unhealthy_count": 0,
        }

        # List of all agents
        agents = [
            "orchestrator",
            "elite_training_strategist",
            "precision_nutrition_architect",
            "biometrics_insight_engine",
            "motivation_behavior_coach",
            "progress_tracker",
            "recovery_corrective",
            "security_compliance_guardian",
            "systems_integration_ops",
            "biohacking_innovator",
            "client_success_liaison",
        ]

        for agent in agents:
            try:
                # Check agent response time
                start_time = datetime.utcnow()

                # Simulate agent health check
                response = supabase.check_agent_status(agent)

                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                agent_health["agents"][agent] = {
                    "status": "healthy" if response else "unhealthy",
                    "response_time_ms": response_time,
                    "last_active": response.get("last_active") if response else None,
                }

                if not response:
                    agent_health["unhealthy_count"] += 1

            except Exception as e:
                agent_health["agents"][agent] = {"status": "error", "error": str(e)}
                agent_health["unhealthy_count"] += 1

        # Determine overall health
        agent_health["overall"] = (
            "healthy" if agent_health["unhealthy_count"] == 0 else "degraded"
        )

        # Alert if agents are unhealthy
        if agent_health["unhealthy_count"] > 0:
            logger.warning(f"{agent_health['unhealthy_count']} agents are unhealthy")

        logger.info(f"Agent health check completed: {agent_health['overall']}")

        return agent_health

    except Exception as e:
        logger.error(f"Error checking agent health: {e}")
        raise


@app.task(base=BaseMaintenanceTask, name="tasks.maintenance.cleanup_old_logs")
def cleanup_old_logs(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old application logs

    Args:
        days_old: Logs older than this many days will be archived/deleted

    Returns:
        Dict with cleanup statistics
    """
    try:
        logger.info(f"Cleaning up logs older than {days_old} days")

        import glob
        import shutil

        log_stats = {"files_processed": 0, "files_archived": 0, "space_freed_mb": 0}

        # Log directories
        log_dirs = ["logs/", "/var/log/ngx-agents/", "app/logs/"]

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                continue

            # Find log files
            log_files = glob.glob(os.path.join(log_dir, "*.log*"))

            for log_file in log_files:
                try:
                    # Check file age
                    file_time = datetime.fromtimestamp(os.path.getmtime(log_file))

                    if file_time < cutoff_date:
                        file_size = os.path.getsize(log_file)

                        # Archive old logs
                        if not log_file.endswith(".gz"):
                            # Compress the file
                            import gzip

                            with open(log_file, "rb") as f_in:
                                with gzip.open(f"{log_file}.gz", "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)

                            # Remove original
                            os.remove(log_file)
                            log_stats["files_archived"] += 1

                        log_stats["files_processed"] += 1
                        log_stats["space_freed_mb"] += file_size / 1024 / 1024

                except Exception as e:
                    logger.warning(f"Error processing log file {log_file}: {e}")

        logger.info(f"Log cleanup completed: {log_stats}")

        return {
            "success": True,
            "stats": log_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in log cleanup: {e}")
        raise
