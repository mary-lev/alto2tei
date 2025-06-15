# Testing Guide for ALTO to TEI Converter

This document describes how to run and understand the tests for the YAML-driven ALTO to TEI converter.

## Quick Start

```bash
# Run all tests
python3 test_alto2tei.py

# Or use the test runner
python3 run_tests.py
```

## Test Categories

### Unit Tests
Test individual methods and functions in isolation:

```bash
python3 run_tests.py --unit
```

**Covers:**
- Configuration loading and validation
- Rule engine processing logic  
- Tag parsing and resolution
- Line processing with YAML rules
- TextBlock conversion logic

### Integration Tests
Test complete workflows with real ALTO files:

```bash
python3 run_tests.py --integration
```

**Covers:**
- Full file conversion (ALTO → TEI)
- Real-world data processing
- Output validation

### Quick Tests
Run all tests except integration (faster):

```bash
python3 run_tests.py --quick
```

### Error Handling Tests
Verify robust error handling:
- Empty/malformed input files
- Missing configuration
- Invalid YAML syntax
- Unknown line/block types

### Regression Tests
Ensure specific bug fixes continue to work:
- ET.Element boolean evaluation bug fix
- Container closing logic fix
- Verse line appending fix

## Test Structure

```
test_alto2tei.py
├── TestConfigurationLoader    # YAML config loading
├── TestRuleEngine            # Rule processing logic
├── TestTagParsing           # Unified tag resolution
├── TestLineProcessing       # YAML-driven line processing
├── TestTextBlockConversion  # Complete textblock conversion
├── TestMultipleParagraphs   # Multiple paragraph detection
├── TestRunningTitleHandling # RunningTitleZone exclusion
├── TestRealWorldMultipleParagraphs # Real file paragraph tests
├── TestIntegration         # Real file processing
├── TestErrorHandling       # Edge cases and errors
└── TestRegressionFixes     # Specific bug fixes
```

## What the Tests Verify

### ✅ Core Functionality
- **Tag Resolution**: ALTO tags → line/block types
- **YAML Configuration**: Proper loading and rule processing
- **Content Processing**: Paragraphs, verses, headers, speakers
- **Container Management**: Proper opening/closing of `<lg>`, `<p>` elements
- **Element Creation**: Correct TEI structure generation
- **Content Exclusion**: RunningTitleZone and other layout elements properly excluded

### ✅ YAML-Driven Behavior
- **Configurable Processing**: All behavior driven by YAML config
- **Rule-Based Logic**: No hardcoded conversion rules
- **Extensible Design**: New line types only require YAML changes

### ✅ Regression Prevention
- **Boolean Bug Fix**: ET.Element falsy value handling
- **Container Logic**: Proper verse/paragraph container management
- **Content Preservation**: No lost text during conversion

### ✅ Real-World Compatibility
- **Poetry Documents**: Complex verse structures (0aefed141cd6.xml)
- **Prose Documents**: Multi-line paragraphs (0e2a73f13785.xml)
- **Mixed Content**: Headers, speakers, verses, paragraphs

## Expected Test Results

**All tests should pass:**
```
Ran 25 tests in ~0.2s
OK
```

**Key test files:**
- `0aefed141cd6.xml` → 22 verse lines, 4 verse blocks, 5 speakers
- `0e2a73f13785.xml` → 1 substantial paragraph with Russian text

## Debugging Failed Tests

If tests fail:

1. **Check configuration**: Ensure `config/alto_tei_mapping.yaml` exists
2. **Verify ALTO files**: Test files should be in `alto/` directory  
3. **Review error messages**: Tests provide detailed failure information
4. **Run specific categories**: Use `--unit` or `--integration` to isolate issues

## Adding New Tests

When adding features:

1. **Add unit tests** for new methods
2. **Update integration tests** for new file types
3. **Add regression tests** for bug fixes
4. **Update YAML config tests** for new configuration options

## Performance Notes

- **Unit tests**: ~0.1s (fast feedback)
- **Integration tests**: ~0.1s (real file processing)
- **All tests**: ~0.2s (complete validation)

Tests are designed to be fast and can be run frequently during development.