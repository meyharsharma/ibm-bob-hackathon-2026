"""
The Time Machine - A 3D visualization that renders git repositories as living cities.

This package provides tools to:
- Ingest git repositories and parse their history
- Generate 3D city visualizations where files are buildings
- Animate the city through time showing repository evolution
- Generate AI-powered narration using IBM Watson/Bob
"""

__version__ = "0.1.0"
__author__ = "IBM Bob Hackathon Team"

from .ingestion import RepositoryIngester
from .city import CityGenerator
from .rendering import CityRenderer
from .narration import NarrationGenerator

__all__ = [
    "RepositoryIngester",
    "CityGenerator",
    "CityRenderer",
    "NarrationGenerator",
]

# Made with Bob
