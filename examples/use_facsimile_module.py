#!/usr/bin/env python3
"""
Example: Using the modularized facsimile module

This demonstrates how the extracted facsimile module can be used
independently for any ALTO to TEI conversion task.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import sys
sys.path.append('..')

from facsimile import FacsimileExtractor, FacsimileTEIGenerator


def extract_facsimile_from_alto_files(alto_directory: Path, output_file: Path):
    """Example: Extract facsimile data from multiple ALTO files"""
    
    # Initialize components
    extractor = FacsimileExtractor()
    generator = FacsimileTEIGenerator()
    
    # Configuration for facsimile generation
    config = {
        'include_graphic': True,
        'include_textblocks': True,
        'include_textlines': True,
        'include_strings': False,  # Skip word-level zones for performance
        'include_baselines': True,
        'use_polygons': True
    }
    
    # Extract facsimile data from all ALTO files
    page_facsimiles = []
    alto_files = sorted(alto_directory.glob('*.xml'))
    
    for i, alto_file in enumerate(alto_files, 1):
        print(f"Processing {alto_file.name}...")
        
        try:
            page_facs = extractor.extract_page_facsimile(alto_file, i)
            page_facsimiles.append(page_facs)
            print(f"  → Extracted {len(page_facs.zones)} zones")
        except Exception as e:
            print(f"  ⚠️ Warning: Could not process {alto_file}: {e}")
    
    # Generate TEI facsimile section
    print(f"\nGenerating TEI facsimile section...")
    facsimile_elem = generator.create_facsimile_section(page_facsimiles, config)
    
    # Create minimal TEI document
    tei_root = ET.Element('TEI')
    tei_root.set('xmlns', 'http://www.tei-c.org/ns/1.0')
    
    # Add facsimile section
    tei_root.append(facsimile_elem)
    
    # Add empty text section for valid TEI
    text_elem = ET.SubElement(tei_root, 'text')
    body_elem = ET.SubElement(text_elem, 'body')
    p_elem = ET.SubElement(body_elem, 'p')
    p_elem.text = "Facsimile-only TEI document"
    
    # Save to file
    tree = ET.ElementTree(tei_root)
    ET.indent(tree, space="  ", level=0)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding='unicode')
    
    print(f"✅ Facsimile TEI saved to {output_file}")
    print(f"   → {len(page_facsimiles)} pages")
    print(f"   → {sum(len(p.zones) for p in page_facsimiles)} total zones")


def standalone_facsimile_analysis(alto_file: Path):
    """Example: Analyze facsimile data from a single ALTO file"""
    
    extractor = FacsimileExtractor()
    
    print(f"Analyzing facsimile data in {alto_file}...")
    
    try:
        page_facs = extractor.extract_page_facsimile(alto_file, 1)
        
        print(f"📄 Page: {page_facs.source_image}")
        print(f"📐 Dimensions: {page_facs.width} × {page_facs.height}")
        print(f"🔍 Total zones: {len(page_facs.zones)}")
        
        # Analyze zone types
        zone_types = {}
        for zone in page_facs.zones:
            zone_types[zone.zone_type] = zone_types.get(zone.zone_type, 0) + 1
        
        print("\n📊 Zone breakdown:")
        for zone_type, count in zone_types.items():
            print(f"   {zone_type}: {count}")
        
        # Show some example zones
        print("\n🔍 Example zones:")
        for zone_type in zone_types:
            example = next(z for z in page_facs.zones if z.zone_type == zone_type)
            print(f"   {zone_type}: {example.id} at ({example.ulx},{example.uly})-({example.lrx},{example.lry})")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    # Example 1: Extract facsimile from directory of ALTO files
    print("=== Example 1: Extract Facsimile from ALTO Directory ===")
    alto_dir = Path('../alto_book')
    if alto_dir.exists():
        extract_facsimile_from_alto_files(alto_dir, Path('facsimile_only.xml'))
    else:
        print(f"Directory {alto_dir} not found")
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Analyze single ALTO file
    print("=== Example 2: Analyze Single ALTO File ===")
    sample_alto = Path('../alto_book/page_5.xml')
    if sample_alto.exists():
        standalone_facsimile_analysis(sample_alto)
    else:
        print(f"File {sample_alto} not found")