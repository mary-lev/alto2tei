#!/usr/bin/env python3
"""
Convert eScriptorium ALTO XML output to plain text format

This module provides the simplest conversion: just extract text content
line by line, maintaining document order but without any markup.
Perfect for text analysis, searching, or basic reading.
"""

import xml.etree.ElementTree as ET
import argparse
import re
from pathlib import Path
from typing import Dict, Optional, Any
from alto2tei import ConfigurationLoader as BaseConfigurationLoader, AltoToTeiConverter

class TextConfigurationLoader(BaseConfigurationLoader):
    """Loads and manages ALTO-Text transformation rules from YAML configuration"""
    
    def __init__(self, config_path: str = "config/alto_text_mapping.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def get_text_structure(self) -> Dict[str, Any]:
        """Get text structure configuration"""
        return self.config.get('text_structure', {})
    
    def get_page_handling(self) -> Dict[str, Any]:
        """Get page handling configuration"""
        return self.config.get('page_handling', {})
    
    def get_line_merging(self) -> Dict[str, Any]:
        """Get line merging configuration"""
        return self.config.get('line_merging', {})
    
    def get_hyphenation(self) -> Dict[str, Any]:
        """Get hyphenation configuration"""
        return self.config.get('hyphenation', {})

class TextRuleEngine:
    """Processes YAML-based rules for ALTO to text conversion"""
    
    def __init__(self, config_loader: TextConfigurationLoader):
        self.config = config_loader
        self.block_types = config_loader.get_block_types()
        self.line_types = config_loader.get_line_types()
        self.text_structure = config_loader.get_text_structure()
        self.page_handling = config_loader.get_page_handling()
        self.line_merging = config_loader.get_line_merging()
        self.hyphenation = config_loader.get_hyphenation()
    
    def should_process_block(self, block_type: str) -> bool:
        """Check if a block type should be processed for content"""
        block_config = self.block_types.get(block_type, {})
        return block_config.get('process_lines', False)
    
    
    def get_line_mapping(self, line_type: str) -> Dict[str, Any]:
        """Get text mapping configuration for a line type"""
        return self.line_types.get(line_type, self.line_types.get('DefaultLine', {}))
    
    def get_line_separator(self) -> str:
        """Get line separator for text"""
        return self.text_structure.get('line_separator', '\n')
    
    
    def should_clean_output(self) -> bool:
        """Check if output should be cleaned (remove empty lines, etc.)"""
        return self.page_handling.get('clean_output', True)
    
    def should_merge_lines(self) -> bool:
        """Check if line merging is enabled"""
        return self.line_merging.get('enabled', False)
    
    def should_merge_paragraph_lines(self) -> bool:
        """Check if paragraph lines should be merged"""
        return self.line_merging.get('merge_paragraph_lines', True)
    
    def should_merge_verse_lines(self) -> bool:
        """Check if verse lines should be merged"""
        return self.line_merging.get('merge_verse_lines', False)
    
    def get_paragraph_separator(self) -> str:
        """Get separator between merged paragraphs"""
        return self.line_merging.get('paragraph_separator', '\n\n')
    
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

class AltoToTextConverter:
    """Convert ALTO XML to plain text format using configuration-driven approach"""
    
    def __init__(self, config_path: str = "config/alto_text_mapping.yaml", merge_lines: bool = False):
        # Reuse ALTO parsing logic from TEI converter
        self.tei_converter = AltoToTeiConverter()
        self.alto_ns = self.tei_converter.alto_ns
        
        # Load text-specific configuration
        self.config_loader = TextConfigurationLoader(config_path)
        self.rule_engine = TextRuleEngine(self.config_loader)
        
        # Override line merging setting if specified
        self.merge_lines = merge_lines
    
    def convert_alto_to_text(self, alto_file: Path) -> str:
        """Convert an ALTO file to plain text"""
        
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
        all_lines = []
        
        # Process each page
        for page in alto_root.findall('.//alto:Page', self.alto_ns):
            page_lines = []
            
            # Process textblocks
            for textblock in page.findall('.//alto:TextBlock', self.alto_ns):
                block_type = self.tei_converter.get_block_type(textblock, tags_mapping)
                
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

                    # Get line type and text mapping
                    line_type = self.tei_converter.get_line_type(textline, tags_mapping)

                    # Special handling: if line is in NumberingZone, treat as PageNumberLine
                    if block_type == "NumberingZone":
                        line_type = "PageNumberLine"

                    line_config = self.rule_engine.get_line_mapping(line_type)

                    # Process line to text
                    text_line = self._process_line_to_text(text_content, line_config)

                    if text_line:  # Only add non-empty lines
                        page_lines.append(text_line)

            # Add page content if any
            if page_lines:
                all_lines.extend(page_lines)
        
        # Join all lines
        text_content = self.rule_engine.get_line_separator().join(all_lines)
        
        # Clean output if configured
        if self.rule_engine.should_clean_output():
            text_content = self._clean_text_output(text_content)
        
        return text_content
    
    def _convert_with_line_merging(self, alto_root, tags_mapping) -> str:
        """Convert with line merging enabled"""
        # Collect line groups with block separation
        all_block_groups = []
        
        # Process each page
        for page in alto_root.findall('.//alto:Page', self.alto_ns):
            # Process textblocks
            for textblock in page.findall('.//alto:TextBlock', self.alto_ns):
                block_type = self.tei_converter.get_block_type(textblock, tags_mapping)
                
                # Skip non-content blocks
                if not self.rule_engine.should_process_block(block_type):
                    continue
                
                # Collect lines within this specific textblock
                block_line_groups = []  # (paragraph_type, text_content)
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

                    # Get line type and text mapping
                    line_type = self.tei_converter.get_line_type(textline, tags_mapping)

                    # Special handling: if line is in NumberingZone, treat as PageNumberLine
                    if block_type == "NumberingZone":
                        line_type = "PageNumberLine"

                    line_config = self.rule_engine.get_line_mapping(line_type)

                    # Skip lines marked for skipping
                    if line_config.get('text_format') == 'skip':
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

                    # Process line to text
                    text_line = self._process_line_to_text(text_content, line_config)
                    
                    if text_line:  # Only add non-empty lines
                        block_line_groups.append((paragraph_type_with_block, text_line))

                # Process this block's lines and add to overall collection
                if block_line_groups:
                    block_merged_paragraphs = self._merge_line_groups(block_line_groups)
                    all_block_groups.extend(block_merged_paragraphs)

        # Join all blocks with appropriate separation
        return self.rule_engine.get_paragraph_separator().join(all_block_groups)

    def _process_line_to_text(self, text: str, config: Dict) -> Optional[str]:
        """Process a single line to text format"""
        
        text_format = config.get('text_format', 'line')
        template = config.get('template', '{text}')
        
        # Skip lines marked for skipping (like dividers)
        if text_format == 'skip':
            return None
        
        # For text output, we just extract the content
        return template.format(text=text)
    
    def _clean_text_output(self, text: str) -> str:
        """Clean text output by removing empty lines and excess whitespace"""
        
        # Split into lines
        lines = text.split('\n')
        
        # Remove empty lines and strip whitespace
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:  # Only keep non-empty lines
                cleaned_lines.append(line)
        
        # Join back with single newlines
        return '\n'.join(cleaned_lines)
    
    def _merge_line_groups(self, line_groups) -> list:
        """Group consecutive lines of same type and merge them"""
        if not line_groups:
            return []
        
        merged_paragraphs = []
        current_group = []
        current_type = None
        
        for paragraph_type, text_line in line_groups:
            # If type changes, finalize current group
            if current_type is not None and current_type != paragraph_type:
                if current_group:
                    merged_text = self._merge_lines_in_group(current_group, current_type)
                    if merged_text:
                        merged_paragraphs.append(merged_text)
                current_group = []
            
            current_type = paragraph_type
            current_group.append(text_line)
        
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
    
    def save_text(self, text_content: str, output_file: Path) -> None:
        """Save text content to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
    
    def process_all_alto_files(self, input_folder: str, output_folder: str) -> None:
        """Process all ALTO files in a folder and convert to text"""
        
        input_path = Path(input_folder)
        output_path = Path(output_folder)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all ALTO XML files
        alto_files = list(input_path.glob("*.xml"))
        
        if not alto_files:
            print(f"No XML files found in {input_folder}")
            return
        
        merge_status = "merged" if (self.merge_lines or self.rule_engine.should_merge_lines()) else "lines"
        print(f"Converting {len(alto_files)} ALTO files to plain text ({merge_status})...")
        
        total_words = 0
        
        for alto_file in alto_files:
            try:
                # Convert to text
                text_content = self.convert_alto_to_text(alto_file)
                
                # Count words for statistics
                word_count = len(text_content.split())
                total_words += word_count
                
                # Create output filename
                output_filename = alto_file.stem + "_" + merge_status + ".txt"
                output_file = output_path / output_filename
                
                # Save text
                self.save_text(text_content, output_file)
                
                print(f"✅ {alto_file.name} → {output_filename} ({word_count} words)")
                
            except Exception as e:
                print(f"❌ Error converting {alto_file.name}: {e}")
        
        print(f"Conversion complete! {total_words:,} total words extracted.")
        print(f"Text files saved to {output_folder}")

def main():
    """Command-line interface for ALTO to text conversion"""
    
    parser = argparse.ArgumentParser(
        description='Convert eScriptorium ALTO XML files to plain text format'
    )
    
    parser.add_argument('input_folder', nargs='?', default='alto',
                       help='Input folder containing ALTO XML files (default: alto)')
    parser.add_argument('output_folder', nargs='?', default='text',
                       help='Output folder for text files (default: text)')
    
    parser.add_argument('--input', '-i', dest='input_folder_flag',
                       help='Input folder (alternative to positional argument)')
    parser.add_argument('--output', '-o', dest='output_folder_flag',
                       help='Output folder (alternative to positional argument)')
    parser.add_argument('--suffix', '-s', default='_txt',
                       help='Suffix to add to output filenames (default: _txt)')
    parser.add_argument('--config', '-c', default='config/alto_text_mapping.yaml',
                       help='Path to YAML configuration file')
    parser.add_argument('--merge-lines', '-m', action='store_true',
                       help='Merge lines within paragraphs and handle hyphenation')
    
    args = parser.parse_args()
    
    # Use flag values if provided, otherwise use positional arguments
    input_folder = args.input_folder_flag or args.input_folder
    output_folder = args.output_folder_flag or args.output_folder
    
    print("📄 ALTO to Text Converter")
    print("=" * 40)
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Configuration: {args.config}")
    print("=" * 40)
    
    try:
        converter = AltoToTextConverter(args.config, merge_lines=args.merge_lines)
        converter.process_all_alto_files(input_folder, output_folder)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())