#!/usr/bin/env python3
"""
Test runner script for alto2tei converter

Usage:
    python3 run_tests.py              # Run all tests
    python3 run_tests.py --unit       # Run unit tests only
    python3 run_tests.py --integration # Run integration tests only
    python3 run_tests.py --quick      # Run quick tests (no integration)
"""

import sys
import argparse
import unittest
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent / 'tests'))

from tests.test_alto2tei import run_tests
from tests.test_alto2teibook import run_book_tests
from tests.test_alto2tei import (
    TestConfigurationLoader, TestRuleEngine, TestTagParsing, 
    TestLineProcessing, TestTextBlockConversion, TestMultipleParagraphs,
    TestRealWorldMultipleParagraphs, TestIntegration,
    TestErrorHandling, TestRegressionFixes
)
from tests.test_alto2teibook import (
    TestMetsParser, TestAltoBookToTeiConverter, TestBookConversionIntegration,
    TestLineMergingFunctionality, TestEdgeCasesAndErrorHandling,
    TestCLIArgumentParsing, TestBookConfiguration
)


def run_test_category(test_classes, verbose=True):
    """Run specific test categories"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description="Test runner for alto2tei converter")
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--quick', action='store_true', help='Run quick tests (no integration)')
    parser.add_argument('--book', action='store_true', help='Run alto2teibook tests only')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.unit:
        print("🧪 Running Unit Tests...")
        test_classes = [
            TestConfigurationLoader, TestRuleEngine, TestTagParsing,
            TestLineProcessing, TestTextBlockConversion, TestMultipleParagraphs,
            TestMetsParser, TestAltoBookToTeiConverter
        ]
        success = run_test_category(test_classes, args.verbose)
        
    elif args.integration:
        print("🔗 Running Integration Tests...")
        test_classes = [
            TestIntegration, TestRealWorldMultipleParagraphs,
            TestBookConversionIntegration, TestLineMergingFunctionality
        ]
        success = run_test_category(test_classes, args.verbose)
        
    elif args.quick:
        print("⚡ Running Quick Tests (no integration)...")
        test_classes = [
            TestConfigurationLoader, TestRuleEngine, TestTagParsing,
            TestLineProcessing, TestTextBlockConversion, TestMultipleParagraphs,
            TestErrorHandling, TestRegressionFixes,
            TestMetsParser, TestAltoBookToTeiConverter, TestCLIArgumentParsing
        ]
        success = run_test_category(test_classes, args.verbose)
        
    elif args.book:
        print("📚 Running Alto2TeiBook Tests...")
        success = run_book_tests()
        
    else:
        print("🚀 Running All Tests...")
        # Run both test suites
        print("\n📄 Running alto2tei tests...")
        success1 = run_tests()
        print("\n📚 Running alto2teibook tests...")
        success2 = run_book_tests()
        success = success1 and success2
    
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
