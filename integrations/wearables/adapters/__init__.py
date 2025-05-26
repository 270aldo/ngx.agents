"""
Wearable Device Adapters
Individual adapters for each supported device
"""

from .whoop import WHOOPAdapter
from .apple_health import AppleHealthAdapter

# from .oura import OuraAdapter  # Coming next
# from .garmin import GarminAdapter  # Coming next

__all__ = ["WHOOPAdapter", "AppleHealthAdapter"]
