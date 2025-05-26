"""
CDN Middleware for FastAPI
Handles CDN integration, caching headers, and content optimization
"""

import gzip
import brotli
import hashlib
import json
from typing import Callable, Optional, Dict, Any
from datetime import datetime
import logging

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers, MutableHeaders

from core.cdn_config import cdn_config, image_optimizer, cache_manager

logger = logging.getLogger(__name__)


class CDNMiddleware(BaseHTTPMiddleware):
    """
    Middleware for CDN integration and optimization
    """

    def __init__(
        self,
        app,
        enable_compression: bool = True,
        enable_caching: bool = True,
        enable_image_optimization: bool = True,
    ):
        super().__init__(app)
        self.enable_compression = enable_compression
        self.enable_caching = enable_caching
        self.enable_image_optimization = enable_image_optimization

        # Compression settings
        self.min_compress_size = 1024  # 1KB
        self.compression_level = {"gzip": 6, "br": 4}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with CDN optimizations
        """
        # Check if request is from CDN
        is_cdn_request = self._is_cdn_request(request)

        # Add CDN headers to request
        if is_cdn_request:
            request.state.is_cdn = True
            request.state.cdn_pop = request.headers.get("CF-Ray", "unknown")

        # Process request
        response = await call_next(request)

        # Skip processing for streaming responses
        if isinstance(response, StreamingResponse):
            return response

        # Apply CDN optimizations
        if self.enable_caching:
            await self._apply_cache_headers(request, response)

        # Apply compression if needed
        if self.enable_compression and self._should_compress(request, response):
            response = await self._compress_response(request, response)

        # Add CDN tracking headers
        self._add_cdn_headers(response, is_cdn_request)

        # Add security headers
        self._add_security_headers(response)

        return response

    def _is_cdn_request(self, request: Request) -> bool:
        """Check if request is coming through CDN"""
        cdn_headers = [
            "CF-Ray",  # Cloudflare
            "X-Amz-Cf-Id",  # CloudFront
            "X-CDN-Forwarded-For",  # Generic CDN
            "X-Pull-Request-Id",  # Google Cloud CDN
        ]

        return any(header in request.headers for header in cdn_headers)

    async def _apply_cache_headers(self, request: Request, response: Response):
        """Apply appropriate cache headers"""
        # Skip caching for authenticated endpoints
        if "authorization" in request.headers and "/public/" not in str(request.url):
            response.headers["Cache-Control"] = "private, no-cache"
            return

        # Get content type
        content_type = response.headers.get("content-type", "text/plain")

        # Get cache headers from CDN config
        cache_headers = cdn_config.get_cache_headers(
            content_type=content_type, path=str(request.url.path)
        )

        # Apply headers
        for header, value in cache_headers.items():
            response.headers[header] = value

        # Add Last-Modified if not present
        if "Last-Modified" not in response.headers:
            response.headers["Last-Modified"] = datetime.utcnow().strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

    def _should_compress(self, request: Request, response: Response) -> bool:
        """Determine if response should be compressed"""
        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        if not ("gzip" in accept_encoding or "br" in accept_encoding):
            return False

        # Check if already compressed
        if "content-encoding" in response.headers:
            return False

        # Check content type
        content_type = response.headers.get("content-type", "")
        if not cdn_config.should_compress(content_type, len(response.body)):
            return False

        # Check size threshold
        if len(response.body) < self.min_compress_size:
            return False

        return True

    async def _compress_response(
        self, request: Request, response: Response
    ) -> Response:
        """Compress response body"""
        accept_encoding = request.headers.get("accept-encoding", "")
        body = response.body

        # Prefer Brotli if supported
        if "br" in accept_encoding and hasattr(brotli, "compress"):
            compressed = brotli.compress(body, quality=self.compression_level["br"])
            encoding = "br"
        # Fallback to gzip
        elif "gzip" in accept_encoding:
            compressed = gzip.compress(
                body, compresslevel=self.compression_level["gzip"]
            )
            encoding = "gzip"
        else:
            return response

        # Only use compression if it reduces size
        if len(compressed) >= len(body):
            return response

        # Update response
        response.body = compressed
        response.headers["Content-Encoding"] = encoding
        response.headers["Content-Length"] = str(len(compressed))

        # Add Vary header
        vary = response.headers.get("Vary", "")
        if vary:
            response.headers["Vary"] = f"{vary}, Accept-Encoding"
        else:
            response.headers["Vary"] = "Accept-Encoding"

        logger.debug(
            f"Compressed response: {len(body)} -> {len(compressed)} bytes ({encoding})"
        )

        return response

    def _add_cdn_headers(self, response: Response, is_cdn_request: bool):
        """Add CDN-specific headers"""
        if is_cdn_request:
            response.headers["X-Served-By"] = "CDN"
            response.headers["X-Cache"] = (
                "HIT" if response.status_code == 304 else "MISS"
            )
        else:
            response.headers["X-Served-By"] = "Origin"

        # Add timing header
        response.headers["X-Response-Time"] = str(getattr(response, "process_time", 0))

    def _add_security_headers(self, response: Response):
        """Add security headers"""
        # Content Security Policy
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' wss: https:; "
                "frame-ancestors 'none';"
            )

        # Other security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )


class ImageOptimizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for on-the-fly image optimization
    """

    def __init__(self, app):
        super().__init__(app)
        self.image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process image requests with optimization
        """
        # Check if this is an image request
        path = str(request.url.path)
        if not any(path.endswith(ext) for ext in self.image_extensions):
            return await call_next(request)

        # Check for optimization parameters
        params = dict(request.query_params)
        should_optimize = any(param in params for param in ["w", "h", "q", "f"])

        if not should_optimize:
            return await call_next(request)

        # Process original response
        response = await call_next(request)

        # Only optimize successful responses
        if response.status_code != 200:
            return response

        # Get optimization parameters
        opt_params = {"resize_params": {}, "quality": None, "target_format": None}

        if "w" in params:
            opt_params["resize_params"]["max_width"] = int(params["w"])
        if "h" in params:
            opt_params["resize_params"]["max_height"] = int(params["h"])
        if "q" in params:
            opt_params["quality"] = int(params["q"])
        if "f" in params:
            opt_params["target_format"] = params["f"]

        # Determine format from Accept header if not specified
        if not opt_params["target_format"]:
            accept = request.headers.get("accept", "")
            user_agent = request.headers.get("user-agent", "")

            format_params = cdn_config.get_image_optimization_params(
                accept, user_agent, path.split(".")[-1]
            )
            opt_params["target_format"] = format_params.get("format")

        try:
            # Optimize image
            optimized_data, output_format = await image_optimizer.optimize_image(
                image_data=response.body,
                source_format=path.split(".")[-1],
                **opt_params,
            )

            # Update response
            response.body = optimized_data
            response.headers["Content-Type"] = f"image/{output_format}"
            response.headers["Content-Length"] = str(len(optimized_data))

            # Add optimization headers
            response.headers["X-Image-Optimized"] = "true"
            response.headers["X-Original-Size"] = str(len(response.body))
            response.headers["X-Optimized-Size"] = str(len(optimized_data))

            logger.debug(f"Image optimized: {path} -> {output_format}")

        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            # Return original on failure

        return response


class ETAGMiddleware(BaseHTTPMiddleware):
    """
    Middleware for ETag generation and validation
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Handle ETag generation and validation
        """
        # Check for If-None-Match header
        if_none_match = request.headers.get("if-none-match")

        # Process request
        response = await call_next(request)

        # Only process successful GET requests
        if request.method != "GET" or response.status_code != 200:
            return response

        # Skip if ETag already present
        if "etag" in response.headers:
            # Validate existing ETag
            if if_none_match and if_none_match == response.headers["etag"]:
                return Response(status_code=304, headers=dict(response.headers))
            return response

        # Generate ETag for cacheable content
        content_type = response.headers.get("content-type", "")
        if self._should_generate_etag(content_type, len(response.body)):
            # Generate ETag from content
            etag = self._generate_etag(response.body)
            response.headers["ETag"] = f'"{etag}"'

            # Check if client has matching ETag
            if if_none_match == f'"{etag}"':
                return Response(status_code=304, headers=dict(response.headers))

        return response

    def _should_generate_etag(self, content_type: str, content_length: int) -> bool:
        """Determine if ETag should be generated"""
        # Don't generate for large files (> 10MB)
        if content_length > 10 * 1024 * 1024:
            return False

        # Generate for common cacheable types
        cacheable_types = [
            "application/json",
            "text/html",
            "text/css",
            "application/javascript",
            "image/",
        ]

        return any(content_type.startswith(ct) for ct in cacheable_types)

    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag from content"""
        return hashlib.md5(content).hexdigest()


def setup_cdn_middleware(app):
    """
    Setup all CDN-related middleware
    """
    # Order matters - compression should be last
    app.add_middleware(ETAGMiddleware)
    app.add_middleware(ImageOptimizationMiddleware)
    app.add_middleware(
        CDNMiddleware,
        enable_compression=True,
        enable_caching=True,
        enable_image_optimization=True,
    )
