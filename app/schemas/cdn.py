"""
CDN Schemas
Pydantic models for CDN operations
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class ImageOptimizationRequest(BaseModel):
    """Request for image optimization"""

    source_url: HttpUrl = Field(..., description="Source image URL")
    width: Optional[int] = Field(None, ge=1, le=5000, description="Target width")
    height: Optional[int] = Field(None, ge=1, le=5000, description="Target height")
    quality: Optional[int] = Field(85, ge=1, le=100, description="Output quality")
    format: Optional[str] = Field(
        None, description="Output format (webp, avif, jpeg, png)"
    )
    fit: Optional[str] = Field(
        "contain", description="Fit mode (contain, cover, fill, inside, outside)"
    )


class ImageOptimizationResponse(BaseModel):
    """Response for image optimization"""

    original_size: int = Field(..., description="Original file size in bytes")
    optimized_size: int = Field(..., description="Optimized file size in bytes")
    format: str = Field(..., description="Output format")
    width: Optional[int] = Field(None, description="Output width")
    height: Optional[int] = Field(None, description="Output height")
    cdn_url: HttpUrl = Field(..., description="CDN URL for optimized image")
    storage_url: HttpUrl = Field(..., description="Storage URL")
    compression_ratio: float = Field(..., description="Compression ratio achieved")


class CacheInvalidationRequest(BaseModel):
    """Request for cache invalidation"""

    paths: List[str] = Field(
        ..., min_items=1, max_items=100, description="Paths to invalidate"
    )
    invalidate_children: bool = Field(False, description="Invalidate child paths")


class CacheInvalidationResponse(BaseModel):
    """Response for cache invalidation"""

    success: bool = Field(..., description="Whether invalidation was successful")
    invalidated_count: int = Field(..., description="Number of paths invalidated")
    operation_id: Optional[str] = Field(None, description="Operation ID for tracking")
    message: str = Field(..., description="Status message")


class CDNStatsResponse(BaseModel):
    """CDN usage statistics"""

    cache_hit_ratio: float = Field(..., ge=0, le=1, description="Cache hit ratio")
    bandwidth_saved_gb: float = Field(..., description="Bandwidth saved in GB")
    requests_served: int = Field(..., description="Total requests served")
    avg_response_time_ms: float = Field(
        ..., description="Average response time in milliseconds"
    )
    top_cached_paths: List[str] = Field(..., description="Most frequently cached paths")
    cost_saved_usd: float = Field(..., description="Estimated cost savings in USD")
    period: str = Field(..., description="Statistics period")


class SrcSetResponse(BaseModel):
    """Response for srcset generation"""

    srcset: str = Field(..., description="Srcset attribute value")
    sizes: str = Field(..., description="Sizes attribute value")
    src: HttpUrl = Field(..., description="Default src URL")


class EdgeConfigResponse(BaseModel):
    """Edge computing configuration"""

    edge_functions: Dict[str, Any] = Field(
        ..., description="Edge function configurations"
    )
    geo_routing: bool = Field(..., description="Whether geo-routing is enabled")
    custom_rules: List[Dict[str, Any]] = Field(
        default_factory=list, description="Custom edge rules"
    )


class PrefetchResponse(BaseModel):
    """Response for resource prefetch"""

    prefetch_links: List[str] = Field(..., description="Prefetch link headers")
    link_header: str = Field(..., description="Combined link header value")
    count: int = Field(..., description="Number of resources prefetched")


class CacheWarmingRequest(BaseModel):
    """Request for cache warming"""

    paths: List[str] = Field(
        ..., min_items=1, max_items=50, description="Paths to warm"
    )
    priority: str = Field("normal", description="Warming priority (low, normal, high)")


class CacheWarmingResponse(BaseModel):
    """Response for cache warming"""

    success: bool = Field(..., description="Whether warming was successful")
    warmed_count: int = Field(..., description="Number of paths warmed")
    failed_count: int = Field(..., description="Number of failures")
    failed_paths: List[str] = Field(
        default_factory=list, description="Paths that failed to warm"
    )
