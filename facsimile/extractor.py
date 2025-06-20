"""
Facsimile data extraction from ALTO XML files.

This module handles parsing ALTO XML files to extract spatial coordinates
and zone information for text regions, lines, and individual words.
"""

from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

from .models import FacsimileZone, PageFacsimile


class FacsimileExtractor:
    """Extract facsimile information from ALTO files"""
    
    def __init__(self, alto_namespace: str = 'http://www.loc.gov/standards/alto/ns-v4#'):
        """Initialize extractor with ALTO namespace"""
        self.alto_ns = {'alto': alto_namespace}
    
    def extract_page_facsimile(self, alto_file: Path, page_number: int) -> PageFacsimile:
        """Extract all facsimile zones from an ALTO file
        
        Args:
            alto_file: Path to the ALTO XML file
            page_number: Sequential page number for ID generation
            
        Returns:
            PageFacsimile object containing all extracted zones
            
        Raises:
            ValueError: If ALTO XML cannot be parsed or is invalid
        """
        tree = ET.parse(alto_file)
        root = tree.getroot()
        
        # Get page info
        page_elem = root.find('.//alto:Page', self.alto_ns)
        if page_elem is None:
            raise ValueError(f"No Page element found in {alto_file}")
        
        # Source image
        filename_elem = root.find('.//alto:sourceImageInformation/alto:fileName', self.alto_ns)
        source_image = filename_elem.text if filename_elem is not None else f"page_{page_number}.jpg"
        
        # Page dimensions
        width = int(float(page_elem.get('WIDTH', '0')))
        height = int(float(page_elem.get('HEIGHT', '0')))
        page_id = f"facs_page_{page_number}"
        
        zones = []
        
        # Extract TextBlock zones
        textblocks = root.findall('.//alto:TextBlock', self.alto_ns)
        for i, textblock in enumerate(textblocks):
            block_zone = self._extract_zone_from_element(
                textblock, f"facs_block_{page_number}_{i+1}", 'textblock'
            )
            if block_zone:
                zones.append(block_zone)
            
            # Extract TextLine zones within this block
            textlines = textblock.findall('.//alto:TextLine', self.alto_ns)
            for j, textline in enumerate(textlines):
                line_zone = self._extract_zone_from_element(
                    textline, f"facs_line_{page_number}_{i+1}_{j+1}", 'textline'
                )
                if line_zone:
                    # Add baseline if available
                    baseline = textline.get('BASELINE')
                    if baseline:
                        line_zone.baseline = baseline
                    zones.append(line_zone)
                
                # Extract String zones (word-level) - optional
                strings = textline.findall('.//alto:String', self.alto_ns)
                for k, string in enumerate(strings):
                    string_zone = self._extract_zone_from_element(
                        string, f"facs_string_{page_number}_{i+1}_{j+1}_{k+1}", 'string'
                    )
                    if string_zone:
                        zones.append(string_zone)
        
        return PageFacsimile(page_id, page_number, source_image, width, height, zones)
    
    def _extract_zone_from_element(self, element: ET.Element, zone_id: str, zone_type: str) -> Optional[FacsimileZone]:
        """Extract zone coordinates from ALTO element
        
        Args:
            element: ALTO XML element (TextBlock, TextLine, String)
            zone_id: Unique identifier for this zone
            zone_type: Type of zone ('textblock', 'textline', 'string')
            
        Returns:
            FacsimileZone object or None if coordinates are missing
        """
        hpos = element.get('HPOS')
        vpos = element.get('VPOS')
        width = element.get('WIDTH')
        height = element.get('HEIGHT')
        
        if not all([hpos, vpos, width, height]):
            return None
        
        ulx = int(float(hpos))
        uly = int(float(vpos))
        lrx = ulx + int(float(width))
        lry = uly + int(float(height))
        
        # Extract polygon if available for more precise boundaries
        polygon = None
        shape_elem = element.find('alto:Shape', self.alto_ns)
        if shape_elem is not None:
            polygon_elem = shape_elem.find('alto:Polygon', self.alto_ns)
            if polygon_elem is not None:
                polygon = polygon_elem.get('POINTS')
        
        return FacsimileZone(
            id=zone_id,
            ulx=ulx, uly=uly, lrx=lrx, lry=lry,
            zone_type=zone_type,
            element_id=element.get('ID'),
            polygon=polygon
        )