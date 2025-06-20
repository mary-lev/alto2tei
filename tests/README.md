# Test Suite for ALTO-to-TEI Converter

This directory contains comprehensive tests for both page-level and book-level ALTO-to-TEI conversion functionality.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── test_alto2tei.py         # Page-level converter tests (34 tests)
├── test_alto2teibook.py     # Book-level converter tests (29 tests)
└── README.md               # This file
```

## Test Categories

### Page-Level Tests (`test_alto2tei.py`)

- **Configuration Tests**: YAML loading, validation, error handling
- **Rule Engine Tests**: Line type mapping, block processing decisions
- **Tag Parsing Tests**: ALTO tag resolution and type detection
- **Line Processing Tests**: Container management, paragraph creation
- **Text Block Conversion**: Mixed content, paragraphs, verse handling
- **Multiple Paragraphs**: Explicit markers, indentation detection
- **Running Title Handling**: Special block type processing
- **Facsimile Output**: Basic TEI structure without coordinates
- **Integration Tests**: Real ALTO file conversion
- **Error Handling**: Empty blocks, missing elements, unknown types
- **Regression Tests**: Bug fixes for element handling

### Book-Level Tests (`test_alto2teibook.py`)

- **METS Parser Tests**: XML parsing, page ordering, metadata extraction
- **Converter Initialization**: Configuration, options, setup
- **Book Conversion Integration**: Complete workflow testing
- **Line Merging**: Cross-page paragraph processing
- **Edge Cases**: Missing files, malformed XML, permissions
- **CLI Argument Parsing**: Command-line interface validation
- **Book Configuration**: Header creation, metadata handling

## Running Tests

### All Tests
```bash
# Using the custom test runner
python3 run_tests.py

# Using pytest (if installed)
pytest tests/

# Using unittest
python3 -m unittest discover tests/
```

### Specific Test Categories
```bash
# Unit tests only
python3 run_tests.py --unit

# Integration tests only
python3 run_tests.py --integration

# Quick tests (no integration)
python3 run_tests.py --quick

# Book-level tests only
python3 run_tests.py --book

# Specific test file
python3 -m unittest tests.test_alto2tei
python3 -m unittest tests.test_alto2teibook
```

### Individual Test Classes
```bash
# Test specific functionality
python3 -c "
import unittest
import sys
sys.path.insert(0, '.')
from tests.test_alto2tei import TestConfigurationLoader
suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigurationLoader)
unittest.TextTestRunner(verbosity=2).run(suite)
"
```

## Test Data Requirements

### Page-Level Tests
- **alto/** directory with sample ALTO XML files
- Files: `0aefed141cd6.xml`, `0e2a73f13785.xml`, `0d1b1aaf40cb.xml`
- `4b369dc6f692.xml` for running title tests

### Book-Level Tests
- **alto_loni/** directory with complete book data
- **METS.xml** file for page ordering
- ALTO files: `page_1.xml` through `page_25.xml`
- At least `page_5.xml`, `page_7.xml` with text content

## Test Coverage

### Current Status
- **Total Tests**: 63 (34 page-level + 29 book-level)
- **Success Rate**: 100% passing
- **Coverage Areas**:
  - ✅ Configuration loading and validation
  - ✅ ALTO XML parsing and processing
  - ✅ TEI XML generation
  - ✅ Cross-page paragraph merging
  - ✅ Hyphenation handling
  - ✅ METS.xml integration
  - ✅ Error handling and edge cases
  - ✅ CLI argument parsing

### Key Test Scenarios
- **Configuration**: Valid/invalid YAML, missing files
- **ALTO Processing**: Real files, malformed XML, empty content
- **TEI Generation**: Proper structure, namespaces, elements
- **Cross-Page Merging**: Hyphenated words, paragraph boundaries
- **Error Handling**: Missing files, permissions, malformed data
- **Integration**: End-to-end conversion workflows

## Adding New Tests

### Test File Structure
```python
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from your_module import YourClass

class TestYourFunctionality(unittest.TestCase):
    def setUp(self):
        # Test setup
        pass
    
    def test_specific_feature(self):
        # Test implementation
        pass
```

### Best Practices
- Use descriptive test names
- Include docstrings explaining test purpose
- Mock external dependencies where appropriate
- Test both success and failure scenarios
- Use `skipTest()` for missing test data
- Clean up temporary files in `tearDown()`

## Continuous Integration

The test suite is designed to:
- Run in any environment with Python 3.7+
- Handle missing test data gracefully with skips
- Provide clear error messages
- Complete quickly (< 1 minute total runtime)
- Work with both unittest and pytest runners

## Troubleshooting

### Common Issues
1. **Import Errors**: Ensure parent directory is in Python path
2. **Missing Test Data**: Tests will skip if required files not found
3. **Permission Errors**: Some tests intentionally test permission scenarios
4. **XML Parsing Errors**: Expected for malformed XML tests

### Debug Individual Tests
```bash
# Run with verbose output
python3 run_tests.py --verbose

# Debug specific test
python3 -m unittest tests.test_alto2tei.TestConfigurationLoader.test_config_loading_success -v
```