#!/usr/bin/env python3
"""
Convert eScriptorium ALTO XML output to TEI format
"""

import xml.etree.ElementTree as ET
import glob
import os
import re
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class ConfigurationLoader:
    """Loads and manages ALTO-TEI transformation rules from YAML configuration"""
    
    def __init__(self, config_path: str = "config/alto_tei_mapping.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")
    
    def get_block_types(self) -> Dict[str, Dict[str, Any]]:
        """Get block type configuration"""
        return self.config.get('block_types', {})
    
    def get_line_types(self) -> Dict[str, Dict[str, Any]]:
        """Get line type configuration"""
        return self.config.get('line_types', {})
    
    def get_footnote_patterns(self) -> List[Dict[str, str]]:
        """Get footnote pattern configuration"""
        return self.config.get('footnote_patterns', [])
    
    
    def get_tei_structure(self) -> Dict[str, Any]:
        """Get TEI structure configuration"""
        return self.config.get('tei_structure', {})
    
    def get_element_creation_config(self) -> Dict[str, Any]:
        """Get element creation configuration"""
        return self.config.get('element_creation', {})

class RuleEngine:
    """Processes YAML-based rules for ALTO to TEI conversion"""
    
    def __init__(self, config_loader: ConfigurationLoader):
        self.config = config_loader
        self.block_types = config_loader.get_block_types()
        self.line_types = config_loader.get_line_types()
        self.footnote_patterns = [item['pattern'] for item in config_loader.get_footnote_patterns()]
        self.tei_structure = config_loader.get_tei_structure()
        
        # Validate configuration
        self._validate_configuration()
    
    def should_process_block(self, block_type: str) -> bool:
        """Check if a block type should be processed for content"""
        block_config = self.block_types.get(block_type, {})
        return block_config.get('process_lines', False)
    
    def should_skip_block(self, block_type: str) -> bool:
        """Check if a block type should be skipped entirely"""
        block_config = self.block_types.get(block_type, {})
        return block_config.get('skip_content', False)
    
    def should_extract_page_number(self, block_type: str) -> bool:
        """Check if page number should be extracted from this block type"""
        block_config = self.block_types.get(block_type, {})
        return block_config.get('extract_page_number', False)
    
    def should_extract_footnote(self, block_type: str) -> bool:
        """Check if footnote should be extracted from this block type"""
        block_config = self.block_types.get(block_type, {})
        return block_config.get('extract_footnote', False)
    
    def should_create_block_element(self, block_type: str) -> bool:
        """Check if block should be converted to a single TEI element"""
        block_config = self.block_types.get(block_type, {})
        return 'tei_element' in block_config
    
    def get_footnote_patterns(self) -> List[str]:
        """Get list of footnote patterns for matching"""
        return self.footnote_patterns
    
    def get_line_mapping(self, line_type: str) -> Dict[str, Any]:
        """Get TEI mapping configuration for a line type"""
        return self.line_types.get(line_type, self.line_types.get('DefaultLine', {}))
    
    
    def get_tei_namespace(self) -> str:
        """Get TEI namespace from configuration"""
        return self.tei_structure.get('namespace', 'http://www.tei-c.org/ns/1.0')
    
    def should_preserve_line_breaks(self) -> bool:
        """Check if line breaks should be preserved in output"""
        return self.tei_structure.get('body', {}).get('preserve_line_breaks', False)
    
    def get_element_creation_config(self, element_type: str) -> Dict[str, Any]:
        """Get element creation configuration"""
        element_config = self.config.get_element_creation_config()
        return element_config.get(element_type, {})
    
    def create_element(self, element_type: str, content: str = None, **kwargs) -> ET.Element:
        """Create TEI element based on YAML configuration"""
        config = self.get_element_creation_config(element_type)
        
        if not config:
            # Fallback for unknown element types
            element = ET.Element('p')
            if content:
                element.text = content
            return element
        
        # Create the main element
        element = ET.Element(config['element'])
        
        # Set content if provided
        if content:
            element.text = content
        
        # Set attributes from config
        attributes = config.get('attributes', {})
        default_attributes = config.get('default_attributes', {})
        
        # First set default attributes
        for attr_name, attr_value in default_attributes.items():
            element.set(attr_name, attr_value)
        
        # Then set specific attributes (which can override defaults)
        for attr_name, attr_value in attributes.items():
            # Handle dynamic attribute values
            if attr_name == 'n' and 'symbol' in kwargs:
                element.set(attr_name, kwargs['symbol'])
            elif attr_name == 'n' and 'page_number' in kwargs:
                element.set(attr_name, kwargs['page_number'])
            elif attr_name == 'facs' and 'source_image' in kwargs:
                element.set(attr_name, kwargs['source_image'])
            elif attr_name == 'type' and 'line_type' in kwargs and element_type == 'form_work':
                # Handle form work type mappings
                type_mappings = config.get('type_mappings', {})
                mapped_type = type_mappings.get(kwargs['line_type'], type_mappings.get('default', 'other'))
                element.set(attr_name, mapped_type)
            else:
                element.set(attr_name, attr_value)
        
        # Handle additional kwargs that might override attributes
        if 'rend' in kwargs and kwargs['rend'] != 'header':
            element.set('rend', kwargs['rend'])
        
        return element
    
    def create_line_break(self) -> ET.Element:
        """Create a line break element"""
        return self.create_element('line_break')
    
    def _validate_configuration(self) -> None:
        """Validate YAML configuration for common errors"""
        warnings = []
        
        # Validate block types
        for block_name, block_config in self.block_types.items():
            if not isinstance(block_config, dict):
                warnings.append(f"Block '{block_name}': Configuration must be a dictionary")
                continue
                
            # Check for conflicting settings
            if block_config.get('skip_content', False) and block_config.get('process_lines', False):
                warnings.append(f"Block '{block_name}': Cannot both skip_content and process_lines")
            
            # Check for tei_element without process_lines
            if 'tei_element' in block_config and not block_config.get('process_lines', False):
                warnings.append(f"Block '{block_name}': tei_element requires process_lines: true")
        
        # Validate line types
        valid_actions = {'add_to_paragraph', 'start_paragraph', 'create_element'}
        for line_name, line_config in self.line_types.items():
            if not isinstance(line_config, dict):
                warnings.append(f"Line '{line_name}': Configuration must be a dictionary")
                continue
                
            action = line_config.get('action', 'create_element')
            if action not in valid_actions:
                warnings.append(f"Line '{line_name}': Unknown action '{action}'. Valid: {valid_actions}")
            
            # Check for required fields
            if action == 'create_element' and 'tei_element' not in line_config:
                warnings.append(f"Line '{line_name}': action 'create_element' requires 'tei_element'")
        
        # Print warnings
        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"   {warning}")
            print()

class AltoToTeiConverter:
    def __init__(self, config_path: str = "config/alto_tei_mapping.yaml", preserve_line_breaks: bool = None):
        # ALTO namespace
        self.alto_ns = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
        
        # Load configuration and rule engine
        self.config_loader = ConfigurationLoader(config_path)
        self.rule_engine = RuleEngine(self.config_loader)
        self.tei_ns = self.rule_engine.get_tei_namespace()
        
        # Override line break preservation if specified
        if preserve_line_breaks is not None:
            self.rule_engine.tei_structure['body']['preserve_line_breaks'] = preserve_line_breaks
    
    
    def parse_alto_tags(self, alto_root: ET.Element) -> Dict[str, str]:
        """Parse ALTO tags section to get type mappings"""
        tags = {}
        tags_section = alto_root.find('.//alto:Tags', self.alto_ns)
        if tags_section is not None:
            for tag in tags_section.findall('alto:OtherTag', self.alto_ns):
                tag_id = tag.get('ID')
                label = tag.get('LABEL')
                if tag_id and label:
                    tags[tag_id] = label
        return tags
    
    def resolve_tag_type(self, element: ET.Element, tags_mapping: Dict[str, str], tag_prefix: str, default: str = None) -> str:
        """Unified method to resolve tag type from TAGREFS for both blocks and lines"""
        tagrefs = element.get('TAGREFS', '')
        if tagrefs:
            for tagref in tagrefs.split():
                if tagref.startswith(tag_prefix) and tagref in tags_mapping:
                    tag_type = tags_mapping[tagref]
                    # Check if this tag type exists in our config
                    if tag_prefix == 'BT' and tag_type in self.rule_engine.block_types:
                        return tag_type
                    elif tag_prefix == 'LT' and tag_type in self.rule_engine.line_types:
                        return tag_type
                    return tag_type
        return default or ('MainZone' if tag_prefix == 'BT' else 'DefaultLine')
    
    def get_block_type(self, textblock: ET.Element, tags_mapping: Dict[str, str]) -> str:
        """Determine block type from TAGREFS"""
        return self.resolve_tag_type(textblock, tags_mapping, 'BT', 'MainZone')
    
    def _extract_text_from_strings(self, textblock: ET.Element) -> Optional[str]:
        """Extract and combine text content from all ALTO String elements in a block"""
        strings = textblock.findall('.//alto:String', self.alto_ns)
        if not strings:
            return None
        
        # Combine all string contents (in case text spans multiple strings)
        text = ' '.join(
            string.get('CONTENT', '') 
            for string in strings 
            if string.get('CONTENT', '').strip()
        ).strip()
        
        return text if text else None
    
    def extract_page_number(self, textblock: ET.Element) -> Optional[str]:
        """Extract page number from NumberingZone block"""
        page_text = self._extract_text_from_strings(textblock)
        
        # Basic validation - should be mostly numeric
        if page_text and any(char.isdigit() for char in page_text):
            return page_text
        return None
    
    def extract_footnote_content(self, textblock: ET.Element) -> Optional[Dict[str, str]]:
        """Extract footnote content and separate symbol from text"""
        footnote_text = self._extract_text_from_strings(textblock)
        
        if not footnote_text:
            return None
        
        # Try to identify and separate footnote symbol from text
        symbol = None
        text = footnote_text
        
        # Get patterns from rule engine
        patterns = self.rule_engine.get_footnote_patterns()
        
        for pattern in patterns:
            match = re.match(pattern, footnote_text)
            if match:
                symbol = match.group().strip()
                text = footnote_text[match.end():].strip()
                break
        
        # If no pattern matched, try to detect common symbols at the start
        if symbol is None:
            # Look for any symbol-like characters at the beginning
            symbol_match = re.match(r'^[^\w\s]+\s*', footnote_text)
            if symbol_match:
                symbol = symbol_match.group().strip()
                text = footnote_text[symbol_match.end():].strip()
        
        return {
            'symbol': symbol,
            'text': text,
            'full_text': footnote_text
        }
    
    def create_block_element(self, textblock: ET.Element, block_type: str) -> Optional[ET.Element]:
        """Create a single TEI element from an entire textblock"""
        block_config = self.rule_engine.block_types.get(block_type, {})
        
        if 'tei_element' not in block_config:
            return None
        
        # Extract all text content from the block
        block_text = self._extract_text_from_strings(textblock)
        if not block_text:
            return None
        
        # Create the TEI element
        element_tag = block_config['tei_element']
        element = ET.Element(element_tag)
        element.text = block_text
        
        # Set attributes from config
        attributes = block_config.get('attributes', {})
        for attr, value in attributes.items():
            element.set(attr, value)
        
        return element
    
    def create_footnote_element(self, footnote_content: Dict[str, str]) -> ET.Element:
        """Create a TEI note element from footnote content"""
        # Use YAML-driven element creation
        content = footnote_content['text'] if footnote_content['symbol'] else footnote_content['full_text']
        return self.rule_engine.create_element(
            'footnote', 
            content=content,
            symbol=footnote_content['symbol']
        )
    
    def get_line_type(self, textline: ET.Element, tags_mapping: Dict[str, str]) -> str:
        """Determine line type from TAGREFS"""
        return self.resolve_tag_type(textline, tags_mapping, 'LT', 'DefaultLine')
    
    def _get_line_mapping(self, line_type: str) -> Dict[str, Any]:
        """Get line mapping using rule engine"""
        yaml_mapping = self.rule_engine.get_line_mapping(line_type)
        # Convert YAML format to legacy format for compatibility
        if yaml_mapping:
            legacy_mapping = {
                'element': yaml_mapping.get('tei_element', 'p'),
                'rend': yaml_mapping.get('attributes', {}).get('rend', 'default'),
                'action': yaml_mapping.get('action', 'create_element'),
                'container': yaml_mapping.get('container'),
                'container_attributes': yaml_mapping.get('container_attributes', {}),
                'closes': yaml_mapping.get('closes', []),
                'standalone': yaml_mapping.get('standalone', False)
            }
            return legacy_mapping
        else:
            # Fallback for unknown line types
            return {'element': 'p', 'rend': 'default', 'action': 'create_element'}
    
    def create_tei_header(self, alto_root: ET.Element) -> ET.Element:
        """Create TEI header from ALTO metadata"""
        header = ET.Element('teiHeader')
        
        # File description
        file_desc = ET.SubElement(header, 'fileDesc')
        title_stmt = ET.SubElement(file_desc, 'titleStmt')
        title = ET.SubElement(title_stmt, 'title')
        
        # Try to get filename from ALTO
        filename_elem = alto_root.find('.//alto:sourceImageInformation/alto:fileName', self.alto_ns)
        if filename_elem is not None:
            title.text = f"Digital text from {filename_elem.text}"
        else:
            title.text = "Digital text from eScriptorium"
        
        # Publication statement
        pub_stmt = ET.SubElement(file_desc, 'publicationStmt')
        publisher = ET.SubElement(pub_stmt, 'publisher')
        publisher.text = "eScriptorium"
        
        # Source description
        source_desc = ET.SubElement(file_desc, 'sourceDesc')
        p = ET.SubElement(source_desc, 'p')
        p.text = "Transcribed from digital image using eScriptorium"
        
        return header
    
    def _close_containers(self, state: Dict, elements: List[ET.Element], to_close: List[str]) -> None:
        """Close specified containers and add them to elements"""
        for container_type in to_close:
            if container_type == 'paragraph' and state.get('current_p') is not None:
                elements.append(state['current_p'])
                state['current_p'] = None
            elif container_type == 'poetry' and state.get('current_lg') is not None:
                elements.append(state['current_lg'])
                state['current_lg'] = None
    
    def _ensure_container(self, state: Dict, container_type: str, container_config: Dict) -> None:
        """Ensure specified container exists in state"""
        if container_type == 'lg' and not state.get('current_lg'):
            state['current_lg'] = ET.Element('lg')
            # Set attributes from config
            for attr, value in container_config.get('attributes', {}).items():
                state['current_lg'].set(attr, value)
        elif container_type == 'p' and not state.get('current_p'):
            state['current_p'] = ET.Element('p')
    
    def _process_line_by_config(self, line_config: Dict, text_content: str, state: Dict, elements: List[ET.Element]) -> None:
        """Process a line using YAML configuration rules"""
        # Close containers as specified
        closes = line_config.get('closes', [])
        if closes:
            self._close_containers(state, elements, closes)
        
        # Handle different actions
        action = line_config.get('action', 'create_element')
        
        if action == 'start_paragraph':
            # Close current paragraph if it exists
            if state.get('current_p') is not None:
                elements.append(state['current_p'])
            
            # Start new paragraph
            state['current_p'] = ET.Element('p')
            state['current_p'].text = text_content
            
        elif action == 'add_to_paragraph':
            # Add to existing or create new paragraph
            if state.get('current_p') is not None:
                # If preserving line breaks, add line break element and text
                if self.rule_engine.should_preserve_line_breaks():
                    if state['current_p'].text or len(state['current_p']) > 0:
                        # Add line break element
                        lb = self.rule_engine.create_line_break()
                        state['current_p'].append(lb)
                        # Add text after line break
                        if len(state['current_p']) > 0:
                            # Set tail text on the last element (the line break)
                            state['current_p'][-1].tail = text_content
                        else:
                            state['current_p'].text = text_content
                    else:
                        state['current_p'].text = text_content
                else:
                    # Traditional behavior: join with spaces
                    if state['current_p'].text:
                        state['current_p'].text += " " + text_content
                    else:
                        state['current_p'].text = text_content
            else:
                state['current_p'] = ET.Element('p')
                state['current_p'].text = text_content
                
        else:
            # Create standalone element or element in container
            tei_element = line_config.get('tei_element', 'p')
            
            # Create the element
            element = ET.Element(tei_element)
            element.text = text_content
            
            # Set attributes
            attributes = line_config.get('attributes', {})
            for attr, value in attributes.items():
                element.set(attr, value)
            
            # Handle container requirements
            container = line_config.get('container')
            if container:
                container_config = {
                    'attributes': line_config.get('container_attributes', {})
                }
                self._ensure_container(state, container, container_config)
                
                if container == 'lg' and state.get('current_lg') is not None:
                    state['current_lg'].append(element)
                elif container == 'p' and state.get('current_p') is not None:
                    state['current_p'].append(element)
            else:
                # Standalone element
                elements.append(element)
    
    def convert_textblock(self, textblock: ET.Element, tags_mapping: Dict[str, str]) -> List[ET.Element]:
        """Convert an ALTO TextBlock to TEI elements using YAML-driven rules"""
        elements = []
        state = {'current_p': None, 'current_lg': None}
        
        # Get all textlines in this block
        textlines = textblock.findall('.//alto:TextLine', self.alto_ns)
        
        for textline in textlines:
            # Get the text content
            string_elem = textline.find('alto:String', self.alto_ns)
            if string_elem is None:
                continue
                
            text_content = string_elem.get('CONTENT', '').strip()
            if not text_content:
                continue
            
            # Get line type and its configuration
            line_type = self.get_line_type(textline, tags_mapping)
            line_config = self.rule_engine.get_line_mapping(line_type)
            
            # Process line using configuration
            self._process_line_by_config(line_config, text_content, state, elements)
        
        # Add any remaining containers to elements
        if state['current_p'] is not None:
            elements.append(state['current_p'])
        if state['current_lg'] is not None:
            elements.append(state['current_lg'])
        
        return elements
    
    def convert_alto_to_tei(self, alto_file: Path = None, alto_root: ET.Element = None) -> ET.Element:
        """Main conversion function"""
        if alto_root is None:
            if alto_file is None:
                raise ValueError("Either alto_file or alto_root must be provided")
            # Parse ALTO file
            tree = ET.parse(alto_file)
            alto_root = tree.getroot()
        
        # Parse tags
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
        
        for textblock in textblocks:
            block_type = self.get_block_type(textblock, tags_mapping)
            
            # Use rule engine to determine processing logic
            if self.rule_engine.should_extract_page_number(block_type):
                page_num = self.extract_page_number(textblock)
                if page_num:
                    page_numbers.append(page_num)
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
        
        # Process content blocks
        for textblock in content_blocks:
            block_type = self.get_block_type(textblock, tags_mapping)
            
            # Skip blocks we don't want in content
            if self.rule_engine.should_skip_block(block_type):
                continue
                
            # Convert textblock to TEI elements
            tei_elements = self.convert_textblock(textblock, tags_mapping)
            
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
    
    def extract_metadata_from_tree(self, alto_root: ET.Element) -> Dict[str, Any]:
        """Extract metadata (page numbers, poetry, footnotes) from parsed ALTO tree"""
        tags_mapping = self.parse_alto_tags(alto_root)
        textblocks = alto_root.findall('.//alto:TextBlock', self.alto_ns)
        
        metadata = {
            'page_number': None,
            'has_poetry': False,
            'poetry_line_count': 0,
            'footnote_count': 0,
            'footnote_symbols': []
        }
        
        for textblock in textblocks:
            block_type = self.get_block_type(textblock, tags_mapping)
            
            # Use rule engine to determine processing logic
            if self.rule_engine.should_extract_page_number(block_type):
                page_num = self.extract_page_number(textblock)
                if page_num:
                    metadata['page_number'] = page_num
            
            elif self.rule_engine.should_extract_footnote(block_type):
                footnote_content = self.extract_footnote_content(textblock)
                if footnote_content:
                    metadata['footnote_count'] += 1
                    if footnote_content['symbol']:
                        metadata['footnote_symbols'].append(footnote_content['symbol'])
            
            elif self.rule_engine.should_process_block(block_type):
                # Check for poetry in this block
                textlines = textblock.findall('.//alto:TextLine', self.alto_ns)
                for textline in textlines:
                    line_type = self.get_line_type(textline, tags_mapping)
                    if line_type == 'CustomLine:verse':
                        metadata['has_poetry'] = True
                        metadata['poetry_line_count'] += 1
        
        return metadata
    
    def _setup_processing_paths(self, folder: str, output_folder: str = None) -> Tuple[Path, Path, List[str]]:
        """Setup and validate input/output paths, return file list"""
        folder_path = Path(folder)
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder {folder} does not exist")
        
        # Set up output folder
        if output_folder:
            output_path = Path(output_folder)
            output_path.mkdir(exist_ok=True)
        else:
            output_path = folder_path
        
        xml_files = glob.glob(os.path.join(folder, "*.xml"))
        
        if not xml_files:
            raise ValueError(f"No XML files found in {folder}")
        
        return folder_path, output_path, xml_files
    
    def _process_single_file(self, input_path: Path, output_path: Path, output_suffix: str) -> Dict[str, Any]:
        """Process a single ALTO file and return metadata"""
        try:
            # Check if it's actually an ALTO file
            if not self.is_alto_file(input_path):
                return {'skipped': True, 'reason': 'Not an ALTO file'}
            
            # Parse file once and extract both metadata and convert to TEI
            tree = ET.parse(input_path)
            alto_root = tree.getroot()
            
        except ET.ParseError as e:
            return {'skipped': True, 'reason': f'XML parsing error: {e}'}
        except (FileNotFoundError, PermissionError) as e:
            return {'skipped': True, 'reason': f'File access error: {e}'}
        
        try:
            # Extract metadata for reporting
            metadata = self.extract_metadata_from_tree(alto_root)
            
            # Convert ALTO to TEI using already-parsed tree
            tei_root = self.convert_alto_to_tei(alto_root=alto_root)
            
        except Exception as e:
            return {'skipped': True, 'reason': f'Conversion error: {e}'}
        
        try:
            # Create output filename and save
            output_file = output_path / f"{input_path.stem}{output_suffix}.xml"
            self.save_tei(tei_root, output_file)
            
        except (PermissionError, OSError) as e:
            return {'skipped': True, 'reason': f'File writing error: {e}'}
        
        metadata['output_file'] = output_file.name
        metadata['skipped'] = False
        return metadata
    
    def _print_processing_summary(self, successful: int, failed: int, skipped: int, page_numbers_found: List, 
                                  poetry_files: List, footnote_files: List) -> None:
        """Print final processing summary"""
        summary_parts = [f"{successful} successful"]
        if failed > 0:
            summary_parts.append(f"{failed} failed")
        if skipped > 0:
            summary_parts.append(f"{skipped} skipped")
        
        print(f"\n📊 Summary: {', '.join(summary_parts)}")
        
        if page_numbers_found:
            print(f"📄 Page numbers found:")
            for filename, page_num in page_numbers_found:
                print(f"   {filename}: {page_num}")
        
        if poetry_files:
            print(f"📝 Poetry detected:")
            for filename, line_count in poetry_files:
                print(f"   {filename}: {line_count} verse lines")
        
        if footnote_files:
            print(f"📋 Footnotes detected:")
            for filename, count, symbols in footnote_files:
                symbols_str = ', '.join(symbols) if symbols else 'no symbols detected'
                print(f"   {filename}: {count} footnotes ({symbols_str})")
        
        if not any([page_numbers_found, poetry_files, footnote_files]):
            print("📄 No page numbers, poetry, or footnotes detected in any files")
    
    
    
    
    def save_tei(self, tei_root: ET.Element, output_file: Path) -> None:
        """Save TEI to file with proper formatting"""
        # Create tree and apply standard indentation
        tree = ET.ElementTree(tei_root)
        ET.indent(tree, space="  ", level=0)  # Pretty print (Python 3.9+)
        
        # Convert to string for custom formatting
        xml_str = ET.tostring(tei_root, encoding='unicode')
        
        # Apply custom line break formatting if line breaks are preserved
        if self.rule_engine.should_preserve_line_breaks():
            # Format lb elements to appear on separate lines
            import re
            # Replace <lb /> with newline + indented <lb />
            xml_str = re.sub(r'([^>\n])<lb />', r'\1\n      <lb />', xml_str)
            # If lb is followed by text, put text on next line
            xml_str = re.sub(r'<lb />([^<\n])', r'<lb />\n      \1', xml_str)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_str)

    def is_alto_file(self, xml_file: Path) -> bool:
        """Check if XML file is in ALTO format"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            return root.tag.endswith('alto') or 'alto' in root.tag
        except (ET.ParseError, FileNotFoundError, PermissionError) as e:
            return False

    def process_all_alto_files(self, folder: str, output_folder: str = None, output_suffix: str = "_tei") -> None:
        """
        Process all ALTO XML files in the folder and convert them to TEI.
        
        Args:
            folder: Folder containing .xml files.
            output_folder: Optional separate output folder (if None, saves in same folder)
            output_suffix: Suffix to add to output filenames (before .xml)
        """
        try:
            # Setup paths and get file list
            _, output_path, xml_files = self._setup_processing_paths(folder, output_folder)
            
            print(f"Found {len(xml_files)} XML files to process...")
            
            # Initialize tracking variables
            successful = 0
            failed = 0
            skipped = 0
            page_numbers_found = []
            poetry_files = []
            footnote_files = []
            
            # Process each file
            for i, xml_file in enumerate(xml_files, 1):
                input_path = Path(xml_file)
                print(f"[{i}/{len(xml_files)}] Processing: {input_path.name}")
                
                # Process single file
                metadata = self._process_single_file(input_path, output_path, output_suffix)
                
                if metadata['skipped']:
                    print(f"⚠️  Skipping {input_path.name}: {metadata['reason']}")
                    skipped += 1
                    continue
                
                # Store metadata for final reporting
                if metadata['page_number']:
                    page_numbers_found.append((input_path.name, metadata['page_number']))
                if metadata['has_poetry']:
                    poetry_files.append((input_path.name, metadata['poetry_line_count']))
                if metadata['footnote_count'] > 0:
                    footnote_files.append((input_path.name, metadata['footnote_count'], metadata['footnote_symbols']))
                
                # Create status message
                status_parts = []
                if metadata['page_number']:
                    status_parts.append(f"Page: {metadata['page_number']}")
                if metadata['has_poetry']:
                    status_parts.append(f"Poetry: {metadata['poetry_line_count']} lines")
                if metadata['footnote_count'] > 0:
                    status_parts.append(f"Footnotes: {metadata['footnote_count']}")
                
                status = f" ({', '.join(status_parts)})" if status_parts else ""
                print(f"✅ Converted: {input_path.name} -> {metadata['output_file']}{status}")
                successful += 1
            
            # Print final summary
            self._print_processing_summary(successful, failed, skipped, page_numbers_found, poetry_files, footnote_files)
            
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ {e}")
            return


def main() -> None:
    """Main function with command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Convert eScriptorium ALTO XML files to TEI format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Convert alto/ to tei/
  %(prog)s input_folder output_folder  # Convert input_folder to output_folder
  %(prog)s --input alto --output tei   # Same as default
        """
    )
    
    parser.add_argument(
        "input_folder", 
        nargs="?", 
        default="alto",
        help="Input folder containing ALTO XML files (default: alto)"
    )
    
    parser.add_argument(
        "output_folder", 
        nargs="?", 
        default="tei",
        help="Output folder for TEI XML files (default: tei)"
    )
    
    parser.add_argument(
        "--input", "-i",
        dest="input_folder_flag",
        help="Input folder (alternative to positional argument)"
    )
    
    parser.add_argument(
        "--output", "-o",
        dest="output_folder_flag", 
        help="Output folder (alternative to positional argument)"
    )
    
    parser.add_argument(
        "--suffix", "-s",
        default="_tei",
        help="Suffix to add to output filenames (default: _tei)"
    )
    
    parser.add_argument(
        "--config", "-c",
        default="config/alto_tei_mapping.yaml",
        help="Path to YAML configuration file (default: config/alto_tei_mapping.yaml)"
    )
    
    parser.add_argument(
        "--preserve-line-breaks", 
        action="store_true",
        help="Preserve original line breaks with <lb/> elements (default: enabled in config)"
    )
    
    parser.add_argument(
        "--no-line-breaks", 
        action="store_true",
        help="Disable line break preservation, join lines with spaces"
    )
    
    args = parser.parse_args()
    
    # Use flag arguments if provided, otherwise use positional arguments
    input_folder = args.input_folder_flag or args.input_folder
    output_folder = args.output_folder_flag or args.output_folder
    
    # Determine line break preservation setting
    preserve_line_breaks = None
    if args.preserve_line_breaks:
        preserve_line_breaks = True
    elif args.no_line_breaks:
        preserve_line_breaks = False
    
    print(f"Converting ALTO files from '{input_folder}' to '{output_folder}'")
    if preserve_line_breaks is not None:
        print(f"Line break preservation: {'enabled' if preserve_line_breaks else 'disabled'}")
    
    converter = AltoToTeiConverter(config_path=args.config, preserve_line_breaks=preserve_line_breaks)
    converter.process_all_alto_files(input_folder, output_folder, args.suffix)

if __name__ == "__main__":
    main()
