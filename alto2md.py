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
    
    def get_line_merging(self) -> Dict[str, Any]:
        """Get line merging configuration"""
        return self.config.get('line_merging', {})
    
    def get_hyphenation(self) -> Dict[str, Any]:
        """Get hyphenation configuration"""
        return self.config.get('hyphenation', {})

class MarkdownRuleEngine:
    """Processes YAML-based rules for ALTO to Markdown conversion"""
    
    def __init__(self, config_loader: MarkdownConfigurationLoader):
        self.config = config_loader
        self.block_types = config_loader.get_block_types()
        self.line_types = config_loader.get_line_types()
        self.markdown_structure = config_loader.get_markdown_structure()
        self.page_handling = config_loader.get_page_handling()
        self.line_merging = config_loader.get_line_merging()
        self.hyphenation = config_loader.get_hyphenation()
    
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
    
    def should_merge_lines(self) -> bool:
        """Check if line merging is enabled"""
        return self.line_merging.get('enabled', False)
    
    def should_merge_paragraph_lines(self) -> bool:
        """Check if paragraph lines should be merged"""
        return self.line_merging.get('merge_paragraph_lines', True)
    
    def should_merge_verse_lines(self) -> bool:
        """Check if verse lines should be merged"""
        return self.line_merging.get('merge_verse_lines', False)
    
    def get_line_joiner(self) -> str:
        """Get string to join lines within paragraphs"""
        return self.line_merging.get('line_joiner', ' ')
    
    def should_handle_hyphenation(self) -> bool:
        """Check if hyphenation handling is enabled"""
        return self.hyphenation.get('enabled', True)
    
    def get_hyphen_patterns(self) -> list:
        """Get list of hyphenation patterns"""
        return self.hyphenation.get('hyphen_patterns', ['-$', '—$', '–$'])
    
    def get_word_break_chars(self) -> list:
        """Get list of characters that indicate word breaks"""
        return self.hyphenation.get('word_break_chars', ['-', '—', '–'])

class AltoToMarkdownConverter:
    """Convert ALTO XML to Markdown format using configuration-driven approach"""
    
    def __init__(self, config_path: str = "config/alto_markdown_mapping.yaml", merge_lines: bool = False):
        # Reuse ALTO parsing logic from TEI converter
        self.tei_converter = AltoToTeiConverter()
        self.alto_ns = self.tei_converter.alto_ns
        
        # Load Markdown-specific configuration
        self.config_loader = MarkdownConfigurationLoader(config_path)
        self.rule_engine = MarkdownRuleEngine(self.config_loader)
        
        # Override line merging setting if specified
        self.merge_lines = merge_lines
    
    def convert_alto_to_markdown(self, alto_file: Path) -> str:
        """Convert an ALTO file to Markdown text"""
        
        # Parse ALTO file using existing logic
        tree = ET.parse(alto_file)
        alto_root = tree.getroot()
        tags_mapping = self.tei_converter.parse_alto_tags(alto_root)
        
        # Check if line merging is enabled (either from config or parameter)
        merge_enabled = self.merge_lines or self.rule_engine.should_merge_lines()
        
        if merge_enabled:
            return self._convert_with_line_merging(alto_root, tags_mapping)
        else:
            return self._convert_without_line_merging(alto_root, tags_mapping)
    
    def _convert_without_line_merging(self, alto_root, tags_mapping) -> str:
        """Convert without line merging (original behavior)"""
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
    
    def _convert_with_line_merging(self, alto_root, tags_mapping) -> str:
        """Convert with line merging enabled"""
        # Collect line groups with block separation
        all_block_groups = []
        page_number = None
        
        # Process each page
        for page in alto_root.findall('.//alto:Page', self.alto_ns):
            page_content = []
            
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
                
                # Collect lines within this specific textblock
                block_line_groups = []  # (paragraph_type, markdown_content)
                paragraph_start_counter = 0  # Counter for unique paragraph_start IDs
                current_paragraph_id = None  # Track current paragraph for continuation
                
                # Process textlines within this textblock
                for textline in textblock.findall('.//alto:TextLine', self.alto_ns):
                    string_elem = textline.find('alto:String', self.alto_ns)
                    if string_elem is None:
                        continue

                    text_content = string_elem.get('CONTENT', '').strip()
                    if not text_content:
                        continue

                    # Get line type and markdown mapping
                    line_type = self.tei_converter.get_line_type(textline, tags_mapping)

                    # Special handling: if line is in NumberingZone, treat as PageNumberLine
                    if block_type == "NumberingZone":
                        line_type = "PageNumberLine"

                    line_config = self.rule_engine.get_line_mapping(line_type)

                    # Skip lines marked for skipping
                    if line_config.get('markdown_format') == 'skip':
                        continue

                    # Get paragraph type, but also consider block type for zone separation
                    paragraph_type = line_config.get('paragraph_type', 'default')

                    # Special handling for paragraph_start: starts new paragraph, DefaultLine continues it
                    if paragraph_type == 'paragraph_start':
                        # Create unique paragraph group for each paragraph_start line
                        current_paragraph_id = f"{block_type}:paragraph_{paragraph_start_counter}"
                        paragraph_type_with_block = current_paragraph_id
                        paragraph_start_counter += 1
                    elif paragraph_type == 'paragraph' and current_paragraph_id:
                        # DefaultLine continues the current paragraph started by paragraph_start
                        paragraph_type_with_block = current_paragraph_id
                    else:
                        # Add block type as prefix to prevent cross-block merging
                        paragraph_type_with_block = f"{block_type}:{paragraph_type}"
                        # Reset paragraph continuation for non-paragraph types
                        if paragraph_type not in ['paragraph', 'paragraph_start']:
                            current_paragraph_id = None

                    # Process line to markdown
                    markdown_line = self._process_line_to_markdown_simple(text_content, line_config)
                    
                    if markdown_line:  # Only add non-empty lines
                        block_line_groups.append((paragraph_type_with_block, markdown_line))

                # Process this block's lines and add to page content
                if block_line_groups:
                    block_merged_paragraphs = self._merge_line_groups(block_line_groups)
                    page_content.extend(block_merged_paragraphs)

            # Add page break if configured and we have content
            if page_content and self.rule_engine.should_include_page_breaks() and page_number:
                page_break = self.rule_engine.get_page_break_template().format(page_number=page_number)
                all_block_groups.append(page_break + '\n'.join(page_content))
            elif page_content:
                all_block_groups.append('\n'.join(page_content))

        # Join all pages with appropriate separation
        return self.rule_engine.get_paragraph_separator().join(all_block_groups)
    
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
    
    def _process_line_to_markdown_simple(self, text: str, config: Dict) -> Optional[str]:
        """Process a single line to markdown format (simplified for merging)"""
        
        markdown_format = config.get('markdown_format', 'paragraph')
        template = config.get('template', '{text}')
        
        # Skip lines marked for skipping (like dividers)
        if markdown_format == 'skip':
            return None
        
        # For markdown output, apply the template
        return template.format(text=text)
    
    def _merge_line_groups(self, line_groups) -> list:
        """Group consecutive lines of same type and merge them"""
        if not line_groups:
            return []
        
        merged_paragraphs = []
        current_group = []
        current_type = None
        
        for paragraph_type, markdown_line in line_groups:
            # If type changes, finalize current group
            if current_type is not None and current_type != paragraph_type:
                if current_group:
                    merged_text = self._merge_lines_in_group(current_group, current_type)
                    if merged_text:
                        merged_paragraphs.append(merged_text)
                current_group = []
            
            current_type = paragraph_type
            current_group.append(markdown_line)
        
        # Finalize last group
        if current_group and current_type:
            merged_text = self._merge_lines_in_group(current_group, current_type)
            if merged_text:
                merged_paragraphs.append(merged_text)
        
        return merged_paragraphs
    
    def _merge_lines_in_group(self, lines: list, paragraph_type: str) -> str:
        """Merge lines within a group, handling hyphenation"""
        if not lines:
            return ""
        
        # Extract the base paragraph type (remove block prefix and paragraph counter)
        base_type = paragraph_type.split(':')[-1] if ':' in paragraph_type else paragraph_type
        
        # Handle paragraph types (both paragraph_start and continued paragraphs)
        if base_type.startswith('paragraph'):
            base_type = 'paragraph'
        
        # Check if this paragraph type should be merged
        if base_type == "paragraph" and not self.rule_engine.should_merge_paragraph_lines():
            return '\n'.join(lines)
        elif base_type == "verse" and not self.rule_engine.should_merge_verse_lines():
            return '\n'.join(lines)
        elif base_type not in ["paragraph", "verse"]:
            # For speakers, stage directions, etc., keep them separate
            return '\n'.join(lines)
        
        # Handle hyphenation if enabled
        if self.rule_engine.should_handle_hyphenation():
            lines = self._handle_hyphenation(lines)
        
        # Join with appropriate separator
        joiner = self.rule_engine.get_line_joiner()
        return joiner.join(lines)
    
    def _handle_hyphenation(self, lines: list) -> list:
        """Handle hyphenation by joining hyphenated words across lines"""
        
        if len(lines) <= 1:
            return lines
        
        patterns = self.rule_engine.get_hyphen_patterns()
        word_break_chars = self.rule_engine.get_word_break_chars()
        
        # Run hyphenation handling in a loop until no more changes
        current_lines = lines[:]
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            processed_lines = []
            i = 0
            changes_made = False
            
            while i < len(current_lines):
                current_line = current_lines[i]
                
                # Check if current line ends with hyphenation
                is_hyphenated = False
                for pattern in patterns:
                    if re.search(pattern, current_line):
                        is_hyphenated = True
                        break
                
                if is_hyphenated and i + 1 < len(current_lines):
                    # Remove hyphenation character(s) from end of current line
                    for char in word_break_chars:
                        if current_line.endswith(char):
                            current_line = current_line[:-len(char)]
                            break
                    
                    # Join with next line (no space for hyphenated words)
                    next_line = current_lines[i + 1]
                    merged_line = current_line + next_line
                    processed_lines.append(merged_line)
                    i += 2  # Skip next line since we merged it
                    changes_made = True
                else:
                    processed_lines.append(current_line)
                    i += 1
            
            current_lines = processed_lines
            iteration += 1
            
            # If no changes were made, we're done
            if not changes_made:
                break
        
        return current_lines
    
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
    parser.add_argument('--merge-lines', '-m', action='store_true',
                       help='Merge lines within paragraphs and handle hyphenation')
    
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
        converter = AltoToMarkdownConverter(args.config, merge_lines=args.merge_lines)
        converter.process_all_alto_files(input_folder, output_folder, args.suffix)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())