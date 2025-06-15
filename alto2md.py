#!/usr/bin/env python3
"""
Convert eScriptorium ALTO XML output to Markdown format

This module reuses the ALTO parsing architecture from alto2tei.py
but generates Markdown output instead of TEI XML.
"""

import xml.etree.ElementTree as ET
import glob
import os
import re
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from alto2tei import ConfigurationLoader as BaseConfigurationLoader, AltoToTeiConverter

class MarkdownConfigurationLoader(BaseConfigurationLoader):
    """Loads and manages ALTO-Markdown transformation rules from YAML configuration"""
    
    def __init__(self, config_path: str = "config/alto_markdown_mapping.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def get_markdown_structure(self) -> Dict[str, Any]:
        """Get Markdown structure configuration"""
        return self.config.get('markdown_structure', {})
    
    def get_page_handling(self) -> Dict[str, Any]:
        """Get page handling configuration"""
        return self.config.get('page_handling', {})

class MarkdownRuleEngine:
    """Processes YAML-based rules for ALTO to Markdown conversion"""
    
    def __init__(self, config_loader: MarkdownConfigurationLoader):
        self.config = config_loader
        self.block_types = config_loader.get_block_types()
        self.line_types = config_loader.get_line_types()
        self.markdown_structure = config_loader.get_markdown_structure()
        self.page_handling = config_loader.get_page_handling()
    
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
    
    def get_line_mapping(self, line_type: str) -> Dict[str, Any]:
        """Get Markdown mapping configuration for a line type"""
        return self.line_types.get(line_type, self.line_types.get('DefaultLine', {}))
    
    def get_paragraph_separator(self) -> str:
        """Get paragraph separator for Markdown"""
        return self.markdown_structure.get('paragraph_separator', '\n\n')
    
    def get_line_separator(self) -> str:
        """Get line separator for Markdown"""
        return self.markdown_structure.get('line_separator', '  \n')
    
    def should_preserve_line_breaks(self) -> bool:
        """Check if line breaks should be preserved"""
        return self.markdown_structure.get('preserve_line_breaks', True)
    
    def should_include_page_breaks(self) -> bool:
        """Check if page breaks should be included"""
        return self.page_handling.get('include_page_breaks', True)
    
    def get_page_break_template(self) -> str:
        """Get page break template"""
        return self.page_handling.get('page_break_template', '\n\n---\n*Page {page_number}*\n---\n\n')

class AltoToMarkdownConverter:
    """Convert ALTO XML to Markdown format using configuration-driven approach"""
    
    def __init__(self, config_path: str = "config/alto_markdown_mapping.yaml"):
        # Reuse ALTO parsing logic from TEI converter
        self.tei_converter = AltoToTeiConverter()
        self.alto_ns = self.tei_converter.alto_ns
        
        # Load Markdown-specific configuration
        self.config_loader = MarkdownConfigurationLoader(config_path)
        self.rule_engine = MarkdownRuleEngine(self.config_loader)
    
    def convert_alto_to_markdown(self, alto_file: Path) -> str:
        """Convert an ALTO file to Markdown text"""
        
        # Parse ALTO file using existing logic
        tree = ET.parse(alto_file)
        alto_root = tree.getroot()
        tags_mapping = self.tei_converter.parse_alto_tags(alto_root)
        
        markdown_sections = []
        page_number = None
        
        # Process each page
        for page in alto_root.findall('.//alto:Page', self.alto_ns):
            page_content = []
            current_paragraph = []
            current_container = None
            container_lines = []
            
            # Process textblocks
            for textblock in page.findall('.//alto:TextBlock', self.alto_ns):
                block_type = self.tei_converter.get_block_type(textblock, tags_mapping)
                
                # Handle page number extraction
                if self.rule_engine.should_extract_page_number(block_type):
                    page_number = self.tei_converter.extract_page_number(textblock)
                    continue
                
                # Skip non-content blocks
                if not self.rule_engine.should_process_block(block_type):
                    continue
                
                # Process textlines
                for textline in textblock.findall('.//alto:TextLine', self.alto_ns):
                    string_elem = textline.find('alto:String', self.alto_ns)
                    if string_elem is None:
                        continue
                    
                    text_content = string_elem.get('CONTENT', '').strip()
                    if not text_content:
                        continue
                    
                    # Get line type and markdown mapping
                    line_type = self.tei_converter.get_line_type(textline, tags_mapping)
                    line_config = self.rule_engine.get_line_mapping(line_type)
                    
                    # Process line to markdown
                    result = self._process_line_to_markdown(
                        text_content, line_config, current_paragraph, 
                        current_container, container_lines, page_content
                    )
                    
                    if result:
                        current_paragraph, current_container, container_lines = result
            
            # Finalize any remaining content
            self._finalize_page_content(current_paragraph, current_container, 
                                      container_lines, page_content)
            
            # Add page break if configured and we have content
            if page_content and self.rule_engine.should_include_page_breaks() and page_number:
                page_break = self.rule_engine.get_page_break_template().format(page_number=page_number)
                markdown_sections.append(page_break + '\n'.join(page_content))
            elif page_content:
                markdown_sections.append('\n'.join(page_content))
        
        return self.rule_engine.get_paragraph_separator().join(markdown_sections)
    
    def _process_line_to_markdown(self, text: str, config: Dict, current_paragraph: List[str],
                                current_container: str, container_lines: List[str], 
                                page_content: List[str]) -> Optional[Tuple]:
        """Process a single line to markdown format"""
        
        template = config.get('template', '{text}')
        markdown_format = config.get('markdown_format', 'paragraph')
        
        # Handle standalone elements
        if config.get('standalone'):
            # Finalize current paragraph if exists
            if current_paragraph:
                page_content.append(' '.join(current_paragraph))
                current_paragraph = []
            
            # Finalize current container if exists
            if current_container and container_lines:
                page_content.append('\n'.join(container_lines))
                container_lines = []
                current_container = None
            
            # Add standalone element
            if markdown_format == 'divider':
                page_content.append(template)  # Don't format dividers with text
            else:
                page_content.append(template.format(text=text))
            
            return current_paragraph, current_container, container_lines
        
        # Handle container elements (like poetry)
        if config.get('container'):
            container_type = config['container']
            
            # If switching containers, finalize previous
            if current_container and current_container != container_type:
                if container_lines:
                    page_content.append('\n'.join(container_lines))
                container_lines = []
            
            # Add to container
            current_container = container_type
            container_lines.append(template.format(text=text))
            
            return current_paragraph, current_container, container_lines
        
        # Handle paragraph elements
        if config.get('add_to_paragraph') or config.get('starts_paragraph'):
            # If starting new paragraph, finalize previous
            if config.get('starts_paragraph') and current_paragraph:
                page_content.append(' '.join(current_paragraph))
                current_paragraph = []
            
            # Add to current paragraph
            current_paragraph.append(template.format(text=text))
            
            return current_paragraph, current_container, container_lines
        
        # Default: treat as standalone
        if current_paragraph:
            page_content.append(' '.join(current_paragraph))
            current_paragraph = []
        
        page_content.append(template.format(text=text))
        return current_paragraph, current_container, container_lines
    
    def _finalize_page_content(self, current_paragraph: List[str], current_container: str,
                             container_lines: List[str], page_content: List[str]) -> None:
        """Finalize any remaining content at end of page"""
        
        # Finalize paragraph
        if current_paragraph:
            page_content.append(' '.join(current_paragraph))
        
        # Finalize container
        if current_container and container_lines:
            page_content.append('\n'.join(container_lines))
    
    def save_markdown(self, markdown_content: str, output_file: Path) -> None:
        """Save Markdown content to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    
    def process_all_alto_files(self, input_folder: str, output_folder: str, 
                             suffix: str = "_md") -> None:
        """Process all ALTO files in a folder and convert to Markdown"""
        
        input_path = Path(input_folder)
        output_path = Path(output_folder)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all ALTO XML files
        alto_files = list(input_path.glob("*.xml"))
        
        if not alto_files:
            print(f"No XML files found in {input_folder}")
            return
        
        print(f"Converting {len(alto_files)} ALTO files to Markdown...")
        
        for alto_file in alto_files:
            try:
                # Convert to markdown
                markdown_content = self.convert_alto_to_markdown(alto_file)
                
                # Create output filename
                output_filename = alto_file.stem + suffix + ".md"
                output_file = output_path / output_filename
                
                # Save markdown
                self.save_markdown(markdown_content, output_file)
                
                print(f"✅ {alto_file.name} → {output_filename}")
                
            except Exception as e:
                print(f"❌ Error converting {alto_file.name}: {e}")
        
        print(f"Conversion complete! Markdown files saved to {output_folder}")

def main():
    """Command-line interface for ALTO to Markdown conversion"""
    
    parser = argparse.ArgumentParser(
        description='Convert eScriptorium ALTO XML files to Markdown format'
    )
    
    parser.add_argument('input_folder', nargs='?', default='alto',
                       help='Input folder containing ALTO XML files (default: alto)')
    parser.add_argument('output_folder', nargs='?', default='markdown',
                       help='Output folder for Markdown files (default: markdown)')
    
    parser.add_argument('--input', '-i', dest='input_folder_flag',
                       help='Input folder (alternative to positional argument)')
    parser.add_argument('--output', '-o', dest='output_folder_flag',
                       help='Output folder (alternative to positional argument)')
    parser.add_argument('--suffix', '-s', default='_md',
                       help='Suffix to add to output filenames (default: _md)')
    parser.add_argument('--config', '-c', default='config/alto_markdown_mapping.yaml',
                       help='Path to YAML configuration file')
    
    args = parser.parse_args()
    
    # Use flag values if provided, otherwise use positional arguments
    input_folder = args.input_folder_flag or args.input_folder
    output_folder = args.output_folder_flag or args.output_folder
    
    print("🔄 ALTO to Markdown Converter")
    print("=" * 40)
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Configuration: {args.config}")
    print("=" * 40)
    
    try:
        converter = AltoToMarkdownConverter(args.config)
        converter.process_all_alto_files(input_folder, output_folder, args.suffix)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())