"""
TEI facsimile section generation.

This module handles creation of TEI-compliant facsimile XML elements
from extracted spatial data, supporting various configuration options.
"""

from typing import List, Dict, Any
import xml.etree.ElementTree as ET

from .models import PageFacsimile, FacsimileZone


class FacsimileTEIGenerator:
    """Generate TEI facsimile elements from spatial data"""
    
    def create_facsimile_section(self, page_facsimiles: List[PageFacsimile], 
                               config: Dict[str, Any]) -> ET.Element:
        """Create complete facsimile section for TEI
        
        Args:
            page_facsimiles: List of PageFacsimile objects for all pages
            config: Configuration dictionary for facsimile generation
            
        Returns:
            TEI facsimile element containing all page surfaces and zones
        """
        facsimile = ET.Element('facsimile')
        
        for page_facs in page_facsimiles:
            surface = self._create_surface(page_facs, config)
            facsimile.append(surface)
        
        return facsimile
    
    def _create_surface(self, page_facs: PageFacsimile, config: Dict[str, Any]) -> ET.Element:
        """Create surface element for one page
        
        Args:
            page_facs: PageFacsimile object containing page data
            config: Configuration for surface generation
            
        Returns:
            TEI surface element with graphic and zones
        """
        surface = ET.Element('surface')
        surface.set('xml:id', page_facs.page_id)
        surface.set('source', page_facs.source_image)
        
        # Add graphic element if configured
        if config.get('include_graphic', True):
            graphic = ET.SubElement(surface, 'graphic')
            graphic.set('url', page_facs.source_image)
            graphic.set('width', str(page_facs.width))
            graphic.set('height', str(page_facs.height))
        
        # Filter zones based on configuration
        include_types = set()
        if config.get('include_textblocks', True):
            include_types.add('textblock')
        if config.get('include_textlines', True):
            include_types.add('textline')
        if config.get('include_strings', False):
            include_types.add('string')
        
        # Add zones
        for zone in page_facs.zones:
            if zone.zone_type in include_types:
                zone_elem = self._create_zone(zone, config)
                surface.append(zone_elem)
        
        return surface
    
    def _create_zone(self, zone: FacsimileZone, config: Dict[str, Any]) -> ET.Element:
        """Create zone element from FacsimileZone data
        
        Args:
            zone: FacsimileZone object with coordinate data
            config: Configuration for zone generation
            
        Returns:
            TEI zone element with coordinates and attributes
        """
        zone_elem = ET.Element('zone')
        zone_elem.set('xml:id', zone.id)
        zone_elem.set('ulx', str(zone.ulx))
        zone_elem.set('uly', str(zone.uly))
        zone_elem.set('lrx', str(zone.lrx))
        zone_elem.set('lry', str(zone.lry))
        zone_elem.set('type', zone.zone_type)
        
        # Add baseline for textlines if configured
        if zone.baseline and config.get('include_baselines', True):
            zone_elem.set('baseline', zone.baseline)
        
        # Add polygon for precise boundaries if configured
        if zone.polygon and config.get('use_polygons', True):
            zone_elem.set('points', zone.polygon)
        
        return zone_elem