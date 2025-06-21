#!/usr/bin/env python3
"""
Convert eScriptorium ALTO XML output to complete TEI book format

This module processes entire books by using METS.xml to determine page order
and handles cross-page content like paragraphs spanning multiple pages.
It extends the functionality of alto2tei.py for book-level processing.
"""

import xml.etree.ElementTree as ET
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from alto2tei import AltoToTeiConverter

# Import facsimile module
from facsimile import FacsimileExtractor, FacsimileTEIGenerator


# Constants
ALTO_NAMESPACE = 'http://www.loc.gov/standards/alto/ns-v4#'
TEI_NAMESPACE = 'http://www.tei-c.org/ns/1.0'
DEFAULT_BOOK_CONFIG = 'config/alto_book_mapping.yaml'
DEFAULT_TEI_CONFIG = 'config/alto_tei_mapping.yaml'
# Processing Constants  
TEI_XMLNS_ATTRIBUTE = 'http://www.tei-c.org/ns/1.0'
METS_USE_EXPORT = 'export'
XLINK_HREF_ATTRIBUTE = '{http://www.w3.org/1999/xlink}href'


# Custom Exceptions
class AltoBookConversionError(Exception):
    """Base exception for ALTO book conversion errors"""
    pass


class MetsParsingError(AltoBookConversionError):
    """Raised when METS.xml parsing fails"""
    pass


class PageProcessingError(AltoBookConversionError):
    """Raised when individual page processing fails"""
    pass


class FacsimileProcessingError(AltoBookConversionError):
    """Raised when facsimile extraction fails"""
    pass




class MetsParser:
    """Parse METS.xml files to extract page order and book metadata"""

    def __init__(self, mets_path: Path):
        self.mets_path = mets_path
        self.mets_ns = {'mets': 'http://www.loc.gov/METS/',
                       'xlink': 'http://www.w3.org/1999/xlink'}
        self._pages = None
        self._metadata = None

    def get_page_order(self) -> List[str]:
        """Get ordered list of ALTO XML filenames from METS.xml
        
        Returns:
            List of ALTO XML filenames in document order
            
        Raises:
            MetsParsingError: If METS.xml cannot be parsed or is invalid
        """
        if self._pages is None:
            self._parse_mets()
        return self._pages

    def get_book_metadata(self) -> Dict[str, Any]:
        """Extract book metadata from METS.xml"""
        if self._metadata is None:
            self._parse_mets()
        return self._metadata

    def _parse_mets(self) -> None:
        """Parse METS.xml and extract page order and metadata"""
        try:
            tree = ET.parse(self.mets_path)
            root = tree.getroot()

            # Extract page order from fileSec
            pages = []
            file_grp = root.find(f'.//mets:fileGrp[@USE="{METS_USE_EXPORT}"]', self.mets_ns)
            if file_grp is not None:
                for file_elem in file_grp.findall('mets:file', self.mets_ns):
                    flocat = file_elem.find('mets:FLocat', self.mets_ns)
                    if flocat is not None:
                        # Try both the namespaced and non-namespaced attribute
                        href = flocat.get(XLINK_HREF_ATTRIBUTE) or flocat.get('href')
                        if href and href.endswith('.xml'):
                               pages.append(href)

            self._pages = pages

            # Extract basic metadata (can be expanded later)
            self._metadata = {
                'total_pages': len(pages),
                'source_file': str(self.mets_path),
                'first_page': pages[0] if pages else None,
                'last_page': pages[-1] if pages else None
            }

        except ET.ParseError as e:
            raise MetsParsingError(f"Invalid XML in {self.mets_path}: {e}") from e
        except FileNotFoundError as e:
            raise MetsParsingError(f"METS file not found: {self.mets_path}") from e
        except Exception as e:
            raise MetsParsingError(f"Unexpected error parsing METS.xml: {e}") from e


class AltoBookToTeiConverter(AltoToTeiConverter):
    """Convert multiple ALTO files to a single TEI book using METS.xml for ordering
    
    This converter extends AltoToTeiConverter to handle book-level processing including:
    - Page ordering via METS.xml parsing
    - Cross-page content merging
    - Facsimile zone extraction and linking
    - Book-level TEI structure generation
    
    Attributes:
        mets_path: Path to METS.xml file
        merge_lines: Whether to merge lines into paragraphs
        enable_facsimile: Whether to extract spatial coordinates
        pages_data: List of processed page data
        page_facsimiles: List of extracted facsimile data (if enabled)
    """

    def __init__(self, mets_path: Path, merge_lines: bool = True, enable_facsimile: bool = True):
        # Use the line type configuration for the parent class (AltoToTeiConverter)
        super().__init__("config/alto_tei_mapping.yaml")
        self.mets_path = mets_path
        self.mets_parser = MetsParser(mets_path)
        self.pages_data = []
        self.merge_lines = merge_lines
        self.enable_facsimile = enable_facsimile

        # Note: book configuration is now handled through the rule engine's YAML config

        # Initialize facsimile components
        if self.enable_facsimile:
            self.facsimile_extractor = FacsimileExtractor()
            self.facsimile_generator = FacsimileTEIGenerator()
            self.page_facsimiles = []
            self.zone_mapping = {}  # Maps ALTO element IDs to facsimile zone IDs

    def convert_book_to_tei(self, output_file: Path) -> None:
        """Convert entire book to TEI format"""
        try:
            book_metadata = self._get_book_metadata_and_validate()
            self._extract_facsimiles_if_enabled() 
            self._process_all_pages_in_order()
            book_tei = self._create_and_clean_book_tei(book_metadata)
            self._save_tei_with_success_message(book_tei, output_file)
        except Exception as e:
            raise AltoBookConversionError(f"Book conversion failed: {e}") from e

    def _get_book_metadata_and_validate(self) -> Dict[str, Any]:
        """Get book metadata and validate setup"""
        page_files = self.mets_parser.get_page_order()
        book_metadata = self.mets_parser.get_book_metadata()
        
        print(f"📚 Converting book with {len(page_files)} pages...")
        print(f"First page: {book_metadata.get('first_page', 'Unknown')}")
        print(f"Last page: {book_metadata.get('last_page', 'Unknown')}")
        
        return book_metadata

    def _extract_facsimiles_if_enabled(self) -> None:
        """Extract facsimile data if enabled"""
        if self.enable_facsimile:
            print("🗺️  Extracting facsimile data...")
            self._extract_all_facsimiles()

    def _process_all_pages_in_order(self) -> None:
        """Process each page according to METS order"""
        page_files = self.mets_parser.get_page_order()
        mets_dir = self.mets_path.parent
        
        for i, page_file in enumerate(page_files, 1):
            self._process_single_page(page_file, i, mets_dir)

    def _process_single_page(self, page_file: str, page_number: int, mets_dir: Path) -> None:
        """Process a single page file"""
        page_path = mets_dir / page_file
        if not page_path.exists():
            print(f"⚠️  Warning: Page file not found: {page_path}")
            return
            
        print(f"Processing page {page_number}/{len(self.mets_parser.get_page_order())}: {page_file}")
        
        try:
            # Use merged content if line merging is enabled
            if self.merge_lines:
                page_tei = self._convert_page_with_merged_lines(page_path, page_number)
            else:
                page_tei = self.convert_alto_to_tei(page_path)
            
            self.pages_data.append({
                'filename': page_file,
                'page_number': page_number,
                'tei_content': page_tei
            })
        except Exception as e:
            raise PageProcessingError(f"Failed to process {page_file}: {e}") from e

    def _create_and_clean_book_tei(self, book_metadata: Dict[str, Any]) -> ET.Element:
        """Create complete book TEI and clean attributes"""
        try:
            book_tei = self._create_book_tei(book_metadata)
            self._clean_none_attributes(book_tei)
            return book_tei
        except Exception as e:
            raise AltoBookConversionError(f"TEI creation failed: {e}") from e

    def _save_tei_with_success_message(self, book_tei: ET.Element, output_file: Path) -> None:
        """Save TEI file and display appropriate success message"""
        try:
            self.save_tei(book_tei, output_file)
            
            if self.enable_facsimile:
                print(f"✅ Book conversion complete with facsimile data! Saved to {output_file}")
            else:
                print(f"✅ Book conversion complete! Saved to {output_file}")
        except Exception as e:
            raise AltoBookConversionError(f"Failed to save to {output_file}: {e}") from e

    def _clean_none_attributes(self, element: ET.Element) -> None:
        """Remove None attribute values from XML element and its children"""
        if element is None:
            return

        # Clean attributes of current element
        if element.attrib:
            # Find keys with None values
            none_keys = [key for key, value in element.attrib.items() if value is None]
            # Remove None attributes
            for key in none_keys:
                del element.attrib[key]

        # Recursively clean children
        for child in element:
            self._clean_none_attributes(child)

    def _extract_all_facsimiles(self) -> None:
        """Extract facsimile data from all ALTO files
        
        Processes each ALTO file to extract spatial coordinates and builds
        zone mapping for text-to-image linking. Gracefully handles missing
        or malformed files with warnings.
        
        Raises:
            FacsimileProcessingError: If critical facsimile extraction fails
        """
        if not self.enable_facsimile:
            return

        page_files = self.mets_parser.get_page_order()
        mets_dir = self.mets_path.parent

        for i, page_file in enumerate(page_files, 1):
            page_path = mets_dir / page_file
            if page_path.exists():
                try:
                    page_facs = self.facsimile_extractor.extract_page_facsimile(page_path, i)
                    self.page_facsimiles.append(page_facs)

                    # Build zone mapping for linking
                    for zone in page_facs.zones:
                        if zone.element_id:
                            self.zone_mapping[zone.element_id] = zone.id

                except Exception as e:
                    print(f"⚠️  Warning: Could not extract facsimile from {page_file}: {e}")

        print(f"📐 Extracted facsimile data for {len(self.page_facsimiles)} pages with {len(self.zone_mapping)} zones")

    def _get_facsimile_config(self) -> Dict[str, Any]:
        """Get facsimile configuration from YAML rule engine"""
        return self.rule_engine.get_book_facsimile_config()

    def _create_book_tei(self, metadata: Dict[str, Any]) -> ET.Element:
        """Create complete TEI book structure from processed pages"""

        # Create TEI root element
        tei_root = ET.Element('TEI')
        tei_root.set('xmlns', self.tei_ns)

        # Create TEI header
        tei_header = self._create_book_header(metadata)
        tei_root.append(tei_header)

        # Add facsimile section if enabled
        if self.enable_facsimile and self.page_facsimiles:
            facsimile_config = self._get_facsimile_config()
            facsimile = self.facsimile_generator.create_facsimile_section(self.page_facsimiles, facsimile_config)
            tei_root.append(facsimile)
            print(f"📋 Added facsimile section with {len(self.page_facsimiles)} surfaces")

        # Create text element
        text_elem = ET.SubElement(tei_root, 'text')
        body_elem = ET.SubElement(text_elem, 'body')

        # Create book div if configured
        book_structure = self.rule_engine.get_book_structure_config()
        if book_structure.get('create_book_div', True):
            book_div = ET.SubElement(body_elem, 'div')
            book_div.set('type', book_structure.get('div_type', 'book'))
        else:
            book_div = body_elem

        # Process and combine all pages with cross-page paragraph merging
        if self.merge_lines:
            if self.enable_facsimile:
                self._add_pages_with_cross_page_merging_and_facsimile(book_div)
            else:
                self._add_pages_with_cross_page_paragraph_merging(book_div)
        else:
            # Original behavior: process pages separately
            for page_data in self.pages_data:
                if self.enable_facsimile:
                    self._add_page_to_book_with_facsimile(book_div, page_data)
                else:
                    self._add_page_to_book(book_div, page_data)

        return tei_root

    def _create_book_header(self, metadata: Dict[str, Any]) -> ET.Element:
        """Create TEI header for the complete book"""

        header = ET.Element('teiHeader')

        # File description
        file_desc = ET.SubElement(header, 'fileDesc')

        # Title statement
        title_stmt = ET.SubElement(file_desc, 'titleStmt')
        title_elem = ET.SubElement(title_stmt, 'title')

        # Use configured title template or fallback
        book_structure = self.rule_engine.get_book_structure_config()
        title_template = book_structure.get('header_title_template', 'Book converted from ALTO (pages 1-{total_pages})')
        total_pages = metadata.get('total_pages', 'unknown')
        title_elem.text = title_template.format(total_pages=total_pages, first_page=1, last_page=total_pages)

        # Publication statement
        pub_stmt = ET.SubElement(file_desc, 'publicationStmt')
        pub_elem = ET.SubElement(pub_stmt, 'p')
        total_pages = metadata.get('total_pages', 0)
        pub_elem.text = f"Converted from ALTO XML using alto2teibook.py - {total_pages} pages"

        # Source description
        source_desc = ET.SubElement(file_desc, 'sourceDesc')
        source_elem = ET.SubElement(source_desc, 'p')
        source_file = metadata.get('source_file', 'Unknown')
        source_elem.text = f"Source: {source_file}"

        return header

    def _create_page_break_element(self, page_data: Dict[str, Any]) -> ET.Element:
        """Create page break element using YAML-driven rule engine"""
        page_number = page_data['page_number']
        filename = page_data['filename']
        
        # Determine facsimile reference
        if self.enable_facsimile and self.page_facsimiles:
            page_index = page_number - 1
            if 0 <= page_index < len(self.page_facsimiles):
                page_facs = self.page_facsimiles[page_index]
                facs_ref = f'#{page_facs.page_id}'
            else:
                # Generate surface ID using rule engine patterns
                surface_id = self.rule_engine.generate_facsimile_id('surface', page_number)
                facs_ref = f'#{surface_id}'
        else:
            # Fallback to filename-based reference using configured extensions
            file_formats = self.rule_engine.get_file_formats_config()
            alto_ext = file_formats.get('alto_extension', '.xml')
            image_ext = file_formats.get('default_image_extension', '.jpeg')
            facs_ref = f"{filename.replace(alto_ext, '')}{image_ext}"
            
        # Use rule engine to create page break element
        return self.rule_engine.create_book_page_break(
            page_number, 
            facs_reference=facs_ref,
            filename=filename.replace('.xml', '')
        )

    def _add_page_to_book(self, book_div: ET.Element, page_data: Dict[str, Any]) -> None:
        """Add a single page's content to the book structure"""

        # Add page break element
        pb_elem = self._create_page_break_element(page_data)
        book_div.append(pb_elem)

        # Extract content from the page's TEI and add to book
        page_tei = page_data['tei_content']

        # Try to find body element with different approaches
        body = self._find_body_element(page_tei)

        if body is not None:
            # Copy all content from page body to book (except existing pb elements)
            for child in body:
                # Skip page break elements that are already in individual pages
                # as we add our own page breaks
                if self.rule_engine.should_skip_element(child.tag, self.tei_ns):
                    continue

                # Create a copy of the element to avoid moving from original tree
                copied_elem = self._copy_element_deep(child)
                book_div.append(copied_elem)
        else:
            # If no body found, add a comment indicating empty page
            comment = ET.Comment(f" Page {page_data['page_number']} ({page_data['filename']}): No content found ")
            book_div.append(comment)

    def _find_body_element(self, page_tei: ET.Element) -> Optional[ET.Element]:
        """Find body element in TEI using multiple fallback approaches"""
        # First try with namespace
        tei_ns_dict = {'tei': self.tei_ns}
        body = page_tei.find('.//tei:body', tei_ns_dict)

        # If not found, try without namespace (fallback)
        if body is None:
            body = page_tei.find('.//body')

        # If still not found, try with full namespace in tag
        if body is None:
            body = page_tei.find(f'.//{{{self.tei_ns}}}body')

        return body

    def _copy_element_deep(self, elem: ET.Element) -> ET.Element:
        """Create a deep copy of an XML element"""
        if elem is None:
            return None

        new_elem = ET.Element(elem.tag, elem.attrib)
        new_elem.text = elem.text
        new_elem.tail = elem.tail

        for child in elem:
            copied_child = self._copy_element_deep(child)
            if copied_child is not None:
                new_elem.append(copied_child)

        return new_elem

    def _add_pages_with_cross_page_merging(self, book_div: ET.Element) -> None:
        """Add all pages with cross-page paragraph merging"""

        # Process each page individually but allow paragraphs to continue across pages
        for i, page_data in enumerate(self.pages_data):
            # Add page break element at the start of each page (except first page)
            if i > 0:
                pb_elem = self._create_page_break_element(page_data)
                book_div.append(pb_elem)

            # Extract content from the page's TEI and add to book
            page_tei = page_data['tei_content']

            # Try to find body element with different approaches
            body = self._find_body_element(page_tei)

            if body is not None:
                # Copy all content from page body to book (except existing pb elements)
                for child in body:
                    # Skip page break elements that are already in individual pages
                    # as we add our own page breaks
                    if child.tag == 'pb' or child.tag.endswith('}pb'):
                        continue

                    # Create a copy of the element to avoid moving from original tree
                    copied_elem = self._copy_element_deep(child)
                    book_div.append(copied_elem)
            else:
                # If no body found, add a comment indicating empty page
                comment = ET.Comment(f" Page {page_data['page_number']} ({page_data['filename']}): No content found ")
                book_div.append(comment)

    def _add_page_to_book_with_facsimile(self, book_div: ET.Element, page_data: Dict[str, Any]) -> None:
        """Add a single page's content to the book structure with facsimile linking"""

        # Add page break element
        pb_elem = self._create_page_break_element(page_data)
        book_div.append(pb_elem)

        # Extract content from the page's TEI and add to book
        page_tei = page_data['tei_content']

        # Try to find body element with different approaches
        body = self._find_body_element(page_tei)

        if body is not None:
            # Copy all content from page body to book with facsimile enhancement
            for child in body:
                # Skip page break elements that are already in individual pages
                # as we add our own page breaks
                if self.rule_engine.should_skip_element(child.tag, self.tei_ns):
                    continue

                # Create a copy of the element and enhance with facsimile links
                copied_elem = self._copy_element_with_facsimile_links(child)
                book_div.append(copied_elem)
        else:
            # If no body found, add a comment indicating empty page
            comment = ET.Comment(f" Page {page_data['page_number']} ({page_data['filename']}): No content found ")
            book_div.append(comment)

    def _add_pages_with_cross_page_merging_and_facsimile(self, book_div: ET.Element) -> None:
        """Add all pages with cross-page paragraph merging and facsimile links"""

        # Process each page individually but allow paragraphs to continue across pages
        for i, page_data in enumerate(self.pages_data):
            # Add page break element at the start of each page (except first page)
            if i > 0:
                pb_elem = self._create_page_break_element(page_data)
                book_div.append(pb_elem)

            # Extract content from the page's TEI and add to book
            page_tei = page_data['tei_content']

            # Try to find body element with different approaches
            body = self._find_body_element(page_tei)

            if body is not None:
                # Copy all content from page body to book with facsimile enhancement
                for child in body:
                    # Skip page break elements that are already in individual pages
                    # as we add our own page breaks
                    if child.tag == 'pb' or child.tag.endswith('}pb'):
                        continue

                    # Create a copy of the element and enhance with facsimile links
                    copied_elem = self._copy_element_with_facsimile_links(child)
                    book_div.append(copied_elem)
            else:
                # If no body found, add a comment indicating empty page
                comment = ET.Comment(f" Page {page_data['page_number']} ({page_data['filename']}): No content found ")
                book_div.append(comment)

    def _copy_element_with_facsimile_links(self, elem: ET.Element) -> ET.Element:
        """Copy element and add facsimile references where possible"""
        if not self.enable_facsimile:
            return self._copy_element_deep(elem)

        new_elem = ET.Element(elem.tag, elem.attrib)
        new_elem.text = elem.text
        new_elem.tail = elem.tail

        # Try to add facsimile reference based on element type
        self._add_facsimile_reference(new_elem, elem)

        # Recursively copy children with facsimile enhancement
        for child in elem:
            copied_child = self._copy_element_with_facsimile_links(child)
            if copied_child is not None:
                new_elem.append(copied_child)

        return new_elem

    def _add_facsimile_reference(self, tei_elem: ET.Element, original_elem: ET.Element) -> None:
        """Add facsimile reference to TEI element if possible"""
        if not self.enable_facsimile or not self.zone_mapping:
            return

        # Try to find facsimile reference based on ALTO element ID
        alto_id = original_elem.get('ID')
        if alto_id and alto_id in self.zone_mapping:
            zone_id = self.zone_mapping[alto_id]
            tei_elem.set('facs', f'#{zone_id}')
            return

        # Note: getparent() is not available in standard ElementTree
        # Fallback facsimile linking would require additional element tracking

    def _add_pages_with_cross_page_paragraph_merging(self, book_div: ET.Element) -> None:
        """Add all pages with proper cross-page paragraph merging for clean text output"""
        
        # For merge-lines mode, we need to process content differently:
        # 1. Skip facsimile zones and special elements (signatures, running titles)
        # 2. Maintain paragraph state across pages
        # 3. Insert page breaks at their correct positions within text flow
        # 4. Handle paragraph continuation properly
        
        # Global state for cross-page paragraph handling
        current_paragraph = None
        paragraph_state = {
            'in_paragraph': False,
            'paragraph_started_explicitly': False
        }
        
        # Process each page in sequence
        for i, page_data in enumerate(self.pages_data):
            
            # Get the raw ALTO content for this page to process line by line
            alto_file = self.mets_path.parent / page_data['filename']
            page_elements = self._extract_merged_content_from_page(
                alto_file, page_data['page_number'], current_paragraph, paragraph_state, 
                add_page_break=(i > 0), page_data=page_data
            )
            
            # Update current_paragraph from the processing result
            if page_elements['current_paragraph'] is not None:
                current_paragraph = page_elements['current_paragraph']
                paragraph_state = page_elements['paragraph_state']
                
            # Add all elements except the current paragraph (we'll add it when complete)
            for elem in page_elements['completed_elements']:
                book_div.append(elem)
                
        # Add any remaining open paragraph at the end
        if current_paragraph is not None:
            book_div.append(current_paragraph)

    def _extract_merged_content_from_page(self, alto_file: Path, page_number: int, 
                                        current_paragraph: Optional[ET.Element],
                                        paragraph_state: Dict[str, bool],
                                        add_page_break: bool = False,
                                        page_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract content from a page with proper paragraph continuation handling"""
        
        # Parse ALTO file
        tree = ET.parse(alto_file)
        alto_root = tree.getroot()
        tags_mapping = self.parse_alto_tags(alto_root)
        
        # Find all text blocks
        textblocks = alto_root.findall('.//alto:TextBlock', self.alto_ns)
        
        completed_elements = []
        page_break_inserted = False
        
        # Process each text block
        for textblock in textblocks:
            block_type = self.get_block_type(textblock, tags_mapping)
            
            # In merge-lines mode, skip certain block types entirely
            if self._should_skip_block_in_merge_mode(block_type):
                continue
                
            # Process lines in this block
            textlines = textblock.findall('.//alto:TextLine', self.alto_ns)
            
            for textline in textlines:
                line_type = self.get_line_type(textline, tags_mapping)
                line_text = self.extract_text_from_line(textline).strip()
                
                if not line_text:  # Skip empty lines
                    continue
                
                # Insert page break before the first content line of this page (except first page)
                if add_page_break and not page_break_inserted:
                    if current_paragraph is not None:
                        # We're continuing a paragraph from the previous page
                        # Check if the current paragraph ends with a hyphen and remove it
                        # If no hyphen, add a space before the page break
                        had_hyphen = self._remove_trailing_hyphen_from_paragraph(current_paragraph)
                        if not had_hyphen:
                            # Add space before page break for word separation
                            self._add_space_to_paragraph_end(current_paragraph)
                        # Insert page break element within the current paragraph
                        pb_elem = self._create_page_break_element(page_data)
                        current_paragraph.append(pb_elem)
                        # The text will continue after the page break
                    else:
                        # No current paragraph - add page break as standalone element
                        pb_elem = self._create_page_break_element(page_data)
                        completed_elements.append(pb_elem)
                    
                    page_break_inserted = True
                
                # Generate line facsimile ID if needed
                line_facs_id = None
                if self.enable_facsimile:
                    # Use a simple line counter for facsimile IDs in merge mode
                    line_facs_id = f"facs_line_{page_number}_{len(completed_elements) + 1}_{len([l for l in textlines[:textlines.index(textline)+1] if self.extract_text_from_line(l).strip()])}"

                # Handle different line types for paragraph boundaries
                if line_type == 'CustomLine:paragraph_start':
                    # Explicit paragraph start - close current and start new
                    if current_paragraph is not None:
                        completed_elements.append(current_paragraph)
                    
                    current_paragraph = ET.Element('p')
                    if self.enable_facsimile:
                        # Add block-level facsimile reference
                        block_facs_id = f"facs_block_{page_number}_{len(completed_elements) + 1}"
                        current_paragraph.set('facs', f'#{block_facs_id}')
                    self._add_text_to_paragraph(current_paragraph, line_text, line_facs_id)
                    paragraph_state['in_paragraph'] = True
                    paragraph_state['paragraph_started_explicitly'] = True
                    
                elif line_type == 'HeadingLine':
                    # Headers end paragraphs
                    if current_paragraph is not None:
                        completed_elements.append(current_paragraph)
                        current_paragraph = None
                        paragraph_state['in_paragraph'] = False
                    
                    # Create header element
                    head_elem = ET.Element('head')
                    head_elem.text = line_text
                    completed_elements.append(head_elem)
                    
                else:
                    # Regular content line - add to current paragraph or start new one
                    if current_paragraph is None:
                        # No current paragraph - start a new implicit one
                        current_paragraph = ET.Element('p')
                        if self.enable_facsimile:
                            # Add block-level facsimile reference
                            block_facs_id = f"facs_block_{page_number}_{len(completed_elements) + 1}"
                            current_paragraph.set('facs', f'#{block_facs_id}')
                        self._add_text_to_paragraph(current_paragraph, line_text, line_facs_id)
                        paragraph_state['in_paragraph'] = True
                        paragraph_state['paragraph_started_explicitly'] = False
                    else:
                        # Add line break and continue existing paragraph
                        if self.enable_facsimile and line_facs_id:
                            lb = ET.SubElement(current_paragraph, 'lb')
                            lb.set('facs', f'#{line_facs_id}')
                        else:
                            # Add line break without facsimile
                            ET.SubElement(current_paragraph, 'lb')
                        # Add to existing paragraph
                        self._add_text_to_paragraph(current_paragraph, line_text, line_facs_id)
        
        return {
            'completed_elements': completed_elements,
            'current_paragraph': current_paragraph,
            'paragraph_state': paragraph_state
        }
    
    def _should_skip_block_in_merge_mode(self, block_type: str) -> bool:
        """Determine if a block type should be skipped in merge-lines mode"""
        # In merge-lines mode, we want clean text without facsimile zones or special elements
        skip_blocks = [
            'NumberingZone',  # Page numbers - we handle these separately
            'RunningTitleZone',  # Running titles
            'QuireMarksZone',  # Quire marks
            'GraphicZone',  # Graphics
            'MarginTextZone:note'  # Footnotes - could be added separately if needed
        ]
        return block_type in skip_blocks

    def _add_text_to_paragraph(self, paragraph: ET.Element, text: str, line_facs_id: str = None) -> None:
        """Add text to a paragraph, handling cases where paragraph has child elements and hyphen merging"""
        if self.enable_facsimile and line_facs_id:
            # Add text as seg element with facsimile reference
            seg = ET.SubElement(paragraph, 'seg')
            seg.set('facs', f'#{line_facs_id}')
            seg.text = text
        else:
            # Original text handling without facsimile
            if len(paragraph) == 0:
                # No child elements, add to text directly
                if paragraph.text:
                    paragraph.text = self._merge_text_with_hyphen_handling(paragraph.text, text)
                else:
                    paragraph.text = text
            else:
                # Has child elements (like page breaks), add to tail of last child
                last_child = paragraph[-1]
                if last_child.tail:
                    last_child.tail = self._merge_text_with_hyphen_handling(last_child.tail, text)
                else:
                    last_child.tail = text

    def _merge_text_with_hyphen_handling(self, existing_text: str, new_text: str) -> str:
        """Merge text while handling hyphenated words split across pages"""
        # Check if the existing text ends with a hyphen (indicating word split)
        if existing_text.endswith('-') or existing_text.endswith('- '):
            # Remove the hyphen and space, then concatenate without additional space
            cleaned_existing = existing_text.rstrip('- ')
            return cleaned_existing + new_text
        else:
            # Normal case: add space between words
            return existing_text + ' ' + new_text

    def _remove_trailing_hyphen_from_paragraph(self, paragraph: ET.Element) -> bool:
        """Remove trailing hyphen from paragraph text if present. Returns True if hyphen was found."""
        if len(paragraph) == 0:
            # No child elements, check main text
            if paragraph.text and (paragraph.text.endswith('-') or paragraph.text.endswith('- ')):
                paragraph.text = paragraph.text.rstrip('- ')
                return True
        else:
            # Has child elements, check tail of last child
            last_child = paragraph[-1]
            if last_child.tail and (last_child.tail.endswith('-') or last_child.tail.endswith('- ')):
                last_child.tail = last_child.tail.rstrip('- ')
                return True
        return False

    def _add_space_to_paragraph_end(self, paragraph: ET.Element) -> None:
        """Add a space at the end of paragraph text"""
        if len(paragraph) == 0:
            # No child elements, add to main text
            if paragraph.text:
                paragraph.text += ' '
        else:
            # Has child elements, add to tail of last child
            last_child = paragraph[-1]
            if last_child.tail:
                last_child.tail += ' '
            else:
                last_child.tail = ' '

    def extract_text_from_line(self, textline: ET.Element) -> str:
        """Extract text content from an ALTO TextLine element"""
        strings = textline.findall('alto:String', self.alto_ns)
        if not strings:
            return ""
        
        # Combine all string contents from the line
        text_parts = [
            string.get('CONTENT', '') 
            for string in strings 
            if string.get('CONTENT', '').strip()
        ]
        
        return ' '.join(text_parts).strip()

    def _convert_page_with_merged_lines(self, alto_file: Path, page_number: int) -> ET.Element:
        """Convert a single ALTO page to TEI with line merging enabled"""

        # Parse ALTO file using existing logic
        tree = ET.parse(alto_file)
        alto_root = tree.getroot()
        tags_mapping = self.parse_alto_tags(alto_root)

        # Create TEI root
        tei_root = ET.Element('TEI')
        tei_root.set('xmlns', self.tei_ns)

        # Add header
        header = self.create_tei_header(alto_root)
        tei_root.append(header)

        # Create text body
        text_elem = ET.SubElement(tei_root, 'text')
        body = ET.SubElement(text_elem, 'body')

        # Find all text blocks
        textblocks = alto_root.findall('.//alto:TextBlock', self.alto_ns)

        # Separate different types of content
        page_numbers = []
        content_blocks = []
        footnote_blocks = []
        block_elements = []  # For block-level TEI elements

        for _, textblock in enumerate(textblocks):
            block_type = self.get_block_type(textblock, tags_mapping)

            # Let the rule engine handle all line types automatically, including signatures
            # If a NumberingZone contains signature lines, they'll be processed as signatures
            # If it contains page numbers, they'll be processed as page numbers

            # Use rule engine to determine processing logic
            if self.rule_engine.should_extract_page_number(block_type):
                page_num = self.extract_page_number(textblock)
                if page_num:
                    page_numbers.append(page_num)
                
                # Also check for special lines in page number blocks (like signatures in NumberingZone)
                special_elements = self._extract_special_lines_from_block(textblock, tags_mapping, block_type)
                if special_elements:
                    block_elements.extend(special_elements)
            elif self.rule_engine.should_extract_footnote(block_type):
                footnote_content = self.extract_footnote_content(textblock)
                if footnote_content:
                    footnote_blocks.append(footnote_content)
            elif self.rule_engine.should_create_block_element(block_type):
                # Create single TEI element from entire block
                block_element = self.create_block_element(textblock, block_type)
                if block_element is not None:
                    block_elements.append(block_element)
            elif not self.rule_engine.should_skip_block(block_type):
                # Keep content blocks for processing
                content_blocks.append(textblock)
            else:
                # Check for special lines in blocks that don't normally process content
                special_elements = self._extract_special_lines_from_block(textblock, tags_mapping, block_type)
                if special_elements:
                    block_elements.extend(special_elements)

        # Add page break element if we found a page number
        if page_numbers:
            # Use the first page number found (usually there's only one per page)
            filename_elem = alto_root.find('.//alto:sourceImageInformation/alto:fileName', self.alto_ns)
            source_image = filename_elem.text if filename_elem is not None else None
            pb = self.rule_engine.create_element('page_number',
                               page_number=page_numbers[0],
                               source_image=source_image)
            body.append(pb)

        # Add block elements (like running titles)
        for block_element in block_elements:
            body.append(block_element)

        # Process content blocks with line merging
        for block_index, textblock in enumerate(content_blocks, 1):
            block_type = self.get_block_type(textblock, tags_mapping)

            # Skip blocks we don't want in content
            if self.rule_engine.should_skip_block(block_type):
                continue

            # Convert textblock to TEI elements using rule engine with facsimile support
            tei_elements = self.convert_textblock_with_facsimile(textblock, tags_mapping, page_number, block_index)

            # Add elements to body
            for elem in tei_elements:
                body.append(elem)

        # Add footnotes at the end of the body
        if footnote_blocks:
            # Create a div for footnotes
            footnote_div = ET.Element('div')
            footnote_div.set('type', 'notes')

            for footnote_content in footnote_blocks:
                note_elem = self.create_footnote_element(footnote_content)
                footnote_div.append(note_elem)

            body.append(footnote_div)

        return tei_root

    def convert_textblock_with_facsimile(self, textblock: ET.Element, tags_mapping: Dict[str, str],
                               page_number: int, block_index: int) -> List[ET.Element]:
        """Convert an ALTO TextBlock to TEI elements with facsimile zone linking"""
        if not self.enable_facsimile:
            # If facsimile is disabled, use parent's method directly
            return self.convert_textblock(textblock, tags_mapping)
        
        # Use custom conversion with facsimile support
        return self._convert_textblock_with_seg_facsimile(textblock, tags_mapping, page_number, block_index)
    
    def _convert_textblock_with_seg_facsimile(self, textblock: ET.Element, tags_mapping: Dict[str, str], 
                                            page_number: int, block_index: int) -> List[ET.Element]:
        """Convert TextBlock to TEI with seg elements and facsimile linking"""
        textlines = textblock.findall('.//alto:TextLine', self.alto_ns)
        if not textlines:
            return []
        
        elements = []
        state = {'current_p': None, 'current_lg': None}
        line_index = 1
        
        # Generate block facsimile ID for paragraphs
        block_facs_id = self.rule_engine.generate_facsimile_id('block', page_number, block_index=block_index)
        
        for textline in textlines:
            line_type = self.get_line_type(textline, tags_mapping)
            string_elem = textline.find('alto:String', self.alto_ns)
            
            if string_elem is None:
                continue
                
            text_content = string_elem.get('CONTENT', '').strip()
            if not text_content:
                continue
            
            # Generate line facsimile ID
            line_facs_id = self.rule_engine.generate_facsimile_id('line', page_number, 
                                                               block_index=block_index, 
                                                               line_index=line_index)
            
            # Get line configuration
            line_config = self._get_line_mapping(line_type)
            
            # Process based on line type
            if line_config['action'] == 'line_break':
                # Add line break with facsimile reference
                if state['current_p'] is not None:
                    lb = ET.SubElement(state['current_p'], 'lb')
                    lb.set('facs', f'#{line_facs_id}')
                    # Add text as seg element after line break
                    seg = ET.SubElement(state['current_p'], 'seg')
                    seg.set('facs', f'#{line_facs_id}')
                    seg.text = text_content
            elif line_config['element'] == 'head':
                # Close any open paragraphs
                if state['current_p'] is not None:
                    elements.append(state['current_p'])
                    state['current_p'] = None
                # Create header element
                head = ET.Element('head')
                head.text = text_content
                elements.append(head)
            elif line_config['element'] == 'p' or line_config['action'] == 'create_element':
                # Handle paragraph content
                if state['current_p'] is None:
                    # Start new paragraph
                    state['current_p'] = ET.Element('p')
                    state['current_p'].set('facs', f'#{block_facs_id}')
                    # Add first seg element
                    seg = ET.SubElement(state['current_p'], 'seg')
                    seg.set('facs', f'#{line_facs_id}')
                    seg.text = text_content
                else:
                    # Continue existing paragraph with line break
                    lb = ET.SubElement(state['current_p'], 'lb')
                    lb.set('facs', f'#{line_facs_id}')
                    # Add text as new seg element
                    seg = ET.SubElement(state['current_p'], 'seg')
                    seg.set('facs', f'#{line_facs_id}')
                    seg.text = text_content
            
            line_index += 1
        
        # Close any remaining open elements
        if state['current_p'] is not None:
            elements.append(state['current_p'])
        if state['current_lg'] is not None:
            elements.append(state['current_lg'])
        
        return elements

    def _extract_special_lines_from_block(self, textblock: ET.Element, tags_mapping: Dict[str, str], block_type: str) -> List[ET.Element]:
        """Extract special lines (like signatures) from blocks that don't normally process content"""
        special_elements = []
        
        # Get all textlines in this block
        textlines = textblock.findall('.//alto:TextLine', self.alto_ns)
        
        for textline in textlines:
            # Get line type
            line_type = self.get_line_type(textline, tags_mapping)
            
            # Check if this line type should be processed as special content
            if self.rule_engine.should_process_special_line(block_type, line_type):
                # Get the text content
                string_elem = textline.find('alto:String', self.alto_ns)
                if string_elem is not None:
                    content = string_elem.get('CONTENT', '').strip()
                    if content:
                        # Create element using the rule engine - use the same approach for all special lines
                        element = self.rule_engine.create_element('form_work', content=content, line_type=line_type)
                        
                        if element is not None:
                            special_elements.append(element)
        
        return special_elements

    def _add_line_level_facsimile(self, element: ET.Element, page_number: int, block_index: int) -> None:
        """Add line-level facsimile references to text segments"""
        if not self.enable_facsimile:
            return
            
        # Add seg elements with line facsimile references for line breaks
        line_index = 1
        for child in element:
            if child.tag == 'lb':
                line_facs_id = self.rule_engine.generate_facsimile_id('line', page_number, 
                                                                    block_index=block_index, 
                                                                    line_index=line_index)
                child.set('facs', f'#{line_facs_id}')
                line_index += 1

    def save_tei(self, tei_root: ET.Element, output_file: Path) -> None:
        """Save TEI to file with book-specific formatting configuration"""
        # Get output configuration from rule engine
        output_config = self.rule_engine.get_output_config()

        # Create tree and apply standard indentation
        tree = ET.ElementTree(tei_root)
        ET.indent(tree, space="  ", level=0)  # Pretty print (Python 3.9+)

        # Convert to string for custom formatting (always use unicode)
        xml_str = ET.tostring(tei_root, encoding='unicode')

        # Apply custom line break formatting if line breaks are preserved
        if self.rule_engine.should_preserve_line_breaks():
            # Format lb elements to appear on separate lines
            import re
            # Replace <lb /> with newline + indented <lb />
            xml_str = re.sub(r'([^>\n])<lb />', r'\1\n      <lb />', xml_str)
            # If lb is followed by text, put text on next line
            xml_str = re.sub(r'<lb />([^<\n])', r'<lb />\n      \1', xml_str)

        # Get encoding for file writing
        encoding = output_config.get('encoding', 'utf-8')

        with open(output_file, 'w', encoding=encoding) as f:
            # Include XML declaration if configured
            if output_config.get('xml_declaration', True):
                f.write(f'<?xml version="1.0" encoding="{encoding.upper()}"?>\n')
            f.write(xml_str)


def main():
    """Command-line interface for ALTO book to TEI conversion"""

    parser = argparse.ArgumentParser(
        description='Convert entire ALTO XML books to TEI format using METS.xml for page ordering'
    )

    parser.add_argument('input_path', nargs='?',
                       help='Input directory containing ALTO files and METS.xml, or path to METS.xml file')
    parser.add_argument('--mets', '-m',
                       help='Path to METS.xml file (alternative to auto-detection)')
    parser.add_argument('--output', '-o', default='output/book.xml',
                       help='Output TEI XML file (default: output/book.xml)')
    parser.add_argument('--merge-lines', type=str, choices=['True', 'False'], default='True',
                       help='Merge lines into paragraphs and handle hyphenation (default: True)')
    parser.add_argument('--facsimile', type=str, choices=['True', 'False'], default='True',
                       help='Include facsimile zones with spatial coordinates (default: True)')

    args = parser.parse_args()

    # Determine METS.xml path
    if args.mets:
        mets_path = Path(args.mets)
    elif args.input_path:
        input_path = Path(args.input_path)
        if input_path.is_file() and input_path.name == 'METS.xml':
            mets_path = input_path
        elif input_path.is_dir():
            mets_path = input_path / 'METS.xml'
        else:
            print("❌ Error: Input path must be a directory containing METS.xml or path to METS.xml file")
            return 1
    else:
        print("❌ Error: Please provide input path or --mets argument")
        return 1

    # Validate METS.xml exists
    if not mets_path.exists():
        print(f"❌ Error: METS.xml not found at {mets_path}")
        return 1

    output_path = Path(args.output)

    # Convert string to boolean
    merge_lines = args.merge_lines.lower() == 'true'
    enable_facsimile = args.facsimile.lower() == 'true'

    print("📚 ALTO Book to TEI Converter")
    print("=" * 50)
    print(f"METS file: {mets_path}")
    print(f"Output file: {output_path}")
    print(f"Line merging: {'enabled' if merge_lines else 'disabled'}")
    print(f"Facsimile zones: {'enabled' if enable_facsimile else 'disabled'}")
    print("=" * 50)

    try:
        converter = AltoBookToTeiConverter(mets_path, merge_lines=merge_lines,
                                          enable_facsimile=enable_facsimile)
        converter.convert_book_to_tei(output_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
