#!/usr/bin/env python3
"""
Test and validate ALTO-TEI configuration files
"""

import argparse
import sys
from pathlib import Path
from alto2tei import ConfigurationLoader, RuleEngine

def test_configuration(config_path: str) -> bool:
    """Test a configuration file for errors"""
    try:
        print(f"Testing configuration: {config_path}")
        
        # Load configuration
        config_loader = ConfigurationLoader(config_path)
        print("✅ Configuration file loaded successfully")
        
        # Initialize rule engine (this will validate)
        rule_engine = RuleEngine(config_loader)
        print("✅ Rule engine initialized successfully")
        
        # Report configuration stats
        block_count = len(rule_engine.block_types)
        line_count = len(rule_engine.line_types)
        footnote_patterns = len(rule_engine.footnote_patterns)
        
        print(f"\n📊 Configuration Summary:")
        print(f"   Block types: {block_count}")
        print(f"   Line types: {line_count}")
        print(f"   Footnote patterns: {footnote_patterns}")
        
        # Show some examples
        if block_count > 0:
            print(f"\n📋 Block types:")
            for i, (name, config) in enumerate(rule_engine.block_types.items()):
                if i >= 5:  # Show first 5
                    print(f"   ... and {block_count - 5} more")
                    break
                action = []
                if config.get('process_lines'): action.append('process_lines')
                if config.get('skip_content'): action.append('skip_content')
                if 'tei_element' in config: action.append(f"→{config['tei_element']}")
                print(f"   {name}: {', '.join(action) if action else 'default'}")
        
        if line_count > 0:
            print(f"\n📝 Line types:")
            for i, (name, config) in enumerate(rule_engine.line_types.items()):
                if i >= 5:  # Show first 5
                    print(f"   ... and {line_count - 5} more")
                    break
                action = config.get('action', 'create_element')
                element = config.get('tei_element', 'p')
                print(f"   {name}: {action} → {element}")
        
        print(f"\n✅ Configuration is valid!")
        return True
        
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Test and validate ALTO-TEI configuration files"
    )
    
    parser.add_argument(
        "config_path",
        nargs="?",
        default="config/alto_tei_mapping.yaml",
        help="Path to YAML configuration file (default: config/alto_tei_mapping.yaml)"
    )
    
    args = parser.parse_args()
    
    # Test the configuration
    success = test_configuration(args.config_path)
    
    if not success:
        sys.exit(1)
    
    print("\n🎉 Ready to convert ALTO files!")

if __name__ == "__main__":
    main()