# ALTO-to-TEI Converter

A Python tool for converting eScriptorium ALTO XML files to TEI (Text Encoding Initiative) format, with support for the **Segmonto ontology** for document structure classification.

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

## 🔧 Configuration

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

## 🔧 Extension and Validation Tools

### Configuration Testing

```bash
# Test your configuration file for errors
python test_config.py

# Test custom configuration
python test_config.py my_custom_config.yaml

# Example output:
✅ Configuration file loaded successfully
✅ Rule engine initialized successfully

📊 Configuration Summary:
   Block types: 6
   Line types: 6
   Footnote patterns: 10

📋 Block types:
   MainZone: process_lines
   NumberingZone: skip_content, extract_page_number
   GraphicZone: skip_content
   ...

✅ Configuration is valid!
🎉 Ready to convert ALTO files!
```

### Adding New ALTO Types

See `EXTENDING_TYPES.md` for comprehensive guidance on:
- Adding new block types (content, extraction, single element, skip patterns)
- Adding new line types with custom actions
- Real-world examples for newspapers, books, tables
- Configuration patterns and best practices

Example configurations available in `examples/new_types_examples.yaml`

## Usage

### Basic Conversion

```bash
# Convert all ALTO files in 'alto' folder to 'tei' folder
python alto2tei.py

# Specify input and output folders
python alto2tei.py manuscripts output_tei

# Use custom configuration
python alto2tei.py --config custom_mapping.yaml
```

### Command Line Options

```bash
python alto2tei.py [input_folder] [output_folder] [options]

Options:
  --input, -i      Input folder containing ALTO XML files
  --output, -o     Output folder for TEI XML files  
  --suffix, -s     Output filename suffix (default: _tei)
  --config, -c     Path to YAML configuration file
  --help, -h       Show help message
```

### Configuration Validation

```bash
# Test configuration before processing
python test_config.py config/alto_tei_mapping.yaml

# Test custom configuration
python test_config.py examples/newspaper_config.yaml
```

### Examples

```bash
# Basic usage
python alto2tei.py manuscripts tei_output

# Custom suffix and config
python alto2tei.py -i alto -o tei -s _converted -c segmonto_config.yaml

# Using flags
python alto2tei.py --input manuscripts --output tei_files
```

## Output Features

### TEI Structure

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

## References

- **Segmonto Ontology**: [https://segmonto.github.io/](https://segmonto.github.io/)
- **TEI Guidelines**: [https://tei-c.org/guidelines/](https://tei-c.org/guidelines/)
- **ALTO Standard**: [https://www.loc.gov/standards/alto/](https://www.loc.gov/standards/alto/)
- **eScriptorium**: [https://escriptorium.readthedocs.io](https://escriptorium.readthedocs.io/en/latest/)


## License

This project is licensed under the [MIT License](LICENSE).
