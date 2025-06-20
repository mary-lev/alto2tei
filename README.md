# ALTO-to-TEI Converter

A comprehensive Python toolkit for converting eScriptorium ALTO XML files to TEI (Text Encoding Initiative) format, with support for the **Segmonto ontology** for document structure classification.

## Two Conversion Modes

**📄 Page-Level Converter (`alto2tei.py`)**
- Converts individual ALTO files to corresponding TEI files
- Preserves original document structure and line breaks
- Ideal for analyzing individual pages or small collections

**📚 Book-Level Converter (`alto2teibook.py`)**
- Converts entire books using METS.xml for page ordering
- Advanced cross-page paragraph merging with hyphenation handling
- Generates single TEI document with optional facsimile zones
- Perfect for creating machine-readable complete texts

## Core Principles

### 1. **Segmonto Ontology Compliance**
This converter is designed to work with document zones and line types following the [Segmonto ontology](https://segmonto.github.io/), a controlled vocabulary for the semantic annotation of historical document layouts.

**Key Segmonto Features:**
- **Zone Classification**: Uses standardized zone types (e.g., `MainZone`, `MarginZone:note`, `GraphicZone`)
- **Hierarchical Names**: Supports colon-separated names for precise classification (e.g., `MarginZone:note`)
- **Semantic Consistency**: Maintains semantic relationships between document regions across different manuscripts

### 2. **YAML-Driven Configuration**
All transformation rules are externalized in YAML configuration files, enabling:
- **Maintainability**: Easy updates without code changes
- **Flexibility**: Support for different document types and ontologies
- **Transparency**: Clear, readable transformation rules
- **Extensibility**: Simple addition of new zone and line types

### 3. **TEI Best Practices**
Generates TEI XML following established standards:
- **Semantic Markup**: Meaningful element names reflecting content structure
- **Metadata Preservation**: Maintains page numbers, image references, and document structure
- **Poetry Handling**: Proper grouping of verse lines with `<lg>` and `<l>` elements
- **Footnote Management**: Structured footnote handling with automatic symbol recognition
- **Simplified Paragraphs**: Uses only paragraph start markers with automatic closure for cleaner annotation

## Architecture

### Document Processing Pipeline

```
ALTO XML → Parse Tags → Classify Zones → Process Lines → Generate TEI
    ↓           ↓           ↓             ↓            ↓
 eScriptorium  Segmonto   YAML Rules   Line Types   TEI XML
```

### Zone Classification (Segmonto-Based)

The system recognizes these primary zone types:

| Zone Type | Segmonto Category | Processing | TEI Output |
|-----------|------------------|------------|------------|
| `MainZone` | Primary text content | Process all lines | `<p>`, `<lg>`, `<head>` |
| `MarginTextZone:note` | Footnote annotations | Extract as footnotes | `<note type="footnote">` |
| `MarginTextZone:outer` | Outer margin content | Process lines | `<p>` or specialized elements |
| `NumberingZone` | Page numbering | Extract page numbers | `<pb n="..." facs="...">` |
| `RunningTitleZone` | Running headers/titles | Process lines | `<p>` with context |
| `QuireMarksZone` | Quire markings | Process lines | `<p>` with context |

### Line Type Processing

Within processed zones, lines are classified according to their semantic function:

| Line Type | Purpose | TEI Element | Container |
|-----------|---------|-------------|-----------|
| `HeadingLine` | Section headings | `<head>` | Standalone |
| `CustomLine:paragraph_start` | Begin paragraph | `<p>` | Auto-closed on next paragraph |
| `CustomLine:verse` | Poetry lines | `<l>` | `<lg type="verse">` |
| `CustomLine:speaker` | Speaker names | `<speaker>` | Standalone |
| `CustomLine:catchword` | Page catchwords | `<fw type="catchword">` | Standalone |
| `CustomLine:signature` | Technical marks/signatures | `<fw type="signature">` | Standalone |
| `DefaultLine` | Regular text | Add to `<p>` | Current paragraph |

## Configuration

### YAML Structure

```yaml
block_types:
  MainZone:
    description: "Main text content blocks"
    process_lines: true
    skip_content: false
  
  "MarginTextZone:note":  # Quoted for colon support
    description: "Footnote blocks"
    process_lines: false
    extract_footnote: true
    tei_element: "note"
    attributes:
      type: "footnote"
  
  "MarginTextZone:outer":  # Segmonto hierarchical naming
    description: "Margin text content blocks"
    process_lines: true
    skip_content: false

line_types:
  "CustomLine:paragraph_start":  # Segmonto-style naming
    description: "Beginning of paragraph - starts a new paragraph, auto-closes previous"
    action: "start_paragraph"
    tei_element: "p"
    closes:
      - "poetry"
  
  "CustomLine:verse":  # Poetry line
    description: "Poetry lines"
    tei_element: "l"
    container: "lg"
    container_attributes:
      type: "verse"
    closes:
      - "paragraph"
  
  DefaultLine:
    description: "Default line type"
    action: "add_to_paragraph"
    fallback_element: "p"

element_creation:
  page_number:
    element: "pb"
    attributes:
      n: "page_number"
      facs: "source_image"
  
  form_work:
    element: "fw"
    attributes:
      type: "placeholder"
    type_mappings:
      "CustomLine:catchword": "catchword"
      "CustomLine:signature": "signature"
      "default": "other"
```

### Segmonto Ontology Integration

The configuration supports Segmonto's hierarchical naming:

```yaml
# Standard zone types
"MainZone": {...}
"GraphicZone": {...}
"NumberingZone": {...}

# Hierarchical Segmonto types (quoted for colon support)
"MarginTextZone:note": {...}      # Footnote annotations
"MarginTextZone:outer": {...}     # Outer margin content
"CustomLine:paragraph_start": {...}
"CustomLine:catchword": {...}
"CustomLine:signature": {...}
"CustomLine:verse": {...}        # Note: space after colon supported
```

### Current Type Usage Statistics

Based on analysis of your ALTO files:

**Block Types (6 actively used):**
- `MainZone`: 100 files (102 instances) - Primary content
- `NumberingZone`: 89 files (91 instances) - Page numbers  
- `GraphicZone`: 32 files (35 instances) - Graphics/decorations
- `MarginTextZone:outer`: 6 files (8 instances) - Margin content
- `RunningTitleZone`: 5 files (5 instances) - Running headers
- `MarginTextZone:note`: 4 files (4 instances) - Footnotes

**Line Types (6 actively used):**
- `DefaultLine`: 100 files (2,775 instances) - Regular text
- `CustomLine:catchword`: 75 files (75 instances) - Page catchwords
- `CustomLine: verse`: 2 files (50 instances) - Poetry lines
- `CustomLine:paragraph_start`: 7 files (30 instances) - Paragraph starts
- `HeadingLine`: 3 files (13 instances) - Section headers
- `CustomLine:signature`: 7 files (7 instances) - Signatures


### Adding New ALTO Types

See `EXTENDING_TYPES.md` for comprehensive guidance on:
- Adding new block types (content, extraction, single element, skip patterns)
- Adding new line types with custom actions
- Real-world examples for newspapers, books, tables
- Configuration patterns and best practices

Example configurations available in `examples/new_types_examples.yaml`

## Usage

### Basic Page-Level Conversion

```bash
# Convert all ALTO files in 'alto' folder to 'tei' folder
python alto2tei.py

# Specify input and output folders
python alto2tei.py manuscripts output_tei

# Use custom configuration
python alto2tei.py --config custom_mapping.yaml
```

### Book-Level Conversion (NEW)

Convert entire books from multiple ALTO pages to a single TEI document with advanced cross-page processing:

```bash
# Convert entire book using METS.xml for page ordering
python alto2teibook.py alto_book/

# Specify output file
python alto2teibook.py alto_book/ --output book.xml

# Enable cross-page paragraph merging with facsimile zones
python alto2teibook.py alto_book/ --merge-lines True --facsimile True

# Process without facsimile for pure text output
python alto2teibook.py alto_book/ --merge-lines True --facsimile False
```

### Command Line Options

#### Page-Level Converter (`alto2tei.py`)
```bash
python alto2tei.py [input_folder] [output_folder] [options]

Options:
  --input, -i      Input folder containing ALTO XML files
  --output, -o     Output folder for TEI XML files  
  --suffix, -s     Output filename suffix (default: _tei)
  --config, -c     Path to YAML configuration file
  --help, -h       Show help message
```

#### Book-Level Converter (`alto2teibook.py`)
```bash
python alto2teibook.py [input_path] [options]

Arguments:
  input_path               Input directory with ALTO files and METS.xml, or path to METS.xml

Options:
  --mets, -m METS         Path to METS.xml file (alternative to auto-detection)
  --output, -o OUTPUT     Output TEI XML file (default: output/book.xml)
  --merge-lines {True,False}
                          Merge lines into paragraphs and handle hyphenation (default: True)
  --facsimile {True,False}
                          Include facsimile zones with spatial coordinates (default: True)
  --help, -h              Show help message
```

### Testing

```bash
# Run all tests
python3 run_tests.py

# Run specific test categories  
python3 run_tests.py --unit           # Unit tests only
python3 run_tests.py --integration    # Integration tests only
python3 run_tests.py --quick          # Quick tests (no integration)
python3 run_tests.py --book           # Book-level tests only

# Using pytest (if installed)
pytest tests/
```

### Examples

#### Page-Level Processing
```bash
# Basic usage
python alto2tei.py manuscripts tei_output

# Custom suffix and config
python alto2tei.py -i alto -o tei -s _converted -c segmonto_config.yaml

# Using flags
python alto2tei.py --input manuscripts --output tei_files
```

#### Book-Level Processing
```bash
# Convert complete book with cross-page paragraph merging
python alto2teibook.py alto_book/ --output complete_book.xml

# Text-only output for machine processing
python alto2teibook.py alto_book/ --merge-lines True --facsimile False --output clean_text.xml

# Full facsimile output with coordinates
python alto2teibook.py alto_book/ --merge-lines True --facsimile True --output annotated_book.xml

# Use specific METS file
python alto2teibook.py --mets /path/to/METS.xml --output book.xml
```

## Advanced Book Processing Features

### Cross-Page Paragraph Merging

The book converter (`alto2teibook.py`) includes sophisticated text processing capabilities:

**Smart Paragraph Detection:**
- Uses `CustomLine:paragraph_start` markers to identify paragraph boundaries
- Automatically merges paragraphs that span multiple pages
- Handles paragraphs without explicit end markers
- Stops merging at headings (`HeadingLine`) or new paragraph starts

**Hyphenation Handling:**
- Detects hyphenated words split across page boundaries
- Removes hyphens (`-`, `—`, `–`) and joins word parts seamlessly
- Preserves proper spacing for non-hyphenated text
- Example: `wonder-` + `ful` → `wonderful`

**Smart Page Break Positioning:**
- Places `<pb>` elements at natural breaking points within text flow
- Maintains reading flow while preserving page structure
- Handles both hyphenated and non-hyphenated page breaks correctly

### METS.xml Integration

**Automatic Page Ordering:**
- Reads METS.xml to determine correct page sequence
- Supports both absolute and relative file paths
- Handles missing or malformed ALTO files gracefully
- Processes 25+ page books efficiently

**Metadata Extraction:**
- Extracts book-level metadata from METS.xml
- Generates appropriate TEI headers with page counts
- Includes source file information and processing details

### Facsimile Zone Support

**Coordinate Preservation:**
- Extracts spatial coordinates from ALTO files
- Maps text elements to image regions
- Generates TEI facsimile zones with polygons and baselines
- Links text content to corresponding image areas

**Flexible Output Modes:**
- `--facsimile True`: Include complete coordinate information
- `--facsimile False`: Generate clean text-only output
- Automatic zone detection and mapping

## Output Features

### Page-Level TEI Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Digital text from manuscript.jpeg</title>
      </titleStmt>
      <publicationStmt>
        <publisher>eScriptorium</publisher>
      </publicationStmt>
      <sourceDesc>
        <p>Transcribed from digital image using eScriptorium</p>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <pb n="1" facs="manuscript.jpeg"/>
      <head>Chapter Title</head>
      <lg type="verse">
        <l>First line of poetry</l>
        <l>Second line of poetry</l>
      </lg>
      <p>Regular paragraph text...</p>
      <fw type="catchword">catchword</fw>
      <div type="notes">
        <note type="footnote" n="*">Footnote content</note>
      </div>
    </body>
  </text>
</TEI>
```

### Book-Level TEI Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Book converted from ALTO (pages 1-25)</title>
      </titleStmt>
      <publicationStmt>
        <p>Converted from ALTO XML using alto2teibook.py - 25 pages</p>
      </publicationStmt>
      <sourceDesc>
        <p>Source: alto_book/METS.xml</p>
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <facsimile>
    <surface xml:id="facs_page_5" source="page_5.jpg">
      <graphic url="page_5.jpg" width="1500" height="2800" />
      <zone xml:id="facs_block_5_1" ulx="197" uly="310" lrx="1320" lry="2392" type="textblock" />
    </surface>
    <!-- Additional pages... -->
  </facsimile>
  <text>
    <body>
      <div type="book">
        <pb n="5" facs="page_5.jpeg" />
        <p>ПРИМѢРЪ Добродѣтельныя Женщины, Гонимая нещастїемъ ИЛИ МИССЪ ЛОНІИ.</p>
        <p>Сочиненїе АгЛИНСКОЕ. Переводъ съ французскаго языка. Съ Указнаго дозволенiя.</p>
        <p>МОСКВА. Въ Типографiи при Театрѣ у Христофора Клаудгя, 1793 года. <pb n="7" facs="page_7.jpeg" />
        </p>
        <p>ЕЯ ПРЕВОСХОДИТЕЛЬСТВУ милостивой государынѣ ПАЛАГЬЕ ИВАНОВНЪ ЧЕРТКОВОЙ. <pb n="9" facs="page_9.jpeg" />
        </p>
        <!-- Cross-page paragraphs merged seamlessly -->
        <p>Удостойте, Милостивая Государыня! благосклонно принять оной знакомъ моей къ Вамъ благо<pb n="10" facs="page_10.jpeg" />дарности и почтенiя, съ каковымъ навсегда останется</p>
        <!-- Hyphenated words joined: "благо-" + "дарности" → "благодарности" -->
      </div>
    </body>
  </text>
</TEI>
```

### Line-Level Facsimile

Automatic coordinate mapping preserves spatial relationships:

```xml
<facsimile>
  <surface>
    <graphic url="page1.jpg"/>
    <zone xml:id="tl1" ulx="10" uly="20" lrx="60" lry="30"/>
    <zone xml:id="tl2" ulx="15" uly="35" lrx="70" lry="45"/>
  </surface>
</facsimile>

<p facs="#tl1">Line one
      <lb facs="#tl2"/>
      Line two</p>
```

### Enhanced Formatting

Improved XML formatting makes files more readable:

```xml
<lg type="verse">
  <l>First line of poetry
      <lb/>
  </l>
  <l>Second line with better spacing
      <lb/>
  </l>
</lg>
```

## Segmonto Ontology Benefits

### 1. **Standardization**
- Consistent zone classification across different manuscripts
- Interoperability with other Segmonto-compliant tools
- Reproducible annotation practices

### 2. **Semantic Precision**
- Hierarchical classification enables fine-grained distinctions
- Clear separation between content types (text, graphics, annotations)
- Contextual meaning preservation

### 3. **Research Applications**
- Enables comparative analysis across manuscript traditions
- Supports digital humanities research methodologies
- Facilitates automated content analysis

### 4. **Future-Proofing**
- Alignment with emerging digital manuscript standards
- Compatibility with evolving TEI guidelines
- Support for advanced scholarly applications

## Technical Details

### Dependencies

```python
xml.etree.ElementTree  # XML parsing and generation
yaml                   # Configuration file parsing
pathlib               # Modern path handling
argparse              # Command-line interface
re                    # Regular expressions for footnote patterns
glob                  # File pattern matching
```

### Testing Framework

The project includes a comprehensive test suite with 63 tests covering:

```
tests/
├── test_alto2tei.py         # Page-level converter tests (34 tests)
├── test_alto2teibook.py     # Book-level converter tests (29 tests)
└── README.md               # Detailed testing documentation
```

**Test Coverage:**
- Configuration loading and validation
- ALTO XML parsing and TEI generation  
- Cross-page paragraph merging
- Hyphenation handling
- METS.xml integration
- Error handling and edge cases
- CLI functionality

## Quick Start

### For Individual Pages
```bash
# Convert all ALTO files in current directory
python alto2tei.py

# Convert specific folder
python alto2tei.py manuscripts/ tei_output/
```

### For Complete Books
```bash
# Convert entire book with cross-page merging
python alto2teibook.py alto_book/

# Text-only output for NLP processing
python alto2teibook.py alto_book/ --facsimile False --output clean_book.xml
```

## Key Features Summary

✅ **Segmonto Ontology Support** - Standard document zone classification  
✅ **YAML-Driven Configuration** - Easy customization without code changes  
✅ **Cross-Page Paragraph Merging** - Intelligent text flow reconstruction  
✅ **Hyphenation Handling** - Automatic word joining across page breaks  
✅ **METS.xml Integration** - Proper page ordering and metadata extraction  
✅ **Facsimile Zone Support** - Optional coordinate preservation  
✅ **TEI Best Practices** - Standards-compliant output  
✅ **Historical Text Support** - Handles 18th century Cyrillic and special characters

## References

- **Segmonto Ontology**: [https://segmonto.github.io/](https://segmonto.github.io/)
- **TEI Guidelines**: [https://tei-c.org/guidelines/](https://tei-c.org/guidelines/)
- **ALTO Standard**: [https://www.loc.gov/standards/alto/](https://www.loc.gov/standards/alto/)
- **eScriptorium**: [https://escriptorium.readthedocs.io](https://escriptorium.readthedocs.io/en/latest/)


## License

This project is licensed under the [MIT License](LICENSE).
