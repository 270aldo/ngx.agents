"""
Advanced Caching Strategies
Implements intelligent caching for different content types and scenarios
"""

import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List, Callable, Union
from functools import wraps
import asyncio
import logging

from redis import Redis
from core.redis_pool import RedisPool

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Base class for cache strategies"""

    def __init__(self, redis_pool: Optional[RedisPool] = None):
        self.redis_pool = redis_pool or RedisPool()
        self.redis_client = None

    async def get_client(self) -> Redis:
        """Get Redis client"""
        if not self.redis_client:
            self.redis_client = await self.redis_pool.get_client()
        return self.redis_client

    def generate_key(self, *args, **kwargs) -> str:
        """Generate cache key"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        raise NotImplementedError


class StandardCacheStrategy(CacheStrategy):
    """Standard caching strategy with TTL"""

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await self.get_client()
            value = await client.get(key)

            if value:
                # Try to deserialize
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Try pickle for complex objects
                    try:
                        return pickle.loads(value)
                    except:
                        return value.decode() if isinstance(value, bytes) else value

            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            client = await self.get_client()

            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            elif isinstance(value, (str, int, float)):
                serialized = str(value)
            else:
                serialized = pickle.dumps(value)

            # Set with TTL
            if ttl:
                return await client.setex(key, ttl, serialized)
            else:
                return await client.set(key, serialized)

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            client = await self.get_client()
            return await client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False


class StaleWhileRevalidateStrategy(CacheStrategy):
    """
    Stale-while-revalidate caching strategy
    Serves stale content while updating in background
    """

    def __init__(
        self,
        redis_pool: Optional[RedisPool] = None,
        stale_ttl: int = 3600,
        fresh_ttl: int = 300,
    ):
        super().__init__(redis_pool)
        self.stale_ttl = stale_ttl  # How long to keep stale data
        self.fresh_ttl = fresh_ttl  # How long data is considered fresh
        self._revalidation_tasks = {}

    async def get(
        self, key: str, revalidate_func: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Get value from cache with stale-while-revalidate logic
        """
        try:
            client = await self.get_client()

            # Check main key
            value_data = await client.get(key)
            if not value_data:
                return None

            # Deserialize
            data = json.loads(value_data)
            value = data["value"]
            timestamp = data["timestamp"]

            # Check if fresh
            age = datetime.utcnow().timestamp() - timestamp

            if age < self.fresh_ttl:
                # Still fresh
                return value
            elif age < self.stale_ttl:
                # Stale but usable
                if revalidate_func and key not in self._revalidation_tasks:
                    # Start background revalidation
                    task = asyncio.create_task(self._revalidate(key, revalidate_func))
                    self._revalidation_tasks[key] = task

                    # Clean up when done
                    task.add_done_callback(
                        lambda t: self._revalidation_tasks.pop(key, None)
                    )

                return value
            else:
                # Too stale
                return None

        except Exception as e:
            logger.error(f"SWR get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with timestamp"""
        try:
            client = await self.get_client()

            data = {"value": value, "timestamp": datetime.utcnow().timestamp()}

            serialized = json.dumps(data)
            total_ttl = ttl or self.stale_ttl

            return await client.setex(key, total_ttl, serialized)

        except Exception as e:
            logger.error(f"SWR set error: {e}")
            return False

    async def _revalidate(self, key: str, revalidate_func: Callable):
        """Background revalidation"""
        try:
            # Get fresh data
            fresh_value = await revalidate_func()

            # Update cache
            if fresh_value is not None:
                await self.set(key, fresh_value)

        except Exception as e:
            logger.error(f"Revalidation error for {key}: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            client = await self.get_client()
            return await client.delete(key) > 0
        except Exception as e:
            logger.error(f"SWR delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            client = await self.get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"SWR exists error: {e}")
            return False


class TaggedCacheStrategy(CacheStrategy):
    """
    Tagged caching strategy for invalidating groups of cache entries
    """

    def __init__(self, redis_pool: Optional[RedisPool] = None):
        super().__init__(redis_pool)
        self.tag_prefix = "tag:"
        self.key_prefix = "tagged:"

    async def get(self, key: str) -> Optional[Any]:
        """Get tagged value from cache"""
        prefixed_key = f"{self.key_prefix}{key}"

        try:
            client = await self.get_client()
            value = await client.get(prefixed_key)

            if value:
                return json.loads(value)

            return None

        except Exception as e:
            logger.error(f"Tagged get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = 3600,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Set value with tags"""
        prefixed_key = f"{self.key_prefix}{key}"

        try:
            client = await self.get_client()

            # Set the value
            serialized = json.dumps(value)

            # Use pipeline for atomic operations
            pipe = client.pipeline()

            # Set the main value
            if ttl:
                pipe.setex(prefixed_key, ttl, serialized)
            else:
                pipe.set(prefixed_key, serialized)

            # Add to tag sets
            if tags:
                for tag in tags:
                    tag_key = f"{self.tag_prefix}{tag}"
                    pipe.sadd(tag_key, prefixed_key)
                    if ttl:
                        pipe.expire(tag_key, ttl + 60)  # Slightly longer TTL for tags

            # Execute pipeline
            results = await pipe.execute()
            return all(results)

        except Exception as e:
            logger.error(f"Tagged set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete tagged value"""
        prefixed_key = f"{self.key_prefix}{key}"

        try:
            client = await self.get_client()
            return await client.delete(prefixed_key) > 0
        except Exception as e:
            logger.error(f"Tagged delete error: {e}")
            return False

    async def delete_by_tag(self, tag: str) -> int:
        """Delete all entries with a specific tag"""
        tag_key = f"{self.tag_prefix}{tag}"

        try:
            client = await self.get_client()

            # Get all keys with this tag
            keys = await client.smembers(tag_key)

            if not keys:
                return 0

            # Delete all keys
            pipe = client.pipeline()
            for key in keys:
                pipe.delete(key)

            # Delete the tag set
            pipe.delete(tag_key)

            # Execute
            results = await pipe.execute()
            return sum(1 for r in results[:-1] if r > 0)  # Count successful deletes

        except Exception as e:
            logger.error(f"Tagged delete by tag error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if tagged key exists"""
        prefixed_key = f"{self.key_prefix}{key}"

        try:
            client = await self.get_client()
            return await client.exists(prefixed_key) > 0
        except Exception as e:
            logger.error(f"Tagged exists error: {e}")
            return False


class PersonalizedCacheStrategy(CacheStrategy):
    """
    Personalized caching strategy for user-specific content
    """

    def __init__(self, redis_pool: Optional[RedisPool] = None):
        super().__init__(redis_pool)
        self.user_prefix = "user:"
        self.segment_prefix = "segment:"

    def generate_personalized_key(
        self,
        base_key: str,
        user_id: Optional[str] = None,
        segment: Optional[str] = None,
    ) -> str:
        """Generate personalized cache key"""
        if user_id:
            return f"{self.user_prefix}{user_id}:{base_key}"
        elif segment:
            return f"{self.segment_prefix}{segment}:{base_key}"
        else:
            return base_key

    async def get(
        self, key: str, user_id: Optional[str] = None, segment: Optional[str] = None
    ) -> Optional[Any]:
        """Get personalized value from cache"""
        personalized_key = self.generate_personalized_key(key, user_id, segment)

        try:
            client = await self.get_client()
            value = await client.get(personalized_key)

            if value:
                return json.loads(value)

            # Fallback to segment cache if user cache miss
            if user_id and segment:
                segment_key = self.generate_personalized_key(key, segment=segment)
                segment_value = await client.get(segment_key)
                if segment_value:
                    return json.loads(segment_value)

            return None

        except Exception as e:
            logger.error(f"Personalized get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = 3600,
        user_id: Optional[str] = None,
        segment: Optional[str] = None,
    ) -> bool:
        """Set personalized value in cache"""
        personalized_key = self.generate_personalized_key(key, user_id, segment)

        try:
            client = await self.get_client()
            serialized = json.dumps(value)

            if ttl:
                return await client.setex(personalized_key, ttl, serialized)
            else:
                return await client.set(personalized_key, serialized)

        except Exception as e:
            logger.error(f"Personalized set error: {e}")
            return False

    async def delete(
        self, key: str, user_id: Optional[str] = None, segment: Optional[str] = None
    ) -> bool:
        """Delete personalized value"""
        personalized_key = self.generate_personalized_key(key, user_id, segment)

        try:
            client = await self.get_client()
            return await client.delete(personalized_key) > 0
        except Exception as e:
            logger.error(f"Personalized delete error: {e}")
            return False

    async def delete_user_cache(self, user_id: str) -> int:
        """Delete all cache entries for a user"""
        pattern = f"{self.user_prefix}{user_id}:*"

        try:
            client = await self.get_client()

            # Find all user keys
            keys = []
            cursor = 0
            while True:
                cursor, batch = await client.scan(cursor, match=pattern, count=100)
                keys.extend(batch)
                if cursor == 0:
                    break

            if not keys:
                return 0

            # Delete all keys
            return await client.delete(*keys)

        except Exception as e:
            logger.error(f"Delete user cache error: {e}")
            return 0

    async def exists(
        self, key: str, user_id: Optional[str] = None, segment: Optional[str] = None
    ) -> bool:
        """Check if personalized key exists"""
        personalized_key = self.generate_personalized_key(key, user_id, segment)

        try:
            client = await self.get_client()
            return await client.exists(personalized_key) > 0
        except Exception as e:
            logger.error(f"Personalized exists error: {e}")
            return False


# Cache decorators
def cached(
    strategy: CacheStrategy = None,
    ttl: int = 3600,
    key_prefix: str = "",
    tags: Optional[List[str]] = None,
):
    """
    Decorator for caching function results
    """
    if strategy is None:
        strategy = StandardCacheStrategy()

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = (
                f"{key_prefix}:{func.__name__}:{strategy.generate_key(*args, **kwargs)}"
            )

            # Try to get from cache
            cached_value = await strategy.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            if isinstance(strategy, TaggedCacheStrategy) and tags:
                await strategy.set(cache_key, result, ttl=ttl, tags=tags)
            else:
                await strategy.set(cache_key, result, ttl=ttl)

            logger.debug(f"Cache miss for {cache_key}, stored with TTL {ttl}")
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_aside(strategy: CacheStrategy = None, ttl: int = 3600):
    """
    Cache-aside pattern decorator
    """
    if strategy is None:
        strategy = StandardCacheStrategy()

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract cache key from kwargs
            cache_key = kwargs.get("cache_key")
            if not cache_key:
                # Generate from args
                cache_key = f"{func.__name__}:{strategy.generate_key(*args, **kwargs)}"

            # Try cache first
            cached_value = await strategy.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Load from source
            result = await func(*args, **kwargs)

            # Update cache
            if result is not None:
                await strategy.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# Singleton instances
standard_cache = StandardCacheStrategy()
swr_cache = StaleWhileRevalidateStrategy()
tagged_cache = TaggedCacheStrategy()
personalized_cache = PersonalizedCacheStrategy()
