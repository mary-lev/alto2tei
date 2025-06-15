#!/usr/bin/env python3
"""
ALTO Types Analysis Service

Analyzes all ALTO XML files to extract and report on block types and line types usage.
Provides comprehensive statistics for Segmonto ontology compliance and configuration updates.
"""

import xml.etree.ElementTree as ET
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict
import argparse


class ALTOTypesAnalyzer:
    """Service for analyzing block and line types across ALTO files"""
    
    def __init__(self, folder: str):
        self.folder = Path(folder)
        self.alto_ns = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
        
        # Results storage
        self.block_types = Counter()  # Types defined in tags
        self.line_types = Counter()   # Types defined in tags
        self.block_usage = Counter()  # Types actually used in content
        self.line_usage = Counter()   # Types actually used in content
        self.file_block_types = defaultdict(set)
        self.file_line_types = defaultdict(set)
        self.segmonto_types = set()
        self.errors = []
        
    def analyze_all_files(self) -> Dict:
        """Analyze all ALTO files in the folder"""
        if not self.folder.exists():
            raise FileNotFoundError(f"Folder {self.folder} does not exist")
        
        xml_files = list(self.folder.glob("*.xml"))
        if not xml_files:
            raise FileNotFoundError(f"No XML files found in {self.folder}")
        
        print(f"🔍 Analyzing {len(xml_files)} ALTO files in {self.folder}...")
        
        for i, xml_file in enumerate(xml_files, 1):
            print(f"[{i}/{len(xml_files)}] Processing: {xml_file.name}", end="\r")
            try:
                self._analyze_file(xml_file)
            except Exception as e:
                self.errors.append(f"{xml_file.name}: {e}")
        
        print()  # New line after progress
        return self._compile_results()
    
    def _analyze_file(self, xml_file: Path) -> None:
        """Analyze a single ALTO file"""
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Find tags section and build mapping
        tags_section = root.find('.//alto:Tags', self.alto_ns)
        if tags_section is None:
            return
        
        # Build tag ID to label mapping
        tag_mapping = {}
        file_blocks = set()
        file_lines = set()
        
        # Extract all OtherTag elements and build mapping
        for tag in tags_section.findall('alto:OtherTag', self.alto_ns):
            tag_id = tag.get('ID')
            label = tag.get('LABEL')
            description = tag.get('DESCRIPTION', '')
            
            if not label or not tag_id:
                continue
            
            tag_mapping[tag_id] = label
                
            # Check for block types
            if 'block type' in description:
                self.block_types[label] += 1
                file_blocks.add(label)
                
                # Check if it's a Segmonto-style name
                if ':' in label:
                    self.segmonto_types.add(label)
            
            # Check for line types
            elif 'line type' in description:
                self.line_types[label] += 1
                file_lines.add(label)
                
                # Check if it's a Segmonto-style name
                if ':' in label:
                    self.segmonto_types.add(label)
        
        # Now check actual usage in content
        used_blocks = set()
        used_lines = set()
        
        # Find TextBlocks and check their TAGREFS
        for textblock in root.findall('.//alto:TextBlock', self.alto_ns):
            tagrefs = textblock.get('TAGREFS', '')
            for tagref in tagrefs.split():
                if tagref in tag_mapping:
                    block_type = tag_mapping[tagref]
                    used_blocks.add(block_type)
                    self.block_usage[block_type] += 1
        
        # Find TextLines and check their TAGREFS
        for textline in root.findall('.//alto:TextLine', self.alto_ns):
            tagrefs = textline.get('TAGREFS', '')
            for tagref in tagrefs.split():
                if tagref in tag_mapping:
                    line_type = tag_mapping[tagref]
                    used_lines.add(line_type)
                    self.line_usage[line_type] += 1
        
        # Store per-file results (only types that are actually used)
        if used_blocks:
            self.file_block_types[xml_file.name] = used_blocks
        if used_lines:
            self.file_line_types[xml_file.name] = used_lines
    
    def _compile_results(self) -> Dict:
        """Compile analysis results"""
        total_files = len(list(self.folder.glob("*.xml")))
        
        # Convert sets to lists for JSON serialization
        file_block_types_serializable = {k: list(v) for k, v in self.file_block_types.items()}
        file_line_types_serializable = {k: list(v) for k, v in self.file_line_types.items()}
        
        return {
            'summary': {
                'total_files': total_files,
                'files_with_blocks': len(self.file_block_types),
                'files_with_lines': len(self.file_line_types),
                'unique_block_types_defined': len(self.block_types),
                'unique_line_types_defined': len(self.line_types),
                'unique_block_types_used': len(self.block_usage),
                'unique_line_types_used': len(self.line_usage),
                'segmonto_types': len(self.segmonto_types),
                'errors': len(self.errors)
            },
            'block_types_defined': dict(self.block_types),
            'line_types_defined': dict(self.line_types),
            'block_types_used': dict(self.block_usage),
            'line_types_used': dict(self.line_usage),
            'segmonto_types': sorted(list(self.segmonto_types)),
            'file_coverage': {
                'blocks': file_block_types_serializable,
                'lines': file_line_types_serializable
            },
            'errors': self.errors
        }
    
    def print_report(self, results: Dict) -> None:
        """Print comprehensive analysis report"""
        summary = results['summary']
        
        print("=" * 80)
        print("📊 ALTO TYPES ANALYSIS REPORT")
        print("=" * 80)
        
        # Summary statistics
        print(f"\n📁 FILES ANALYZED:")
        print(f"   Total files: {summary['total_files']}")
        print(f"   Files with block types: {summary['files_with_blocks']}")
        print(f"   Files with line types: {summary['files_with_lines']}")
        print(f"   Block types defined: {summary['unique_block_types_defined']}")
        print(f"   Block types actually used: {summary['unique_block_types_used']}")
        print(f"   Line types defined: {summary['unique_line_types_defined']}")
        print(f"   Line types actually used: {summary['unique_line_types_used']}")
        if summary['errors']:
            print(f"   ⚠️  Files with errors: {summary['errors']}")
        
        # Block types analysis
        print(f"\n📦 BLOCK TYPES (Defined vs Used):")
        all_block_types = set(results['block_types_defined'].keys()) | set(results['block_types_used'].keys())
        for block_type in sorted(all_block_types):
            defined_count = results['block_types_defined'].get(block_type, 0)
            used_count = len([f for f, types in results['file_coverage']['blocks'].items() if block_type in types])
            usage_instances = results['block_types_used'].get(block_type, 0)
            
            segmonto_marker = " 🔗" if block_type in results['segmonto_types'] else ""
            print(f"   {block_type:<25} │ {defined_count:>3} def │ {used_count:>3} files │ {usage_instances:>4} uses{segmonto_marker}")
        
        # Line types analysis
        print(f"\n📝 LINE TYPES (Defined vs Used):")
        all_line_types = set(results['line_types_defined'].keys()) | set(results['line_types_used'].keys())
        for line_type in sorted(all_line_types):
            defined_count = results['line_types_defined'].get(line_type, 0)
            used_count = len([f for f, types in results['file_coverage']['lines'].items() if line_type in types])
            usage_instances = results['line_types_used'].get(line_type, 0)
            
            segmonto_marker = " 🔗" if line_type in results['segmonto_types'] else ""
            print(f"   {line_type:<25} │ {defined_count:>3} def │ {used_count:>3} files │ {usage_instances:>4} uses{segmonto_marker}")
        
        # Segmonto types
        if results['segmonto_types']:
            print(f"\n🔗 SEGMONTO ONTOLOGY TYPES ({summary['segmonto_types']} found):")
            for segmonto_type in results['segmonto_types']:
                if segmonto_type in results['block_types_defined']:
                    type_category = "Block"
                    defined_count = results['block_types_defined'][segmonto_type]
                    used_count = len([f for f, types in results['file_coverage']['blocks'].items() if segmonto_type in types])
                else:
                    type_category = "Line"
                    defined_count = results['line_types_defined'][segmonto_type]
                    used_count = len([f for f, types in results['file_coverage']['lines'].items() if segmonto_type in types])
                print(f"   {segmonto_type:<30} │ {type_category:<5} │ {defined_count:>3} def │ {used_count:>3} files")
        
        # Coverage analysis
        print(f"\n📈 COVERAGE ANALYSIS:")
        
        # Most common combinations
        block_combinations = Counter()
        line_combinations = Counter()
        
        for file_blocks in results['file_coverage']['blocks'].values():
            block_combinations[tuple(sorted(file_blocks))] += 1
        
        for file_lines in results['file_coverage']['lines'].values():
            line_combinations[tuple(sorted(file_lines))] += 1
        
        print(f"   Most common block type combinations:")
        for combo, count in block_combinations.most_common(5):
            combo_str = ", ".join(combo) if combo else "None"
            print(f"     {combo_str:<60} │ {count:>3} files")
        
        print(f"   Most common line type combinations:")
        for combo, count in line_combinations.most_common(5):
            combo_str = ", ".join(combo) if combo else "None"
            print(f"     {combo_str:<60} │ {count:>3} files")
        
        # Errors
        if results['errors']:
            print(f"\n❌ ERRORS ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"   {error}")
        
        print("\n" + "=" * 80)
        print("🔗 Segmonto types are marked with 🔗")
        print("📊 Report completed successfully")
        print("=" * 80)
    
    def export_json(self, results: Dict, output_file: str) -> None:
        """Export results to JSON file"""
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📄 Results exported to: {output_path}")
    
    def export_yaml_template(self, results: Dict, output_file: str) -> None:
        """Export YAML configuration template for new types"""
        output_path = Path(output_file)
        
        yaml_content = []
        yaml_content.append("# YAML Configuration Template")
        yaml_content.append("# Generated from ALTO types analysis")
        yaml_content.append("")
        yaml_content.append("block_types:")
        
        for block_type in sorted(results['block_types_defined'].keys()):
            yaml_content.append(f"  {self._quote_if_needed(block_type)}:")
            yaml_content.append(f"    description: \"{block_type} blocks\"")
            if block_type in ['NumberingZone']:
                yaml_content.append("    process_lines: false")
                yaml_content.append("    skip_content: true")
                yaml_content.append("    extract_page_number: true")
            elif block_type in ['GraphicZone', 'Illustration']:
                yaml_content.append("    process_lines: false")
                yaml_content.append("    skip_content: true")
            else:
                yaml_content.append("    process_lines: true")
                yaml_content.append("    skip_content: false")
            yaml_content.append("")
        
        yaml_content.append("line_types:")
        for line_type in sorted(results['line_types_defined'].keys()):
            yaml_content.append(f"  {self._quote_if_needed(line_type)}:")
            yaml_content.append(f"    description: \"{line_type} lines\"")
            if line_type == 'CustomLine:verse':
                yaml_content.append("    tei_element: \"l\"")
                yaml_content.append("    container: \"lg\"")
                yaml_content.append("    container_attributes:")
                yaml_content.append("      type: \"verse\"")
            elif line_type == 'Header':
                yaml_content.append("    tei_element: \"head\"")
                yaml_content.append("    standalone: true")
            elif line_type in ['Catchword', 'TechLine']:
                yaml_content.append("    tei_element: \"fw\"")
                yaml_content.append("    standalone: true")
            else:
                yaml_content.append("    tei_element: \"p\"")
            yaml_content.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(yaml_content))
        
        print(f"📝 YAML template exported to: {output_path}")
    
    def _quote_if_needed(self, type_name: str) -> str:
        """Quote type name if it contains special characters"""
        if ':' in type_name or ' ' in type_name:
            return f'"{type_name}"'
        return type_name


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(
        description="Analyze ALTO files to extract block and line types usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  analyze_types.py alto/                    # Basic analysis
  analyze_types.py alto/ --json results.json  # Export JSON
  analyze_types.py alto/ --yaml template.yaml # Export YAML template
  analyze_types.py alto/ --export-all       # Export both JSON and YAML
        """
    )
    
    parser.add_argument(
        'folder',
        help='Folder containing ALTO XML files'
    )
    parser.add_argument(
        '--json', '-j',
        help='Export results to JSON file'
    )
    parser.add_argument(
        '--yaml', '-y',
        help='Export YAML configuration template'
    )
    parser.add_argument(
        '--export-all', '-a',
        action='store_true',
        help='Export both JSON (types_analysis.json) and YAML (types_template.yaml)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress console output (only show errors)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = ALTOTypesAnalyzer(args.folder)
        
        # Run analysis
        results = analyzer.analyze_all_files()
        
        # Print report unless quiet
        if not args.quiet:
            analyzer.print_report(results)
        
        # Export files
        if args.json:
            analyzer.export_json(results, args.json)
        
        if args.yaml:
            analyzer.export_yaml_template(results, args.yaml)
        
        if args.export_all:
            analyzer.export_json(results, 'types_analysis.json')
            analyzer.export_yaml_template(results, 'types_template.yaml')
        
        if results['summary']['errors']:
            print(f"\n⚠️  Analysis completed with {results['summary']['errors']} errors")
            return 1
        else:
            print(f"\n✅ Analysis completed successfully")
            return 0
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
