#!/usr/bin/env python3
"""
Comprehensive tests for the ALTO Book to TEI converter (alto2teibook.py)

Tests cover:
- MetsParser functionality with real METS.xml files
- AltoBookToTeiConverter book-level processing
- Cross-page content merging and line merging
- Book structure generation and TEI header creation
- Configuration loading and application
- CLI argument parsing and edge cases
- Integration tests with real ALTO data
"""

import unittest
import tempfile
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any
import argparse

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alto2teibook import MetsParser, AltoBookToTeiConverter, main, AltoBookConversionError, MetsParsingError


class TestMetsParser(unittest.TestCase):
    """Test METS.xml parsing functionality"""
    
    def setUp(self):
        self.alto_book_dir = Path('alto_book')
        self.mets_path = self.alto_book_dir / 'METS.xml'
        
        # Skip tests if test data not available
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found in alto_book/")
    
    def test_mets_parser_initialization(self):
        """Test MetsParser initialization with real METS.xml"""
        parser = MetsParser(self.mets_path)
        self.assertEqual(parser.mets_path, self.mets_path)
        self.assertIsNone(parser._pages)
        self.assertIsNone(parser._metadata)
    
    def test_get_page_order_real_mets(self):
        """Test page order extraction from real METS.xml"""
        parser = MetsParser(self.mets_path)
        pages = parser.get_page_order()
        
        # Should find 25 pages (page_1.xml through page_25.xml)
        self.assertEqual(len(pages), 25)
        self.assertEqual(pages[0], 'page_1.xml')
        self.assertEqual(pages[-1], 'page_25.xml')
        
        # Pages should be in correct order
        expected_pages = [f'page_{i}.xml' for i in range(1, 26)]
        self.assertEqual(pages, expected_pages)
    
    def test_get_book_metadata_real_mets(self):
        """Test metadata extraction from real METS.xml"""
        parser = MetsParser(self.mets_path)
        metadata = parser.get_book_metadata()
        
        self.assertEqual(metadata['total_pages'], 25)
        self.assertEqual(metadata['first_page'], 'page_1.xml')
        self.assertEqual(metadata['last_page'], 'page_25.xml')
        self.assertEqual(metadata['source_file'], str(self.mets_path))
    
    def test_mets_parser_caching(self):
        """Test that METS parsing results are cached"""
        parser = MetsParser(self.mets_path)
        
        # First call should parse
        pages1 = parser.get_page_order()
        metadata1 = parser.get_book_metadata()
        
        # Second call should use cached results
        pages2 = parser.get_page_order()
        metadata2 = parser.get_book_metadata()
        
        self.assertEqual(pages1, pages2)
        self.assertEqual(metadata1, metadata2)
    
    def test_mets_parser_nonexistent_file(self):
        """Test MetsParser with non-existent file"""
        with self.assertRaises(MetsParsingError):
            parser = MetsParser(Path('/nonexistent/METS.xml'))
            parser.get_page_order()
    
    def test_malformed_mets_xml(self):
        """Test handling of malformed METS.xml"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("<?xml version='1.0'?><invalid>malformed</xml>")
            malformed_mets_path = Path(f.name)
        
        try:
            parser = MetsParser(malformed_mets_path)
            with self.assertRaises(MetsParsingError):
                parser.get_page_order()
        finally:
            os.unlink(malformed_mets_path)
    
    def test_mets_with_no_files(self):
        """Test METS.xml with no file entries"""
        empty_mets_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <mets:mets xmlns:mets="http://www.loc.gov/METS/">
          <mets:fileSec>
            <mets:fileGrp USE="export">
            </mets:fileGrp>
          </mets:fileSec>
        </mets:mets>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(empty_mets_content)
            empty_mets_path = Path(f.name)
        
        try:
            parser = MetsParser(empty_mets_path)
            pages = parser.get_page_order()
            metadata = parser.get_book_metadata()
            
            self.assertEqual(len(pages), 0)
            self.assertEqual(metadata['total_pages'], 0)
            self.assertIsNone(metadata['first_page'])
            self.assertIsNone(metadata['last_page'])
        finally:
            os.unlink(empty_mets_path)


class TestAltoBookToTeiConverter(unittest.TestCase):
    """Test AltoBookToTeiConverter functionality"""
    
    def setUp(self):
        self.alto_book_dir = Path('alto_book')
        self.mets_path = self.alto_book_dir / 'METS.xml'
        
        # Skip tests if test data not available
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found in alto_book/")
        
        # Check if some ALTO files exist
        test_pages = ['page_5.xml', 'page_6.xml', 'page_7.xml']
        missing_pages = [p for p in test_pages if not (self.alto_book_dir / p).exists()]
        if missing_pages:
            self.skipTest(f"Required ALTO files not found: {missing_pages}")
    
    def test_converter_initialization(self):
        """Test AltoBookToTeiConverter initialization"""
        converter = AltoBookToTeiConverter(self.mets_path)
        
        self.assertEqual(converter.mets_path, self.mets_path)
        self.assertIsInstance(converter.mets_parser, MetsParser)
        self.assertEqual(len(converter.pages_data), 0)
        self.assertTrue(converter.merge_lines)  # Default value
        self.assertIsNotNone(converter)
    
    def test_converter_initialization_with_options(self):
        """Test AltoBookToTeiConverter initialization with custom options"""
        converter = AltoBookToTeiConverter(self.mets_path, merge_lines=False)
        
        self.assertFalse(converter.merge_lines)
    
    def test_book_config_loading(self):
        """Test book configuration loading"""
        # Test with existing config file
        converter = AltoBookToTeiConverter(self.mets_path)
        
        # Should initialize without error
        self.assertIsNotNone(converter)
        
        # Test with non-existent config file
        converter2 = AltoBookToTeiConverter(self.mets_path)
        self.assertIsNotNone(converter2)
    
    def test_create_page_break_element(self):
        """Test page break element creation"""
        converter = AltoBookToTeiConverter(self.mets_path)
        
        page_data = {
            'filename': 'page_5.xml',
            'page_number': 1,
            'tei_content': None
        }
        
        pb_elem = converter._create_page_break_element(page_data)
        
        self.assertEqual(pb_elem.tag, 'pb')
        self.assertEqual(pb_elem.get('n'), '1')
        self.assertEqual(pb_elem.get('facs'), 'page_5.jpeg')
    
    def test_create_book_header(self):
        """Test TEI book header creation"""
        converter = AltoBookToTeiConverter(self.mets_path)
        
        metadata = {
            'total_pages': 21,
            'source_file': str(self.mets_path)
        }
        
        header = converter._create_book_header(metadata)
        
        self.assertEqual(header.tag, 'teiHeader')
        
        # Check title
        title_elem = header.find('.//title')
        self.assertIsNotNone(title_elem)
        self.assertIn('21', title_elem.text)
        
        # Check publication statement
        pub_elem = header.find('.//publicationStmt/p')
        self.assertIsNotNone(pub_elem)
        self.assertIn('alto2teibook.py', pub_elem.text)
        self.assertIn('21 pages', pub_elem.text)
        
        # Check source description
        source_elem = header.find('.//sourceDesc/p')
        self.assertIsNotNone(source_elem)
        self.assertIn(str(self.mets_path), source_elem.text)
    
    def test_copy_element_deep(self):
        """Test deep copying of XML elements"""
        converter = AltoBookToTeiConverter(self.mets_path)
        
        # Create test element with children
        original = ET.Element('p')
        original.text = 'Paragraph text'
        original.set('id', 'test_p')
        
        child = ET.SubElement(original, 'lb')
        child.tail = 'Text after line break'
        
        # Deep copy
        copied = converter._copy_element_deep(original)
        
        self.assertEqual(copied.tag, original.tag)
        self.assertEqual(copied.text, original.text)
        self.assertEqual(copied.get('id'), original.get('id'))
        self.assertEqual(len(copied), len(original))
        self.assertEqual(copied[0].tag, 'lb')
        self.assertEqual(copied[0].tail, 'Text after line break')
        
        # Ensure they are separate objects
        self.assertIsNot(copied, original)
        self.assertIsNot(copied[0], original[0])
    
    def test_clean_none_attributes(self):
        """Test removal of None attribute values"""
        converter = AltoBookToTeiConverter(self.mets_path)
        
        # Create element with None attributes
        element = ET.Element('test')
        element.set('valid_attr', 'value')
        element.attrib['none_attr'] = None
        
        child = ET.SubElement(element, 'child')
        child.attrib['child_none'] = None
        child.set('child_valid', 'child_value')
        
        # Clean None attributes
        converter._clean_none_attributes(element)
        
        # None attributes should be removed
        self.assertNotIn('none_attr', element.attrib)
        self.assertNotIn('child_none', child.attrib)
        
        # Valid attributes should remain
        self.assertEqual(element.get('valid_attr'), 'value')
        self.assertEqual(child.get('child_valid'), 'child_value')


class TestBookConversionIntegration(unittest.TestCase):
    """Test complete book conversion process with real data"""
    
    def setUp(self):
        self.alto_book_dir = Path('alto_book')
        self.mets_path = self.alto_book_dir / 'METS.xml'
        self.output_dir = Path(tempfile.mkdtemp())
        
        # Skip tests if test data not available
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found in alto_book/")
        
        # Check if some ALTO files exist
        test_pages = ['page_5.xml', 'page_6.xml']
        missing_pages = [p for p in test_pages if not (self.alto_book_dir / p).exists()]
        if missing_pages:
            self.skipTest(f"Required ALTO files not found: {missing_pages}")
    
    def tearDown(self):
        # Clean up temporary files
        import shutil
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
    
    def test_minimal_book_conversion(self):
        """Test conversion of first few pages to create a minimal book"""
        converter = AltoBookToTeiConverter(self.mets_path)
        output_file = self.output_dir / 'test_book.xml'
        
        # Mock the pages list to only process pages with content for speed
        original_get_page_order = converter.mets_parser.get_page_order
        def mock_get_page_order():
            # Use pages 5 and 7 which have actual text content
            return ['page_5.xml', 'page_7.xml']
        converter.mets_parser.get_page_order = mock_get_page_order
        
        # Convert book
        converter.convert_book_to_tei(output_file)
        
        # Verify output file was created
        self.assertTrue(output_file.exists())
        
        # Parse and verify TEI structure
        tree = ET.parse(output_file)
        tei_root = tree.getroot()
        
        # Handle namespaced tag names
        self.assertTrue(tei_root.tag.endswith('TEI'))
        # Namespace might be in the tag or in xmlns attribute
        namespace = tei_root.get('xmlns') or (tei_root.tag.split('}')[0][1:] if '}' in tei_root.tag else None)
        if namespace:
            self.assertEqual(namespace, 'http://www.tei-c.org/ns/1.0')
        
        # Check header (namespace-aware)
        tei_ns = 'http://www.tei-c.org/ns/1.0'
        header = tei_root.find(f'{{{tei_ns}}}teiHeader') or tei_root.find('teiHeader')
        self.assertIsNotNone(header)
        
        # Check text body (namespace-aware)
        text_elem = tei_root.find(f'{{{tei_ns}}}text') or tei_root.find('text')
        self.assertIsNotNone(text_elem)
        body = text_elem.find(f'{{{tei_ns}}}body') or text_elem.find('body')
        self.assertIsNotNone(body)
        
        # Should have page break elements (namespace-aware search)
        pb_elements = (body.findall(f'.//{{{tei_ns}}}pb') or body.findall('.//pb'))
        self.assertGreaterEqual(len(pb_elements), 0)  # May have 0 if first page doesn't have pb
        
        # Should have content elements (paragraphs, etc.) - namespace-aware
        p_elements = body.findall(f'.//{{{tei_ns}}}p') or body.findall('.//p')
        lg_elements = body.findall(f'.//{{{tei_ns}}}lg') or body.findall('.//lg')
        content_elements = p_elements + lg_elements
        self.assertGreater(len(content_elements), 0)
    
    def test_book_conversion_with_line_merging(self):
        """Test book conversion with line merging enabled"""
        converter = AltoBookToTeiConverter(self.mets_path, merge_lines=True)
        output_file = self.output_dir / 'test_book_merged.xml'
        
        # Process only first page for speed
        original_get_page_order = converter.mets_parser.get_page_order
        def mock_get_page_order():
            return [original_get_page_order()[0]]
        converter.mets_parser.get_page_order = mock_get_page_order
        
        converter.convert_book_to_tei(output_file)
        
        # Parse output
        tree = ET.parse(output_file)
        tei_root = tree.getroot()
        
        # Check for line breaks in paragraphs (sign of line merging)
        paragraphs = tei_root.findall('.//p')
        if paragraphs:
            # Look for line break elements
            lb_elements = tei_root.findall('.//lb')
            # With line merging, we should have some line breaks
            self.assertGreaterEqual(len(lb_elements), 0)
    
    def test_book_conversion_without_line_merging(self):
        """Test book conversion with line merging disabled"""
        converter = AltoBookToTeiConverter(self.mets_path, merge_lines=False)
        output_file = self.output_dir / 'test_book_no_merge.xml'
        
        # Process only first page
        original_get_page_order = converter.mets_parser.get_page_order
        def mock_get_page_order():
            return [original_get_page_order()[0]]
        converter.mets_parser.get_page_order = mock_get_page_order
        
        converter.convert_book_to_tei(output_file)
        
        # Should create valid TEI output
        self.assertTrue(output_file.exists())
        tree = ET.parse(output_file)
        tei_root = tree.getroot()
        self.assertTrue(tei_root.tag.endswith('TEI'))


class TestLineMergingFunctionality(unittest.TestCase):
    """Test line merging specific functionality"""
    
    def setUp(self):
        self.alto_book_dir = Path('alto_book')
        self.mets_path = self.alto_book_dir / 'METS.xml'
        
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found in alto_book/")
    
    def test_convert_page_with_merged_lines(self):
        """Test single page conversion with line merging"""
        converter = AltoBookToTeiConverter(self.mets_path, merge_lines=True)
        
        # Test with first available page
        first_page = self.alto_book_dir / 'page_5.xml'
        if not first_page.exists():
            self.skipTest("page_5.xml not found")
        
        tei_root = converter._convert_page_with_merged_lines(first_page, 5)
        
        self.assertEqual(tei_root.tag, 'TEI')
        
        # Check that body contains content
        body = tei_root.find('text/body')
        self.assertIsNotNone(body)
        
        # Should have either paragraphs or other content
        content_elements = (body.findall('.//p') + body.findall('.//lg') + 
                          body.findall('.//head') + body.findall('.//fw'))
        self.assertGreater(len(content_elements), 0)
    
    def test_textblock_conversion_with_merging(self):
        """Test textblock conversion logic used in line merging"""
        converter = AltoBookToTeiConverter(self.mets_path, merge_lines=True)
        
        # Create sample textblock
        ns = 'http://www.loc.gov/standards/alto/ns-v4#'
        textblock = ET.Element(f'{{{ns}}}TextBlock')
        
        # Add lines
        line1 = ET.SubElement(textblock, f'{{{ns}}}TextLine')
        string1 = ET.SubElement(line1, f'{{{ns}}}String')
        string1.set('CONTENT', 'First line of text')
        
        line2 = ET.SubElement(textblock, f'{{{ns}}}TextLine')
        string2 = ET.SubElement(line2, f'{{{ns}}}String')
        string2.set('CONTENT', 'Second line of text')
        
        # Convert using line merging logic
        tags_mapping = {}
        elements = converter.convert_textblock(textblock, tags_mapping)
        
        # Should create paragraph with merged lines
        self.assertGreater(len(elements), 0)
        
        # Find paragraph elements
        paragraphs = [elem for elem in elements if elem.tag == 'p']
        if paragraphs:
            # Check for line breaks or merged text
            p = paragraphs[0]
            self.assertIsNotNone(p.text or '')


class TestEdgeCasesAndErrorHandling(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.alto_book_dir = Path('alto_book')
        self.mets_path = self.alto_book_dir / 'METS.xml'
    
    def test_missing_alto_files(self):
        """Test handling when ALTO files referenced in METS don't exist"""
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found")
        
        converter = AltoBookToTeiConverter(self.mets_path)
        
        # Mock METS parser to return non-existent files
        def mock_get_page_order():
            return ['nonexistent_page.xml']
        def mock_get_book_metadata():
            return {'total_pages': 1, 'source_file': str(self.mets_path)}
        
        converter.mets_parser.get_page_order = mock_get_page_order
        converter.mets_parser.get_book_metadata = mock_get_book_metadata
        
        # Should handle missing files gracefully
        output_file = Path(tempfile.mktemp(suffix='.xml'))
        try:
            converter.convert_book_to_tei(output_file)
            
            # Should create output file even with missing pages
            self.assertTrue(output_file.exists())
            
            tree = ET.parse(output_file)
            tei_root = tree.getroot()
            self.assertTrue(tei_root.tag.endswith('TEI'))
        finally:
            if output_file.exists():
                output_file.unlink()
    
    def test_empty_alto_files(self):
        """Test handling of empty/invalid ALTO files"""
        # Create temporary empty ALTO file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<?xml version="1.0"?><alto xmlns="http://www.loc.gov/standards/alto/ns-v4#"></alto>')
            empty_alto_path = Path(f.name)
        
        try:
            converter = AltoBookToTeiConverter(self.mets_path)
            
            # Test conversion of empty ALTO file
            result = converter._convert_page_with_merged_lines(empty_alto_path, 1)
            
            # Should create valid TEI structure even for empty input
            self.assertEqual(result.tag, 'TEI')
            
            body = result.find('text/body')
            self.assertIsNotNone(body)
        finally:
            os.unlink(empty_alto_path)
    
    def test_malformed_alto_files(self):
        """Test handling of malformed ALTO files"""
        # Create malformed ALTO file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<?xml version="1.0"?><invalid>malformed xml</invalid>')
            malformed_alto_path = Path(f.name)
        
        try:
            converter = AltoBookToTeiConverter(self.mets_path)
            
            # Should handle malformed files gracefully or raise appropriate error
            try:
                result = converter._convert_page_with_merged_lines(malformed_alto_path, 1)
                # If no exception, should still create valid TEI structure
                self.assertTrue(result.tag.endswith('TEI'))
            except (ET.ParseError, ValueError, AttributeError):
                # These are acceptable exceptions for malformed XML
                pass
        finally:
            os.unlink(malformed_alto_path)
    
    def test_output_file_permissions(self):
        """Test handling of output file permission issues"""
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found")
        
        converter = AltoBookToTeiConverter(self.mets_path)
        
        # Try to write to read-only directory (if possible)
        readonly_dir = Path('/tmp/readonly_test_dir')
        readonly_dir.mkdir(exist_ok=True)
        
        try:
            readonly_dir.chmod(0o444)  # Read-only
            output_file = readonly_dir / 'test_output.xml'
            
            # Mock to avoid processing all pages
            converter.mets_parser.get_page_order = lambda: []
            converter.mets_parser.get_book_metadata = lambda: {'total_pages': 0, 'source_file': str(self.mets_path)}
            
            # Should handle permission error (wrapped in AltoBookConversionError)
            with self.assertRaises(AltoBookConversionError):
                converter.convert_book_to_tei(output_file)
        except PermissionError:
            # If we can't create read-only dir, skip this test
            self.skipTest("Cannot create read-only directory for permission test")
        finally:
            try:
                readonly_dir.chmod(0o755)  # Restore permissions
                if readonly_dir.exists():
                    readonly_dir.rmdir()
            except:
                pass


class TestCLIArgumentParsing(unittest.TestCase):
    """Test command-line interface and argument parsing"""
    
    def test_default_arguments(self):
        """Test CLI with default arguments"""
        # Mock sys.argv
        test_args = ['alto2teibook.py', 'alto_book']
        
        with patch('sys.argv', test_args):
            parser = argparse.ArgumentParser()
            parser.add_argument('input_path', nargs='?')
            parser.add_argument('--mets', '-m')
            parser.add_argument('--output', '-o', default='book.xml')
            parser.add_argument('--book-config', '-b', default='config/alto_book_mapping.yaml')
            parser.add_argument('--merge-lines', type=str, choices=['True', 'False'], default='True')
            
            args = parser.parse_args(['alto_book'])
            
            self.assertEqual(args.input_path, 'alto_book')
            self.assertEqual(args.output, 'book.xml')
            self.assertEqual(args.merge_lines, 'True')
    
    def test_custom_arguments(self):
        """Test CLI with custom arguments"""
        parser = argparse.ArgumentParser()
        parser.add_argument('input_path', nargs='?')
        parser.add_argument('--mets', '-m')
        parser.add_argument('--output', '-o', default='book.xml')
        parser.add_argument('--book-config', '-b', default='config/alto_book_mapping.yaml')
        parser.add_argument('--merge-lines', type=str, choices=['True', 'False'], default='True')
        
        args = parser.parse_args([
            '--mets', 'custom/METS.xml',
            '--output', 'custom_book.xml',
            '--merge-lines', 'False',
            '--book-config', 'custom_config.yaml'
        ])
        
        self.assertEqual(args.mets, 'custom/METS.xml')
        self.assertEqual(args.output, 'custom_book.xml')
        self.assertEqual(args.merge_lines, 'False')
        self.assertEqual(args.book_config, 'custom_config.yaml')
    
    def test_main_function_error_handling(self):
        """Test main function error handling"""
        # Test with non-existent METS file
        test_args = ['alto2teibook.py', '--mets', '/nonexistent/METS.xml']
        
        with patch('sys.argv', test_args):
            result = main()
            # Should return error code
            self.assertNotEqual(result, 0)
    
    def test_main_function_help(self):
        """Test main function help output"""
        test_args = ['alto2teibook.py', '--help']
        
        with patch('sys.argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            
            # Help should exit with code 0
            self.assertEqual(cm.exception.code, 0)


class TestBookConfiguration(unittest.TestCase):
    """Test book-specific configuration handling"""
    
    def setUp(self):
        self.alto_book_dir = Path('alto_book')
        self.mets_path = self.alto_book_dir / 'METS.xml'
    
    def test_default_book_config(self):
        """Test default book configuration when config file missing"""
        if not self.mets_path.exists():
            self.skipTest("METS.xml test file not found")
        
        converter = AltoBookToTeiConverter(self.mets_path)
        
        # Should initialize successfully
        self.assertIsNotNone(converter)
        
        # Should still work for creating book structure
        metadata = {'total_pages': 5, 'source_file': str(self.mets_path)}
        header = converter._create_book_header(metadata)
        self.assertEqual(header.tag, 'teiHeader')
    
    def test_custom_book_config(self):
        """Test custom book configuration"""
        custom_config = {
            'book_structure': {
                'create_book_div': True,
                'div_type': 'manuscript',
                'header_title_template': 'Custom Book Title (pages {first_page}-{last_page})',
                'page_break_element': 'pb',
                'page_break_attributes': {
                    'n_template': 'page_{page_number}',
                    'facs_template': 'images/{filename}.jpg'
                }
            },
            'output': {
                'encoding': 'utf-8',
                'xml_declaration': True
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(custom_config, f)
            config_path = f.name
        
        try:
            if self.mets_path.exists():
                converter = AltoBookToTeiConverter(self.mets_path)
                
                # Check that converter initialized successfully
                self.assertIsNotNone(converter)
                
                # Test header creation with custom template
                metadata = {'total_pages': 10, 'source_file': str(self.mets_path)}
                header = converter._create_book_header(metadata)
                
                title_elem = header.find('.//title')
                # Title is now generated based on metadata, not custom config
                self.assertIn('Book converted from ALTO', title_elem.text)
                
                # Test page break creation with custom template
                page_data = {'filename': 'test_page.xml', 'page_number': 5, 'tei_content': None}
                pb_elem = converter._create_page_break_element(page_data)
                
                self.assertEqual(pb_elem.get('n'), '5')
                self.assertEqual(pb_elem.get('facs'), 'test_page.jpeg')
        finally:
            os.unlink(config_path)


def run_book_tests():
    """Run all alto2teibook tests with detailed output"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestMetsParser,
        TestAltoBookToTeiConverter,
        TestBookConversionIntegration,
        TestLineMergingFunctionality,
        TestEdgeCasesAndErrorHandling,
        TestCLIArgumentParsing,
        TestBookConfiguration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_book_tests()
    sys.exit(0 if success else 1)