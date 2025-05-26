"""
CDN Configuration and Management
Handles Cloud CDN setup, cache policies, and asset optimization
"""

import os
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, urlencode
import json
import logging

logger = logging.getLogger(__name__)


class CDNConfig:
    """Cloud CDN configuration and management"""

    def __init__(self):
        self.cdn_enabled = os.getenv("CDN_ENABLED", "true").lower() == "true"
        self.cdn_url = os.getenv("CDN_URL", "https://cdn.ngx-agents.com")
        self.origin_url = os.getenv("ORIGIN_URL", "https://api.ngx-agents.com")
        self.gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT", "agentes-ngx")

        # Cache settings
        self.cache_settings = {
            "static_assets": {
                "max_age": 31536000,  # 1 year
                "public": True,
                "immutable": True,
                "stale_while_revalidate": 86400,
            },
            "images": {
                "max_age": 2592000,  # 30 days
                "public": True,
                "vary": ["Accept", "Accept-Encoding"],
                "stale_while_revalidate": 86400,
            },
            "api_responses": {
                "max_age": 300,  # 5 minutes
                "public": False,
                "vary": ["Accept", "Authorization"],
                "stale_while_revalidate": 60,
            },
            "reports": {
                "max_age": 3600,  # 1 hour
                "public": False,
                "vary": ["Authorization"],
            },
            "realtime": {
                "max_age": 0,
                "no_cache": True,
                "no_store": True,
            },
        }

        # Supported image formats for optimization
        self.image_formats = {
            "webp": {"quality": 85, "method": 6},
            "avif": {"quality": 80, "speed": 6},
            "jpeg": {"quality": 85, "progressive": True},
            "png": {"compress_level": 9, "optimize": True},
        }

        # Compression settings
        self.compression_enabled = (
            os.getenv("COMPRESSION_ENABLED", "true").lower() == "true"
        )
        self.compression_types = [
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "application/xml",
            "text/xml",
            "image/svg+xml",
            "font/woff",
            "font/woff2",
        ]

    def get_cdn_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate CDN URL for a resource

        Args:
            path: Resource path
            params: Optional query parameters

        Returns:
            CDN URL
        """
        if not self.cdn_enabled:
            base_url = self.origin_url
        else:
            base_url = self.cdn_url

        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{base_url}{path}"

        if params:
            # Add cache busting parameter if needed
            if "v" not in params:
                params["v"] = self._generate_version_hash(path)
            url += f"?{urlencode(params)}"

        return url

    def get_cache_headers(self, content_type: str, path: str) -> Dict[str, str]:
        """
        Get appropriate cache headers for content type

        Args:
            content_type: MIME type of content
            path: Resource path

        Returns:
            Dict of cache headers
        """
        headers = {}

        # Determine cache category
        if content_type.startswith("image/"):
            cache_config = self.cache_settings["images"]
        elif path.startswith("/api/"):
            if "/stream/" in path or "/ws/" in path:
                cache_config = self.cache_settings["realtime"]
            else:
                cache_config = self.cache_settings["api_responses"]
        elif path.endswith(".pdf"):
            cache_config = self.cache_settings["reports"]
        else:
            cache_config = self.cache_settings["static_assets"]

        # Build Cache-Control header
        cache_control_parts = []

        if cache_config.get("no_cache"):
            cache_control_parts.append("no-cache")
        if cache_config.get("no_store"):
            cache_control_parts.append("no-store")
        if cache_config.get("public"):
            cache_control_parts.append("public")
        else:
            cache_control_parts.append("private")

        max_age = cache_config.get("max_age", 0)
        cache_control_parts.append(f"max-age={max_age}")

        if cache_config.get("immutable"):
            cache_control_parts.append("immutable")

        if "stale_while_revalidate" in cache_config:
            cache_control_parts.append(
                f"stale-while-revalidate={cache_config['stale_while_revalidate']}"
            )

        headers["Cache-Control"] = ", ".join(cache_control_parts)

        # Add Vary header
        if "vary" in cache_config:
            headers["Vary"] = ", ".join(cache_config["vary"])

        # Add ETag for static content
        if max_age > 0:
            headers["ETag"] = f'"{self._generate_etag(path)}"'

        # Add CDN-specific headers
        headers["X-CDN-Enabled"] = "true" if self.cdn_enabled else "false"
        headers["X-Cache-Category"] = cache_config.get("category", "default")

        return headers

    def get_image_optimization_params(
        self, accept_header: str, user_agent: str, original_format: str
    ) -> Dict[str, Any]:
        """
        Determine optimal image format and parameters

        Args:
            accept_header: Accept header from request
            user_agent: User-Agent header
            original_format: Original image format

        Returns:
            Optimization parameters
        """
        params = {"format": original_format, "quality": 85, "resize": None}

        # Check WebP support
        if "image/webp" in accept_header:
            params["format"] = "webp"
            params.update(self.image_formats["webp"])

        # Check AVIF support (modern browsers)
        elif "image/avif" in accept_header:
            params["format"] = "avif"
            params.update(self.image_formats["avif"])

        # Fallback to optimized JPEG/PNG
        elif original_format in ["jpeg", "jpg"]:
            params.update(self.image_formats["jpeg"])
        elif original_format == "png":
            params.update(self.image_formats["png"])

        # Add responsive image parameters
        if "Mobile" in user_agent:
            params["resize"] = {"max_width": 1080, "max_height": 1920}
        elif "Tablet" in user_agent:
            params["resize"] = {"max_width": 1536, "max_height": 2048}

        return params

    def should_compress(self, content_type: str, content_length: int) -> bool:
        """
        Determine if content should be compressed

        Args:
            content_type: MIME type
            content_length: Content size in bytes

        Returns:
            Whether to compress
        """
        if not self.compression_enabled:
            return False

        # Don't compress small files (< 1KB)
        if content_length < 1024:
            return False

        # Don't compress already compressed formats
        if content_type in [
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/avif",
            "application/zip",
            "application/gzip",
        ]:
            return False

        # Check if content type is compressible
        return any(content_type.startswith(ct) for ct in self.compression_types)

    def get_srcset_urls(self, base_path: str, widths: List[int]) -> str:
        """
        Generate srcset URLs for responsive images

        Args:
            base_path: Base image path
            widths: List of widths to generate

        Returns:
            srcset string
        """
        srcset_parts = []

        for width in widths:
            url = self.get_cdn_url(base_path, {"w": width})
            srcset_parts.append(f"{url} {width}w")

        return ", ".join(srcset_parts)

    def invalidate_cache(self, paths: List[str]) -> Dict[str, Any]:
        """
        Invalidate CDN cache for specific paths

        Args:
            paths: List of paths to invalidate

        Returns:
            Invalidation result
        """
        if not self.cdn_enabled:
            return {"success": False, "message": "CDN not enabled"}

        try:
            from google.cloud import compute_v1

            # Initialize the CDN client
            client = compute_v1.UrlMapsClient()

            # Create invalidation request
            cache_invalidation = compute_v1.CacheInvalidationRule()
            cache_invalidation.path = paths

            # Execute invalidation
            project = self.gcp_project
            url_map = "ngx-agents-cdn"  # Your URL map name

            operation = client.invalidate_cache(
                project=project,
                url_map=url_map,
                cache_invalidation_rule=cache_invalidation,
            )

            logger.info(f"CDN cache invalidation initiated for {len(paths)} paths")

            return {
                "success": True,
                "operation_id": operation.name,
                "paths_invalidated": len(paths),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"CDN cache invalidation failed: {e}")
            return {"success": False, "error": str(e)}

    def get_edge_config(self) -> Dict[str, Any]:
        """
        Get edge computing configuration for CDN

        Returns:
            Edge configuration
        """
        return {
            "edge_functions": {
                "image_optimization": {
                    "enabled": True,
                    "auto_webp": True,
                    "lazy_transform": True,
                    "cache_variants": True,
                },
                "geo_routing": {
                    "enabled": True,
                    "default_region": "us-central1",
                    "region_mapping": {
                        "EU": "europe-west1",
                        "ASIA": "asia-southeast1",
                        "US": "us-central1",
                    },
                },
                "security": {
                    "ddos_protection": True,
                    "rate_limiting": {
                        "enabled": True,
                        "requests_per_minute": 60,
                        "burst": 10,
                    },
                    "bot_detection": True,
                },
                "personalization": {
                    "enabled": True,
                    "cache_key_headers": ["X-User-Segment", "X-Device-Type"],
                    "vary_by_cookie": ["session_id"],
                },
            }
        }

    def _generate_version_hash(self, path: str) -> str:
        """Generate version hash for cache busting"""
        # In production, this would track actual file versions
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        return hashlib.md5(f"{path}:{timestamp}".encode()).hexdigest()[:8]

    def _generate_etag(self, path: str) -> str:
        """Generate ETag for resource"""
        # In production, this would use actual file content hash
        return hashlib.sha256(path.encode()).hexdigest()[:16]


class ImageOptimizer:
    """Image optimization pipeline"""

    def __init__(self, cdn_config: CDNConfig):
        self.cdn_config = cdn_config
        self.supported_formats = {"jpeg", "jpg", "png", "gif", "webp", "avif"}

    async def optimize_image(
        self,
        image_data: bytes,
        source_format: str,
        target_format: Optional[str] = None,
        resize_params: Optional[Dict[str, int]] = None,
        quality: Optional[int] = None,
    ) -> Tuple[bytes, str]:
        """
        Optimize image for web delivery

        Args:
            image_data: Original image data
            source_format: Source image format
            target_format: Target format (optional)
            resize_params: Resize parameters (optional)
            quality: Quality setting (optional)

        Returns:
            Tuple of (optimized_data, format)
        """
        from PIL import Image
        import io

        try:
            # Open image
            img = Image.open(io.BytesIO(image_data))

            # Convert RGBA to RGB if needed
            if img.mode == "RGBA" and target_format in ["jpeg", "jpg"]:
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background

            # Resize if needed
            if resize_params:
                max_width = resize_params.get("max_width")
                max_height = resize_params.get("max_height")

                if max_width or max_height:
                    img.thumbnail(
                        (max_width or img.width, max_height or img.height),
                        Image.Resampling.LANCZOS,
                    )

            # Determine output format
            output_format = target_format or source_format
            if output_format == "jpg":
                output_format = "jpeg"

            # Prepare output
            output = io.BytesIO()

            # Save with optimization
            save_kwargs = {"format": output_format.upper(), "optimize": True}

            # Add format-specific parameters
            if output_format == "jpeg":
                save_kwargs["quality"] = quality or 85
                save_kwargs["progressive"] = True
            elif output_format == "png":
                save_kwargs["compress_level"] = 9
            elif output_format == "webp":
                save_kwargs["quality"] = quality or 85
                save_kwargs["method"] = 6

            img.save(output, **save_kwargs)

            return output.getvalue(), output_format

        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            # Return original on failure
            return image_data, source_format

    def get_image_metadata(self, image_data: bytes) -> Dict[str, Any]:
        """Extract image metadata"""
        from PIL import Image
        import io

        try:
            img = Image.open(io.BytesIO(image_data))

            return {
                "format": img.format.lower() if img.format else "unknown",
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "has_transparency": img.mode in ("RGBA", "LA", "P"),
                "info": img.info,
            }
        except Exception as e:
            logger.error(f"Failed to extract image metadata: {e}")
            return {}


class CacheManager:
    """CDN cache management and strategies"""

    def __init__(self, cdn_config: CDNConfig):
        self.cdn_config = cdn_config
        self.cache_strategies = {
            "api": self._cache_api_response,
            "static": self._cache_static_asset,
            "image": self._cache_image,
            "report": self._cache_report,
        }

    async def cache_response(
        self,
        response_data: Any,
        content_type: str,
        path: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Determine caching strategy and headers for response

        Args:
            response_data: Response data
            content_type: Content type
            path: Request path
            user_context: User context for personalization

        Returns:
            Cache headers
        """
        # Determine cache strategy
        if path.startswith("/api/"):
            strategy = "api"
        elif content_type.startswith("image/"):
            strategy = "image"
        elif content_type == "application/pdf":
            strategy = "report"
        else:
            strategy = "static"

        # Apply strategy
        cache_func = self.cache_strategies.get(strategy, self._cache_default)
        return await cache_func(response_data, content_type, path, user_context)

    async def _cache_api_response(
        self,
        data: Any,
        content_type: str,
        path: str,
        user_context: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Cache strategy for API responses"""
        headers = self.cdn_config.get_cache_headers(content_type, path)

        # Add surrogate control for edge caching
        if "/public/" in path:
            headers["Surrogate-Control"] = "max-age=300, stale-while-revalidate=60"
        else:
            headers["Surrogate-Control"] = "no-store"

        # Add user segment for cache key
        if user_context:
            headers["X-User-Segment"] = user_context.get("segment", "default")

        return headers

    async def _cache_static_asset(
        self,
        data: Any,
        content_type: str,
        path: str,
        user_context: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Cache strategy for static assets"""
        headers = self.cdn_config.get_cache_headers(content_type, path)

        # Use immutable caching for versioned assets
        if "v=" in path or any(
            hash_pattern in path for hash_pattern in [".min.", "-min.", ".bundle."]
        ):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return headers

    async def _cache_image(
        self,
        data: Any,
        content_type: str,
        path: str,
        user_context: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Cache strategy for images"""
        headers = self.cdn_config.get_cache_headers(content_type, path)

        # Add image-specific headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Accept-CH"] = "DPR, Width, Viewport-Width"

        return headers

    async def _cache_report(
        self,
        data: Any,
        content_type: str,
        path: str,
        user_context: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Cache strategy for reports"""
        headers = self.cdn_config.get_cache_headers(content_type, path)

        # Reports are user-specific
        headers["Cache-Control"] = "private, max-age=3600"
        headers["X-Robots-Tag"] = "noindex"

        return headers

    async def _cache_default(
        self,
        data: Any,
        content_type: str,
        path: str,
        user_context: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Default cache strategy"""
        return self.cdn_config.get_cache_headers(content_type, path)


# Singleton instances
cdn_config = CDNConfig()
image_optimizer = ImageOptimizer(cdn_config)
cache_manager = CacheManager(cdn_config)
