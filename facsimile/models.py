"""
Data models for facsimile processing.

This module defines the core data structures used for representing
spatial information extracted from ALTO XML files.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FacsimileZone:
    """Represents a facsimile zone with coordinates and metadata"""
    id: str
    ulx: int  # upper-left x
    uly: int  # upper-left y
    lrx: int  # lower-right x
    lry: int  # lower-right y
    zone_type: str  # 'textblock', 'textline', 'string'
    element_id: Optional[str] = None
    baseline: Optional[str] = None
    polygon: Optional[str] = None


@dataclass
class PageFacsimile:
    """Represents facsimile data for one page"""
    page_id: str
    page_number: int
    source_image: str
    width: int
    height: int
    zones: List[FacsimileZone]