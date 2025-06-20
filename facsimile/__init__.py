"""
Facsimile processing module for ALTO to TEI conversion.

This module handles extraction of spatial coordinates from ALTO XML files
and generation of TEI facsimile sections with precise text-image alignment.
"""

from .models import FacsimileZone, PageFacsimile
from .extractor import FacsimileExtractor
from .generator import FacsimileTEIGenerator

__all__ = [
    'FacsimileZone',
    'PageFacsimile', 
    'FacsimileExtractor',
    'FacsimileTEIGenerator'
]