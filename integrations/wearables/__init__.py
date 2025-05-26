"""
Wearable Device Integrations
Support for Apple Watch, WHOOP, Oura Ring, Garmin, and other devices
"""

from .service import WearableIntegrationService
from .normalizer import WearableDataNormalizer

__all__ = ["WearableIntegrationService", "WearableDataNormalizer"]
