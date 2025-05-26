"""
CDN and Asset Optimization Router
Handles image optimization, asset delivery, and CDN management
"""

import io
import os
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from fastapi import (
    APIRouter,
    Request,
    Response,
    HTTPException,
    Query,
    Depends,
    UploadFile,
    File,
)
from fastapi.responses import StreamingResponse, FileResponse
from PIL import Image

from app.schemas.cdn import (
    ImageOptimizationRequest,
    ImageOptimizationResponse,
    CacheInvalidationRequest,
    CacheInvalidationResponse,
    CDNStatsResponse,
)
from core.cdn_config import cdn_config, image_optimizer, cache_manager
from core.auth import get_current_user
from clients.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cdn", tags=["CDN"])


@router.get("/image/{path:path}")
async def get_optimized_image(
    request: Request,
    path: str,
    w: Optional[int] = Query(None, description="Width"),
    h: Optional[int] = Query(None, description="Height"),
    q: Optional[int] = Query(None, ge=1, le=100, description="Quality"),
    f: Optional[str] = Query(None, description="Format (webp, avif, jpeg, png)"),
    fit: Optional[str] = Query(
        "contain", description="Fit mode (contain, cover, fill)"
    ),
):
    """
    Get optimized image with on-the-fly processing

    Supports:
    - Format conversion (WebP, AVIF, JPEG, PNG)
    - Resizing with aspect ratio preservation
    - Quality adjustment
    - Responsive image generation
    """
    try:
        # Get original image from storage
        supabase = SupabaseClient()
        image_data = supabase.download_file(path)

        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")

        # Determine output format
        accept_header = request.headers.get("accept", "")
        user_agent = request.headers.get("user-agent", "")

        # Get optimization parameters
        opt_params = cdn_config.get_image_optimization_params(
            accept_header, user_agent, path.split(".")[-1]
        )

        # Override with query parameters
        if f:
            opt_params["format"] = f
        if q:
            opt_params["quality"] = q

        # Build resize parameters
        resize_params = {}
        if w:
            resize_params["max_width"] = w
        if h:
            resize_params["max_height"] = h

        # Optimize image
        optimized_data, output_format = await image_optimizer.optimize_image(
            image_data=image_data,
            source_format=path.split(".")[-1],
            target_format=opt_params.get("format"),
            resize_params=resize_params,
            quality=opt_params.get("quality"),
        )

        # Get cache headers
        cache_headers = await cache_manager.cache_response(
            response_data=optimized_data,
            content_type=f"image/{output_format}",
            path=f"/cdn/image/{path}",
            user_context=None,
        )

        # Create response
        return Response(
            content=optimized_data,
            media_type=f"image/{output_format}",
            headers={
                **cache_headers,
                "X-Image-Format": output_format,
                "X-Image-Optimized": "true",
                "Accept-CH": "DPR, Width, Viewport-Width",
                "Vary": "Accept, DPR, Width",
            },
        )

    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Image optimization failed")


@router.post("/optimize", response_model=ImageOptimizationResponse)
async def optimize_uploaded_image(
    file: UploadFile = File(...),
    width: Optional[int] = Query(None),
    height: Optional[int] = Query(None),
    quality: Optional[int] = Query(85, ge=1, le=100),
    format: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Optimize uploaded image and store in CDN
    """
    try:
        # Read uploaded file
        image_data = await file.read()

        # Get file extension
        ext = file.filename.split(".")[-1].lower()

        # Optimize image
        resize_params = {}
        if width:
            resize_params["max_width"] = width
        if height:
            resize_params["max_height"] = height

        optimized_data, output_format = await image_optimizer.optimize_image(
            image_data=image_data,
            source_format=ext,
            target_format=format,
            resize_params=resize_params,
            quality=quality,
        )

        # Generate unique filename
        timestamp = datetime.utcnow().timestamp()
        optimized_filename = (
            f"optimized/{current_user['id']}/{timestamp}.{output_format}"
        )

        # Upload to storage
        supabase = SupabaseClient()
        url = supabase.upload_file(optimized_data, optimized_filename)

        # Get CDN URL
        cdn_url = cdn_config.get_cdn_url(f"/images/{optimized_filename}")

        # Get metadata
        metadata = image_optimizer.get_image_metadata(optimized_data)

        return ImageOptimizationResponse(
            original_size=len(image_data),
            optimized_size=len(optimized_data),
            format=output_format,
            width=metadata.get("width"),
            height=metadata.get("height"),
            cdn_url=cdn_url,
            storage_url=url,
            compression_ratio=round(len(optimized_data) / len(image_data), 2),
        )

    except Exception as e:
        logger.error(f"Image upload optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Image optimization failed")


@router.get("/srcset/{path:path}")
async def generate_srcset(
    path: str,
    widths: str = Query(
        "320,640,768,1024,1366,1920", description="Comma-separated widths"
    ),
):
    """
    Generate srcset URLs for responsive images
    """
    try:
        width_list = [int(w.strip()) for w in widths.split(",")]

        # Generate srcset
        srcset = cdn_config.get_srcset_urls(f"/images/{path}", width_list)

        # Also generate sizes recommendation
        sizes = [
            "(max-width: 320px) 320px",
            "(max-width: 640px) 640px",
            "(max-width: 768px) 768px",
            "(max-width: 1024px) 1024px",
            "(max-width: 1366px) 1366px",
            "1920px",
        ]

        return {
            "srcset": srcset,
            "sizes": ", ".join(sizes),
            "src": cdn_config.get_cdn_url(f"/images/{path}", {"w": width_list[-1]}),
        }

    except Exception as e:
        logger.error(f"Srcset generation failed: {e}")
        raise HTTPException(status_code=500, detail="Srcset generation failed")


@router.post("/invalidate", response_model=CacheInvalidationResponse)
async def invalidate_cache(
    request: CacheInvalidationRequest, current_user: dict = Depends(get_current_user)
):
    """
    Invalidate CDN cache for specific paths
    Requires admin privileges
    """
    # Check admin privileges
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Perform cache invalidation
        result = cdn_config.invalidate_cache(request.paths)

        if result["success"]:
            return CacheInvalidationResponse(
                success=True,
                invalidated_count=result["paths_invalidated"],
                operation_id=result["operation_id"],
                message="Cache invalidation initiated",
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(status_code=500, detail="Cache invalidation failed")


@router.get("/stats", response_model=CDNStatsResponse)
async def get_cdn_stats(current_user: dict = Depends(get_current_user)):
    """
    Get CDN usage statistics
    """
    try:
        # This would integrate with Cloud CDN monitoring API
        # For now, return mock data
        return CDNStatsResponse(
            cache_hit_ratio=0.85,
            bandwidth_saved_gb=1250.5,
            requests_served=1_500_000,
            avg_response_time_ms=45,
            top_cached_paths=[
                "/static/js/app.bundle.js",
                "/static/css/main.css",
                "/images/logo.webp",
            ],
            cost_saved_usd=125.50,
            period="last_30_days",
        )

    except Exception as e:
        logger.error(f"Failed to get CDN stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve CDN statistics")


@router.get("/prefetch")
async def prefetch_resources(
    urls: List[str] = Query(..., description="URLs to prefetch")
):
    """
    Trigger CDN prefetch for specific resources
    """
    try:
        # Generate prefetch hints
        prefetch_links = []
        for url in urls:
            cdn_url = cdn_config.get_cdn_url(url)
            prefetch_links.append(f"<{cdn_url}>; rel=prefetch")

        return {
            "prefetch_links": prefetch_links,
            "link_header": ", ".join(prefetch_links),
            "count": len(urls),
        }

    except Exception as e:
        logger.error(f"Prefetch generation failed: {e}")
        raise HTTPException(status_code=500, detail="Prefetch generation failed")


@router.get("/edge-config")
async def get_edge_configuration(current_user: dict = Depends(get_current_user)):
    """
    Get edge computing configuration
    Requires admin privileges
    """
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    return cdn_config.get_edge_config()


@router.post("/warm-cache")
async def warm_cache(
    paths: List[str] = Query(..., description="Paths to warm in cache"),
    current_user: dict = Depends(get_current_user),
):
    """
    Pre-warm CDN cache with specific paths
    """
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        warmed_count = 0
        failed_paths = []

        for path in paths:
            try:
                # Trigger a request to warm the cache
                # In production, this would use Cloud CDN API
                cdn_url = cdn_config.get_cdn_url(path)
                warmed_count += 1
            except Exception as e:
                failed_paths.append(path)
                logger.error(f"Failed to warm cache for {path}: {e}")

        return {
            "success": True,
            "warmed_count": warmed_count,
            "failed_count": len(failed_paths),
            "failed_paths": failed_paths,
        }

    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        raise HTTPException(status_code=500, detail="Cache warming failed")
