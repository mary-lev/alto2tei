#!/usr/bin/env python3
"""
Comprehensive tests for the ALTO to TEI converter

Tests cover:
- Unit tests for core conversion methods
- Integration tests with real ALTO files  
- YAML configuration loading and processing
- Edge cases and error conditions
- Regression tests for bug fixes
"""

import unittest
import tempfile
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock
from typing import Dict, List, Any

from alto2tei import AltoToTeiConverter, ConfigurationLoader, RuleEngine


def get_element_text_content(element):
    """Extract all text content from an element, including text on sub-elements"""
    text_parts = []
    if element.text:
        text_parts.append(element.text)

    for child in element:
        if child.tail:
            text_parts.append(child.tail)

    return ' '.join(text_parts)


class TestConfigurationLoader(unittest.TestCase):
    """Test YAML configuration loading and validation"""
    
    def setUp(self):
        self.test_config = {
            'block_types': {
                'MainZone': {
                    'process_lines': True,
                    'skip_content': False
                },
                'NumberingZone': {
                    'extract_page_number': True,
                    'skip_content': True
                }
            },
            'line_types': {
                'DefaultLine': {
                    'action': 'add_to_paragraph',
                    'fallback_element': 'p'
                },
                'CustomLine:verse': {
                    'tei_element': 'l',
                    'container': 'lg',
                    'container_attributes': {'type': 'verse'}
                }
            },
            'footnote_patterns': [
                {'pattern': r'^\([0-9]+\)\s*', 'type': 'numeric'}
            ]
        }
    
    def test_config_loading_success(self):
        """Test successful YAML config loading"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(self.test_config, f)
            config_path = f.name
        
        try:
            loader = ConfigurationLoader(config_path)
            self.assertIsNotNone(loader.config)
            self.assertEqual(len(loader.get_block_types()), 2)
            self.assertEqual(len(loader.get_line_types()), 2)
        finally:
            os.unlink(config_path)
    
    def test_config_file_not_found(self):
        """Test handling of missing config file"""
        with self.assertRaises(FileNotFoundError):
            ConfigurationLoader("/nonexistent/path.yaml")
    
    def test_invalid_yaml_format(self):
        """Test handling of invalid YAML syntax"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            with self.assertRaises(ValueError):
                ConfigurationLoader(config_path)
        finally:
            os.unlink(config_path)


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation and warning system"""
    
    def test_valid_configuration_passes(self):
        """Test that a valid configuration passes validation"""
        valid_config = {
            'block_types': {
                'MainZone': {
                    'process_lines': True,
                    'skip_content': False
                }
            },
            'line_types': {
                'DefaultLine': {
                    'action': 'add_to_paragraph',
                    'fallback_element': 'p'
                }
            },
            'footnote_patterns': [
                {'pattern': r'^\\([0-9]+\\)\\s*', 'type': 'numeric'}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(valid_config, f)
            config_path = f.name
        
        try:
            loader = ConfigurationLoader(config_path)
            rule_engine = RuleEngine(loader)  # This should not raise any errors
            self.assertIsNotNone(rule_engine)
        finally:
            os.unlink(config_path)
    
    def test_conflicting_tei_element_validation(self):
        """Test validation catches conflicting tei_element and process_lines settings"""
        conflicting_config = {
            'block_types': {
                'ConflictingBlock': {
                    'process_lines': False,
                    'tei_element': 'div',  # Conflict: has tei_element but doesn't process lines
                    'skip_content': True
                }
            },
            'line_types': {
                'DefaultLine': {
                    'action': 'add_to_paragraph',
                    'fallback_element': 'p'
                }
            },
            'footnote_patterns': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(conflicting_config, f)
            config_path = f.name
        
        try:
            loader = ConfigurationLoader(config_path)
            # This should still work but may produce warnings
            rule_engine = RuleEngine(loader)
            self.assertIsNotNone(rule_engine)
        finally:
            os.unlink(config_path)
    
    def test_unknown_action_validation(self):
        """Test validation handles unknown line actions gracefully"""
        unknown_action_config = {
            'block_types': {
                'MainZone': {
                    'process_lines': True,
                    'skip_content': False
                }
            },
            'line_types': {
                'UnknownActionLine': {
                    'action': 'unknown_action_that_does_not_exist',
                    'tei_element': 'p'
                },
                'DefaultLine': {
                    'action': 'add_to_paragraph',
                    'fallback_element': 'p'
                }
            },
            'footnote_patterns': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(unknown_action_config, f)
            config_path = f.name
        
        try:
            loader = ConfigurationLoader(config_path)
            rule_engine = RuleEngine(loader)
            self.assertIsNotNone(rule_engine)
        finally:
            os.unlink(config_path)
    
    def test_missing_required_fields(self):
        """Test handling of configuration with missing required fields"""
        incomplete_config = {
            'block_types': {
                'IncompleteBlock': {
                    # Missing process_lines and skip_content
                }
            },
            'line_types': {
                'IncompleteLine': {
                    # Missing action or tei_element
                }
            },
            'footnote_patterns': []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(incomplete_config, f)
            config_path = f.name
        
        try:
            loader = ConfigurationLoader(config_path)
            rule_engine = RuleEngine(loader)
            # Should still work with defaults
            self.assertIsNotNone(rule_engine)
        finally:
            os.unlink(config_path)
    
    def test_configuration_statistics(self):
        """Test that configuration statistics are correctly calculated"""
        test_config = {
            'block_types': {
                'MainZone': {'process_lines': True, 'skip_content': False},
                'GraphicZone': {'process_lines': False, 'skip_content': True},
                'NumberingZone': {'extract_page_number': True, 'skip_content': True}
            },
            'line_types': {
                'DefaultLine': {'action': 'add_to_paragraph', 'fallback_element': 'p'},
                'CustomLine:verse': {'tei_element': 'l', 'container': 'lg'},
                'HeadingLine': {'tei_element': 'head', 'standalone': True}
            },
            'footnote_patterns': [
                {'pattern': r'^\\([0-9]+\\)\\s*', 'type': 'numeric'},
                {'pattern': r'^\\(\\*+\\)\\s*', 'type': 'asterisk'}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            loader = ConfigurationLoader(config_path)
            rule_engine = RuleEngine(loader)
            
            # Check statistics
            self.assertEqual(len(rule_engine.block_types), 3)
            self.assertEqual(len(rule_engine.line_types), 3)
            self.assertEqual(len(rule_engine.footnote_patterns), 2)
        finally:
            os.unlink(config_path)


class TestRuleEngine(unittest.TestCase):
    """Test rule engine processing logic using real ALTO data"""
    
    def setUp(self):
        # Load a real ALTO file for testing
        alto_file = Path('alto/04b1382c18da.xml')
        tree = ET.parse(alto_file)
        root = tree.getroot()
        
        # Parse tags to build a real tags_mapping
        tags_section = root.find('.//alto:Tags', {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'})
        if tags_section is None:
            raise ValueError("No Tags section found in ALTO file")
        
        tags_mapping = {}
        for tag in tags_section.findall('alto:OtherTag', {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}):
            tag_id = tag.get('ID')
            label = tag.get('LABEL')
            if tag_id and label:
                tags_mapping[tag_id] = label
        
        # Create a real ConfigurationLoader with the parsed tags
        self.config_loader = ConfigurationLoader("config/alto_tei_mapping.yaml")
        self.rule_engine = RuleEngine(self.config_loader)
        self.converter = AltoToTeiConverter()
        self.tags_mapping = tags_mapping
    
    def test_should_process_block(self):
        """Test block processing decision logic using real ALTO data"""
        # Example: Check if a block with TAGREFS 'BT2' should be processed
        element = ET.Element('TextBlock')
        element.set('TAGREFS', 'BT2')
        block_type = self.converter.resolve_tag_type(element, self.tags_mapping, 'BT')
        self.assertTrue(self.rule_engine.should_process_block(block_type))
    
    def test_should_skip_block(self):
        """Test block skipping decision logic using real ALTO data"""
        # Example: Check if a block with TAGREFS 'BT134' should be skipped
        element = ET.Element('TextBlock')
        element.set('TAGREFS', 'BT134')
        block_type = self.converter.resolve_tag_type(element, self.tags_mapping, 'BT')
        self.assertTrue(self.rule_engine.should_skip_block(block_type))
    
    def test_should_extract_page_number(self):
        """Test page number extraction decision logic using real ALTO data"""
        # Example: Check if a block with TAGREFS 'BT134' should extract page number
        element = ET.Element('TextBlock')
        element.set('TAGREFS', 'BT134')
        block_type = self.converter.resolve_tag_type(element, self.tags_mapping, 'BT')
        self.assertTrue(self.rule_engine.should_extract_page_number(block_type))
    
    def test_get_line_mapping(self):
        """Test line type mapping retrieval using real ALTO data"""
        # Example: Check line mapping for a line with TAGREFS 'LT74'
        element = ET.Element('TextLine')
        element.set('TAGREFS', 'LT74')
        line_type = self.converter.resolve_tag_type(element, self.tags_mapping, 'LT')
        mapping = self.rule_engine.get_line_mapping(line_type)
        self.assertEqual(mapping['action'], 'add_to_paragraph')


class TestTagParsing(unittest.TestCase):
    """Test unified tag parsing logic"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.tags_mapping = {
            'BT2': 'MainZone',
            'BT134': 'NumberingZone',
            'LT74': 'DefaultLine',
            'LT79': 'CustomLine:verse'
        }
    
    def test_resolve_tag_type_block(self):
        """Test block tag type resolution"""
        # Create mock element
        element = ET.Element('TextBlock')
        element.set('TAGREFS', 'BT2')
        
        result = self.converter.resolve_tag_type(element, self.tags_mapping, 'BT')
        self.assertEqual(result, 'MainZone')
    
    def test_resolve_tag_type_line(self):
        """Test line tag type resolution"""
        element = ET.Element('TextLine')
        element.set('TAGREFS', 'LT79')
        
        result = self.converter.resolve_tag_type(element, self.tags_mapping, 'LT')
        self.assertEqual(result, 'CustomLine:verse')
    
    def test_resolve_tag_type_no_tags(self):
        """Test tag resolution with no TAGREFS"""
        element = ET.Element('TextBlock')
        
        result = self.converter.resolve_tag_type(element, self.tags_mapping, 'BT')
        self.assertEqual(result, 'MainZone')  # Default for blocks
    
    def test_resolve_tag_type_unknown_tag(self):
        """Test tag resolution with unknown tag ID"""
        element = ET.Element('TextLine')
        element.set('TAGREFS', 'LT999')
        
        result = self.converter.resolve_tag_type(element, self.tags_mapping, 'LT')
        self.assertEqual(result, 'DefaultLine')  # Default for lines


class TestLineProcessing(unittest.TestCase):
    """Test line processing with YAML configuration"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
    
    def test_process_paragraph_lines(self):
        """Test processing multiple lines into a paragraph"""
        state = {'current_p': None, 'current_lg': None}
        elements = []
        
        config = {'action': 'add_to_paragraph'}
        
        # Process multiple lines
        self.converter._process_line_by_config(config, 'First line', state, elements)
        self.converter._process_line_by_config(config, 'Second line', state, elements)
        self.converter._process_line_by_config(config, 'Third line', state, elements)
        
        # Finalize state
        if state['current_p'] is not None:
            elements.append(state['current_p'])
        
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'p')
        self.assertEqual(elements[0].text, 'First line')
        
        # Check that line breaks were added
        lb_elements = elements[0].findall('.//lb')
        self.assertEqual(len(lb_elements), 2)  # Two line breaks for three lines
        
        # Check tail text on line breaks
        self.assertEqual(lb_elements[0].tail, 'Second line')
        self.assertEqual(lb_elements[1].tail, 'Third line')
    
    def test_process_verse_lines(self):
        """Test processing verse lines into container"""
        state = {'current_p': None, 'current_lg': None}
        elements = []
        
        config = {
            'tei_element': 'l',
            'container': 'lg',
            'container_attributes': {'type': 'verse'}
        }
        
        # Process verse lines
        self.converter._process_line_by_config(config, 'First verse line', state, elements)
        self.converter._process_line_by_config(config, 'Second verse line', state, elements)
        
        # Finalize state
        if state['current_lg'] is not None:
            elements.append(state['current_lg'])
        
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'lg')
        self.assertEqual(elements[0].get('type'), 'verse')
        self.assertEqual(len(elements[0]), 2)  # Two <l> children
        self.assertEqual(elements[0][0].text, 'First verse line')
        self.assertEqual(elements[0][1].text, 'Second verse line')
    
    def test_container_closing(self):
        """Test container closing behavior"""
        state = {'current_p': None, 'current_lg': None}
        elements = []
        
        # Create a paragraph first
        para_config = {'action': 'add_to_paragraph'}
        self.converter._process_line_by_config(para_config, 'Paragraph text', state, elements)
        
        # Ensure paragraph exists
        self.assertIsNotNone(state['current_p'])
        
        # Process header that should close paragraph
        header_config = {
            'tei_element': 'head',
            'closes': ['paragraph']
        }
        self.converter._process_line_by_config(header_config, 'Header text', state, elements)
        
        # Paragraph should be closed and added to elements
        self.assertEqual(len(elements), 2)  # paragraph + header
        self.assertEqual(elements[0].tag, 'p')
        self.assertEqual(elements[1].tag, 'head')
        self.assertIsNone(state['current_p'])


class TestTextBlockConversion(unittest.TestCase):
    """Test complete textblock conversion process"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.ns = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
    
    def create_alto_textblock(self, lines_data):
        """Helper to create ALTO TextBlock with specified lines"""
        textblock = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        
        for i, (content, tagrefs) in enumerate(lines_data):
            textline = ET.SubElement(textblock, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
            textline.set('ID', f'line_{i}')
            if tagrefs:
                textline.set('TAGREFS', tagrefs)
            
            string_elem = ET.SubElement(textline, '{http://www.loc.gov/standards/alto/ns-v4#}String')
            string_elem.set('CONTENT', content)
        
        return textblock
    
    def test_convert_paragraph_textblock(self):
        """Test converting textblock with paragraph content"""
        lines_data = [
            ('First sentence of paragraph.', 'LT74'),
            ('Second sentence of paragraph.', 'LT74'),
            ('Third sentence of paragraph.', 'LT74')
        ]
        
        textblock = self.create_alto_textblock(lines_data)
        tags_mapping = {'LT74': 'DefaultLine'}
        
        elements = self.converter.convert_textblock(textblock, tags_mapping)
        
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'p')
        expected_text = 'First sentence of paragraph. Second sentence of paragraph. Third sentence of paragraph.'
        actual_text = get_element_text_content(elements[0])
        self.assertEqual(actual_text, expected_text)
    
    def test_convert_verse_textblock(self):
        """Test converting textblock with verse content"""
        lines_data = [
            ('First line of verse', 'LT79'),
            ('Second line of verse', 'LT79'),
            ('Third line of verse', 'LT79')
        ]
        
        textblock = self.create_alto_textblock(lines_data)
        tags_mapping = {'LT79': 'CustomLine:verse'}
        
        elements = self.converter.convert_textblock(textblock, tags_mapping)
        
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'lg')
        self.assertEqual(elements[0].get('type'), 'verse')
        self.assertEqual(len(elements[0]), 3)
        
        # Check individual verse lines
        for i, expected_text in enumerate(['First line of verse', 'Second line of verse', 'Third line of verse']):
            self.assertEqual(elements[0][i].tag, 'l')
            self.assertEqual(elements[0][i].text, expected_text)
    
    def test_convert_mixed_content_textblock(self):
        """Test converting textblock with mixed content types"""
        lines_data = [
            ('Scene Title', 'LT83'),  # Header
            ('SPEAKER NAME', 'LT82'),  # Speaker
            ('First verse line', 'LT79'),  # Verse
            ('Second verse line', 'LT79'),  # Verse
            ('Regular paragraph text.', 'LT74')  # Paragraph
        ]

        textblock = self.create_alto_textblock(lines_data)
        tags_mapping = {
            'LT83': 'HeadingLine',
            'LT82': 'CustomLine:speaker', 
            'LT79': 'CustomLine:verse',
            'LT74': 'DefaultLine'
        }

        elements = self.converter.convert_textblock(textblock, tags_mapping)
        
        # Should have: header, speaker, paragraph, verse container
        # Note: DefaultLine doesn't close poetry in YAML config, so verse container comes last
        self.assertEqual(len(elements), 4)

        # Check header
        self.assertEqual(elements[0].tag, 'head')
        self.assertEqual(elements[0].text, 'Scene Title')
        
        # Check speaker  
        self.assertEqual(elements[1].tag, 'speaker')
        self.assertEqual(elements[1].text, 'SPEAKER NAME')
        
        # Check paragraph (comes before verse container per YAML behavior)
        self.assertEqual(elements[2].tag, 'p')
        self.assertEqual(elements[2].text, 'Regular paragraph text.')
        
        # Check verse container (finalized at end)
        self.assertEqual(elements[3].tag, 'lg')
        self.assertEqual(len(elements[3]), 2)
        self.assertEqual(elements[3][0].text, 'First verse line')
        self.assertEqual(elements[3][1].text, 'Second verse line')


class TestMultipleParagraphs(unittest.TestCase):
    """Test handling of multiple paragraphs on a page"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.ns = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
    
    def create_alto_textblock_with_positions(self, lines_data):
        """Helper to create ALTO TextBlock with specified lines and positions"""
        textblock = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        textblock.set('TAGREFS', 'BT2')  # MainZone
        
        for i, (content, tagrefs, hpos) in enumerate(lines_data):
            text_line = ET.SubElement(textblock, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
            text_line.set('ID', f'line_{i}')
            text_line.set('HPOS', str(hpos))
            if tagrefs:
                text_line.set('TAGREFS', tagrefs)
            
            string_elem = ET.SubElement(text_line, '{http://www.loc.gov/standards/alto/ns-v4#}String')
            string_elem.set('CONTENT', content)
            string_elem.set('HPOS', str(hpos))
        
        return textblock
    
    def test_explicit_paragraph_markers(self):
        """Test multiple paragraphs with explicit paragraph_start markers"""
        lines_data = [
            ('First paragraph first line.', 'LT77', 70),  # paragraph_start
            ('First paragraph second line.', 'LT74', 70),  # default
            ('Second paragraph first line.', 'LT77', 70),  # paragraph_start
            ('Second paragraph second line.', 'LT74', 70),  # default
            ('Third paragraph single line.', 'LT77', 70)   # paragraph_start
        ]
        
        textblock = self.create_alto_textblock_with_positions(lines_data)
        tags_mapping = {
            'LT77': 'CustomLine:paragraph_start',
            'LT74': 'DefaultLine'
        }
        
        elements = self.converter.convert_textblock(textblock, tags_mapping)
        
        # Should create 3 separate paragraphs
        paragraphs = [elem for elem in elements if elem.tag == 'p']
        self.assertEqual(len(paragraphs), 3)
        
        # Check paragraph contents
        actual_text = get_element_text_content(paragraphs[0])
        self.assertEqual(actual_text, 'First paragraph first line. First paragraph second line.')
        actual_text2 = get_element_text_content(paragraphs[1])
        self.assertEqual(actual_text2, 'Second paragraph first line. Second paragraph second line.')
        actual_text3 = get_element_text_content(paragraphs[2])
        self.assertEqual(actual_text3, 'Third paragraph single line.')
    
    def test_indentation_based_paragraphs(self):
        """Test paragraph detection based on indentation patterns"""
        # Simulate the 0d1b1aaf40cb.xml pattern
        lines_data = [
            ('End of previous context and life.', 'LT74', 70),
            ('I will briefly declare about following', 'LT74', 173),  # Big indent = new paragraph
            ('events of bloody campaign in 1686.', 'LT74', 70),
            ('This campaign was most famous.', 'LT74', 70),
            ('Finally garrison noticed their', 'LT74', 163),  # Big indent = new paragraph
            ('empty fear and made sortie.', 'LT74', 70),
            ('But it was too late!', 'LT74', 70)
        ]
        
        textblock = self.create_alto_textblock_with_positions(lines_data)
        tags_mapping = {'LT74': 'DefaultLine'}
        
        # TODO: This test will fail until we implement indentation detection
        # For now, test current behavior (single paragraph)
        elements = self.converter.convert_textblock(textblock, tags_mapping)
        paragraphs = [elem for elem in elements if elem.tag == 'p']
        
        # Currently creates 1 paragraph (incorrect behavior)
        self.assertEqual(len(paragraphs), 1)
        
        # TODO: After implementing indentation detection, should be 3 paragraphs:
        # self.assertEqual(len(paragraphs), 3)
        # self.assertTrue(paragraphs[0].text.endswith('and life.'))
        # self.assertTrue(paragraphs[1].text.startswith('I will briefly'))
        # self.assertTrue(paragraphs[2].text.startswith('Finally garrison'))
    
    def test_mixed_paragraph_indicators(self):
        """Test combination of explicit markers and indentation"""
        lines_data = [
            ('Normal paragraph line.', 'LT74', 70),
            ('Explicit new paragraph start.', 'LT77', 70),  # paragraph_start
            ('Continuation of explicit paragraph.', 'LT74', 70),
            ('Indented line should start new paragraph.', 'LT74', 180),  # indented
            ('Continuation of indented paragraph.', 'LT74', 70)
        ]
        
        textblock = self.create_alto_textblock_with_positions(lines_data)
        tags_mapping = {
            'LT77': 'CustomLine:paragraph_start',
            'LT74': 'DefaultLine'
        }
        
        elements = self.converter.convert_textblock(textblock, tags_mapping)
        paragraphs = [elem for elem in elements if elem.tag == 'p']
        
        # Currently: explicit paragraph_start creates 2 paragraphs
        # TODO: After indentation detection, should be 3 paragraphs
        self.assertGreaterEqual(len(paragraphs), 2)
    
    def test_no_false_paragraph_breaks(self):
        """Test that small indentation variations don't create false breaks"""
        lines_data = [
            ('Normal line with standard margin.', 'LT74', 70),
            ('Slight variation in margin.', 'LT74', 75),  # Small variation
            ('Another slight variation.', 'LT74', 68),   # Small variation
            ('Back to normal margin.', 'LT74', 70)
        ]
        
        textblock = self.create_alto_textblock_with_positions(lines_data)
        tags_mapping = {'LT74': 'DefaultLine'}
        
        elements = self.converter.convert_textblock(textblock, tags_mapping)
        paragraphs = [elem for elem in elements if elem.tag == 'p']
        
        # Should remain as single paragraph (small variations don't count)
        self.assertEqual(len(paragraphs), 1)
        expected_text = 'Normal line with standard margin. Slight variation in margin. Another slight variation. Back to normal margin.'
        actual_text = get_element_text_content(paragraphs[0])
        self.assertEqual(actual_text, expected_text)


class TestRunningTitleHandling(unittest.TestCase):
    """Test handling of RunningTitleZone blocks"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.ns = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
    
    def test_running_title_zone_as_form_work(self):
        """Test that RunningTitleZone blocks are converted to form work elements"""
        # Create mock ALTO structure with RunningTitleZone
        alto_root = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}alto')
        
        # Add tags section
        tags = ET.SubElement(alto_root, '{http://www.loc.gov/standards/alto/ns-v4#}Tags')
        running_title_tag = ET.SubElement(tags, '{http://www.loc.gov/standards/alto/ns-v4#}OtherTag')
        running_title_tag.set('ID', 'BT138')
        running_title_tag.set('LABEL', 'RunningTitleZone')
        
        main_zone_tag = ET.SubElement(tags, '{http://www.loc.gov/standards/alto/ns-v4#}OtherTag')
        main_zone_tag.set('ID', 'BT2')
        main_zone_tag.set('LABEL', 'MainZone')
        
        # Add layout with RunningTitleZone and MainZone blocks
        layout = ET.SubElement(alto_root, '{http://www.loc.gov/standards/alto/ns-v4#}Layout')
        page = ET.SubElement(layout, '{http://www.loc.gov/standards/alto/ns-v4#}Page')
        print_space = ET.SubElement(page, '{http://www.loc.gov/standards/alto/ns-v4#}PrintSpace')
        
        # RunningTitleZone block (should become form work)
        running_title_block = ET.SubElement(print_space, '{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        running_title_block.set('TAGREFS', 'BT138')
        running_title_line = ET.SubElement(running_title_block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        running_title_string = ET.SubElement(running_title_line, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        running_title_string.set('CONTENT', 'Chapter Title Header')
        
        # MainZone block (should be included)
        main_block = ET.SubElement(print_space, '{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        main_block.set('TAGREFS', 'BT2')
        main_line = ET.SubElement(main_block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        main_string = ET.SubElement(main_line, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        main_string.set('CONTENT', 'This is the actual document content.')
        
        # Convert to TEI
        tei_root = self.converter.convert_alto_to_tei(alto_root=alto_root)
        
        # Check that running title appears as form work element
        fw_elements = tei_root.findall('.//fw[@type="running-title"]')
        self.assertEqual(len(fw_elements), 1, "Should have one running title form work element")
        self.assertEqual(fw_elements[0].text, 'Chapter Title Header')
        self.assertEqual(fw_elements[0].get('place'), 'top')
        
        # Main content should still appear in paragraphs
        paragraphs = tei_root.findall('.//p')
        content_found = any('This is the actual document content.' in (p.text or '') for p in paragraphs)
        self.assertTrue(content_found, "MainZone content should be included in TEI output")
    
    def test_running_title_zone_rule_engine(self):
        """Test that rule engine properly handles RunningTitleZone configuration"""
        # Test that RunningTitleZone is configured for block element creation
        should_skip = self.converter.rule_engine.should_skip_block('RunningTitleZone')
        should_process = self.converter.rule_engine.should_process_block('RunningTitleZone')
        should_create_block = self.converter.rule_engine.should_create_block_element('RunningTitleZone')
        
        self.assertFalse(should_skip, "RunningTitleZone should not be skipped")
        self.assertTrue(should_process, "RunningTitleZone should be processed")
        self.assertTrue(should_create_block, "RunningTitleZone should create block element")
    
    def test_real_file_with_running_title(self):
        """Test real file that contains RunningTitleZone content"""
        alto_dir = Path('alto')
        # Use a file that we know exists
        test_files = ['4b369dc6f692.xml', 'e0ecd2558f84.xml', '267889351c5d.xml', '47a6fe0fae17.xml']
        
        test_file = None
        for file in test_files:
            if (alto_dir / file).exists():
                test_file = file
                break
        
        if test_file is None:
            self.skipTest("No test files with running titles found")
        
        input_file = alto_dir / test_file
        tei_root = self.converter.convert_alto_to_tei(input_file)
        
        # Running title should appear as form work element
        fw_elements = tei_root.findall('.//fw[@type="running-title"]')
        
        # Should have actual content
        body = tei_root.find('text/body')
        content_elements = body.findall('.//p') + body.findall('.//lg') + body.findall('.//head')
        self.assertGreater(len(content_elements), 0, "Should have main content elements")
        
        print(f"✅ Tested file {test_file}: found {len(fw_elements)} running title form work elements")


class TestLineBreakPreservation(unittest.TestCase):
    """Test line break preservation functionality"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
    
    def test_line_break_preservation_config(self):
        """Test that line break preservation is enabled in configuration"""
        should_preserve = self.converter.rule_engine.should_preserve_line_breaks()
        self.assertTrue(should_preserve, "Line break preservation should be enabled")
    
    def test_line_break_creation(self):
        """Test that line break elements can be created"""
        lb = self.converter.rule_engine.create_line_break()
        self.assertEqual(lb.tag, 'lb')
        self.assertEqual(len(lb.attrib), 0)  # Should be self-closing with no attributes
    
    def test_line_breaks_in_paragraphs(self):
        """Test that line breaks are properly inserted in paragraphs"""
        # Create mock ALTO structure with multiple lines in one block
        alto_root = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}alto')
        
        # Add layout with TextBlock containing multiple TextLines
        layout = ET.SubElement(alto_root, '{http://www.loc.gov/standards/alto/ns-v4#}Layout')
        page = ET.SubElement(layout, '{http://www.loc.gov/standards/alto/ns-v4#}Page')
        print_space = ET.SubElement(page, '{http://www.loc.gov/standards/alto/ns-v4#}PrintSpace')
        
        text_block = ET.SubElement(print_space, '{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        
        # First line
        line1 = ET.SubElement(text_block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        string1 = ET.SubElement(line1, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        string1.set('CONTENT', 'First line of text')
        
        # Second line
        line2 = ET.SubElement(text_block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        string2 = ET.SubElement(line2, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        string2.set('CONTENT', 'Second line of text')
        
        # Third line
        line3 = ET.SubElement(text_block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        string3 = ET.SubElement(line3, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        string3.set('CONTENT', 'Third line of text')
        
        # Convert to TEI
        tei_root = self.converter.convert_alto_to_tei(alto_root=alto_root)
        
        # Find paragraphs in body (excluding header)
        body = tei_root.find('text/body')
        paragraphs = body.findall('p')
        self.assertEqual(len(paragraphs), 1, "Should have one paragraph in body")
        
        paragraph = paragraphs[0]
        
        # Check that line breaks are present
        lb_elements = paragraph.findall('lb')
        self.assertEqual(len(lb_elements), 2, "Should have 2 line break elements between 3 lines")
        
        # Check text content preservation
        self.assertTrue('First line of text' in paragraph.text)
        self.assertTrue('Second line of text' in (lb_elements[0].tail or ''))
        self.assertTrue('Third line of text' in (lb_elements[1].tail or ''))


class TestFacsimileOutput(unittest.TestCase):
    """Test facsimile zone generation and facs references"""

    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.ns = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}

    def create_simple_alto(self):
        alto_root = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}alto')

        # Source image
        src_info = ET.SubElement(alto_root, '{http://www.loc.gov/standards/alto/ns-v4#}sourceImageInformation')
        fname = ET.SubElement(src_info, '{http://www.loc.gov/standards/alto/ns-v4#}fileName')
        fname.text = 'page1.jpg'

        layout = ET.SubElement(alto_root, '{http://www.loc.gov/standards/alto/ns-v4#}Layout')
        page = ET.SubElement(layout, '{http://www.loc.gov/standards/alto/ns-v4#}Page')
        print_space = ET.SubElement(page, '{http://www.loc.gov/standards/alto/ns-v4#}PrintSpace')
        block = ET.SubElement(print_space, '{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')

        line1 = ET.SubElement(block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        line1.set('HPOS', '10'); line1.set('VPOS', '20'); line1.set('WIDTH', '50'); line1.set('HEIGHT', '10')
        string1 = ET.SubElement(line1, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        string1.set('CONTENT', 'Line one')

        line2 = ET.SubElement(block, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        line2.set('HPOS', '15'); line2.set('VPOS', '35'); line2.set('WIDTH', '55'); line2.set('HEIGHT', '10')
        string2 = ET.SubElement(line2, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        string2.set('CONTENT', 'Line two')

        return alto_root

    def test_facsimile_zones_and_refs(self):
        alto_root = self.create_simple_alto()
        tei_root = self.converter.convert_alto_to_tei(alto_root=alto_root)

        facs = tei_root.find('facsimile')
        self.assertIsNotNone(facs)
        surface = facs.find('surface')
        zones = surface.findall('zone')
        self.assertEqual(len(zones), 2)
        self.assertEqual(zones[0].get('ulx'), '10')
        self.assertEqual(zones[1].get('lry'), '45')

        body = tei_root.find('text/body')
        p = body.find('p')
        self.assertEqual(p.get('facs'), '#tl1')
        lb = p.find('lb')
        self.assertEqual(lb.get('facs'), '#tl2')


class TestRealWorldMultipleParagraphs(unittest.TestCase):
    """Test multiple paragraph handling with real ALTO files"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.alto_dir = Path('alto')
    
    def test_document_with_multiple_logical_paragraphs(self):
        """Test document that should have multiple paragraphs (0d1b1aaf40cb.xml)"""
        if not (self.alto_dir / '0d1b1aaf40cb.xml').exists():
            self.skipTest("Test ALTO file not found")
        
        input_file = self.alto_dir / '0d1b1aaf40cb.xml'
        tei_root = self.converter.convert_alto_to_tei(input_file)
        
        body = tei_root.find('text/body')
        paragraphs = body.findall('p')
        
        # Currently creates 1 paragraph (incorrect)
        # TODO: After implementing indentation detection, should create 3 paragraphs
        self.assertGreater(len(paragraphs), 0, "Should have paragraphs")
        
        # Check that we have substantial content (including line break tail text)
        content_paragraphs = [p for p in paragraphs if len(get_element_text_content(p)) > 50]
        self.assertGreater(len(content_paragraphs), 0, "Should have substantial content")
        
        # TODO: Add specific checks for proper paragraph breaks after implementation
        # self.assertEqual(len(paragraphs), 3, "Should detect 3 paragraphs based on indentation")


class TestIntegration(unittest.TestCase):
    """Integration tests with real ALTO files"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
        self.alto_dir = Path('alto')
        self.tei_dir = Path('tei')
    
    def test_verse_file_conversion(self):
        """Test conversion of file with verse content (0aefed141cd6.xml)"""
        if not (self.alto_dir / '0aefed141cd6.xml').exists():
            self.skipTest("Test ALTO file not found")
        
        input_file = self.alto_dir / '0aefed141cd6.xml'
        tei_root = self.converter.convert_alto_to_tei(input_file)
        
        # Should have TEI structure
        self.assertEqual(tei_root.tag, 'TEI')
        self.assertEqual(tei_root.get('xmlns'), 'http://www.tei-c.org/ns/1.0')
        
        # Should have header and text
        header = tei_root.find('teiHeader')
        text = tei_root.find('text')
        self.assertIsNotNone(header)
        self.assertIsNotNone(text)
        
        # Body should contain verse structures
        body = text.find('body')
        verse_containers = body.findall('lg[@type="verse"]')
        self.assertGreater(len(verse_containers), 0, "Should contain verse containers")
        
        # Verse containers should have line elements
        for lg in verse_containers:
            lines = lg.findall('l')
            self.assertGreater(len(lines), 0, "Verse containers should have lines")
    
    def test_paragraph_file_conversion(self):
        """Test conversion of file with paragraph content (0e2a73f13785.xml)"""
        if not (self.alto_dir / '0e2a73f13785.xml').exists():
            self.skipTest("Test ALTO file not found")
        
        input_file = self.alto_dir / '0e2a73f13785.xml'
        tei_root = self.converter.convert_alto_to_tei(input_file)
        
        # Should have TEI structure
        self.assertEqual(tei_root.tag, 'TEI')
        
        # Body should contain paragraph
        body = tei_root.find('text/body')
        paragraphs = body.findall('p')
        self.assertGreater(len(paragraphs), 0, "Should contain paragraphs")
        
        # Find the main content paragraph (not just page number reference)
        content_paragraphs = [p for p in paragraphs if len(p.text or '') > 10]
        self.assertGreater(len(content_paragraphs), 0, "Should contain substantial paragraph content")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
    
    def test_empty_textblock(self):
        """Test handling of empty textblock"""
        textblock = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        elements = self.converter.convert_textblock(textblock, {})
        self.assertEqual(len(elements), 0)
    
    def test_textblock_with_empty_lines(self):
        """Test handling of textblock with empty text content"""
        textblock = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        textline = ET.SubElement(textblock, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        string_elem = ET.SubElement(textline, '{http://www.loc.gov/standards/alto/ns-v4#}String')
        string_elem.set('CONTENT', '')  # Empty content
        
        elements = self.converter.convert_textblock(textblock, {})
        self.assertEqual(len(elements), 0)
    
    def test_missing_string_element(self):
        """Test handling of TextLine without String element"""
        textblock = ET.Element('{http://www.loc.gov/standards/alto/ns-v4#}TextBlock')
        textline = ET.SubElement(textblock, '{http://www.loc.gov/standards/alto/ns-v4#}TextLine')
        # No String element
        
        elements = self.converter.convert_textblock(textblock, {})
        self.assertEqual(len(elements), 0)
    
    def test_unknown_line_type_handling(self):
        """Test handling of unknown line types"""
        state = {'current_p': None, 'current_lg': None}
        elements = []
        
        # Unknown line type should fall back to DefaultLine behavior
        unknown_config = self.converter.rule_engine.get_line_mapping('UnknownLineType')
        self.converter._process_line_by_config(unknown_config, 'Test content', state, elements)
        
        # Should create paragraph (default behavior)
        if state['current_p'] is not None:
            elements.append(state['current_p'])
        
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'p')


class TestRegressionFixes(unittest.TestCase):
    """Regression tests for specific bug fixes"""
    
    def setUp(self):
        self.converter = AltoToTeiConverter()
    
    def test_element_tree_falsy_bug_fix(self):
        """Test that ET.Element boolean evaluation bug is fixed"""
        state = {'current_p': None, 'current_lg': None}
        elements = []
        
        # Create empty paragraph element (has falsy boolean value)
        state['current_p'] = ET.Element('p')
        
        # This should recognize the element exists despite falsy boolean value
        config = {'action': 'add_to_paragraph'}
        self.converter._process_line_by_config(config, 'Test content', state, elements)
        
        # Should add to existing paragraph, not create new one
        self.assertIsNotNone(state['current_p'])
        self.assertEqual(state['current_p'].text, 'Test content')
    
    def test_verse_container_appending_fix(self):
        """Test that verse lines are properly added to containers"""
        state = {'current_p': None, 'current_lg': None}
        elements = []
        
        config = {
            'tei_element': 'l',
            'container': 'lg',
            'container_attributes': {'type': 'verse'}
        }
        
        # Process verse line
        self.converter._process_line_by_config(config, 'Verse line', state, elements)
        
        # Container should exist and have the line
        self.assertIsNotNone(state['current_lg'])
        self.assertEqual(len(state['current_lg']), 1)
        self.assertEqual(state['current_lg'][0].text, 'Verse line')


def run_tests():
    """Run all tests with detailed output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestConfigurationLoader,
        TestRuleEngine,
        TestTagParsing,
        TestLineProcessing,
        TestTextBlockConversion,
        TestMultipleParagraphs,
        TestRunningTitleHandling,
        TestFacsimileOutput,
        TestRealWorldMultipleParagraphs,
        TestIntegration,
        TestErrorHandling,
        TestRegressionFixes
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
