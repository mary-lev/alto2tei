# Extending ALTO Block and Line Types

This guide explains how to add support for new ALTO block types and line types in the alto2tei converter.

## Overview

The converter uses a flexible YAML-based configuration system that allows you to add new ALTO types without modifying the Python code. All configuration is done in `config/alto_tei_mapping.yaml`.

## Adding New Block Types

### Pattern 1: Content Processing Blocks

Use this pattern when you want to process the text lines inside the block and convert them to paragraphs, poetry, etc.

```yaml
block_types:
  YourNewBlockType:
    description: "Description of what this block contains"
    process_lines: true      # Process lines inside this block
    skip_content: false      # Don't skip the content
```

**Examples:**
- Text columns in newspapers
- Chapter content
- Article bodies

### Pattern 2: Single Element Blocks

Use this pattern when the entire block should become one TEI element.

```yaml
block_types:
  YourBlockType:
    description: "Block that becomes a single TEI element"
    process_lines: true      # Usually true to get text content
    skip_content: false      # Don't skip content
    tei_element: "div"       # TEI element to create
    attributes:
      type: "advertisement"  # Attributes for the element
      place: "bottom"
```

**Examples:**
- Advertisements → `<div type="advertisement">`
- Captions → `<figDesc>`
- Sidebars → `<div type="sidebar">`

### Pattern 3: Extraction Blocks

Use this pattern when you need to extract information for special processing.

```yaml
block_types:
  YourBlockType:
    description: "Block with extractable information"
    process_lines: false     # Don't process lines normally
    skip_content: true       # Skip from regular content flow
    extract_page_number: true   # Built-in extraction (or create custom)
```

**Examples:**
- Page numbers → uses `extract_page_number: true`
- Footnotes → uses `extract_footnote: true`
- Custom extractions → you can add new extraction methods

### Pattern 4: Skip Blocks

Use this pattern to ignore content entirely.

```yaml
block_types:
  YourBlockType:
    description: "Content to ignore"
    process_lines: false
    skip_content: true
```

**Examples:**
- Decorative borders
- Printer marks
- Image regions without text

## Adding New Line Types

Line types control how individual text lines within blocks are processed.

### Basic Line Actions

```yaml
line_types:
  YourLineType:
    description: "Description of line type"
    action: "action_name"           # What to do with this line
    tei_element: "element_name"     # TEI element to create
    attributes:
      key: "value"                  # Attributes for the element
```

### Available Actions

1. **`add_to_paragraph`** - Add text to current paragraph
```yaml
DefaultLine:
  action: "add_to_paragraph"
  fallback_element: "p"
```

2. **`start_paragraph`** - Start a new paragraph
```yaml
"CustomLine:paragraph_start":
  action: "start_paragraph"
  tei_element: "p"
  closes:
    - "poetry"  # Close other containers first
```

3. **`create_element`** - Create standalone or contained element
```yaml
"CustomLine:verse":
  action: "create_element"
  tei_element: "l"
  container: "lg"
  container_attributes:
    type: "verse"
  closes:
    - "paragraph"
```

### Container Patterns

Lines can be grouped into containers:

```yaml
"CustomLine:table_cell":
  tei_element: "cell"
  container: "row"
  container_attributes:
    role: "data"
```

### Closing Containers

Lines can automatically close other containers:

```yaml
HeadingLine:
  tei_element: "head"
  closes:
    - "paragraph"  # Close any open paragraph
    - "poetry"     # Close any open poetry group
  standalone: true # Don't put in a container
```

## Real-World Examples

### Example 1: Adding Table Support

```yaml
# Block type for tables
block_types:
  TableZone:
    description: "Table blocks"
    process_lines: true
    skip_content: false

# Line types for table content
line_types:
  "CustomLine:table_header":
    description: "Table header row"
    tei_element: "cell"
    attributes:
      role: "columnheader"
    container: "row"
    container_attributes:
      role: "header"
    closes:
      - "paragraph"
      - "poetry"
  
  "CustomLine:table_data":
    description: "Table data cell"
    tei_element: "cell"
    attributes:
      role: "data"
    container: "row"
    container_attributes:
      role: "data"
```

### Example 2: Adding Advertisement Support

```yaml
block_types:
  AdvertisementZone:
    description: "Advertisement blocks"
    process_lines: true
    skip_content: false
    tei_element: "div"
    attributes:
      type: "advertisement"
      place: "margin"

line_types:
  "CustomLine:ad_title":
    description: "Advertisement title"
    tei_element: "head"
    attributes:
      type: "advertisement"
    closes:
      - "paragraph"
```

### Example 3: Adding Chapter/Section Support

```yaml
block_types:
  ChapterZone:
    description: "Chapter blocks"
    process_lines: true
    skip_content: false

line_types:
  "CustomLine:chapter_title":
    description: "Chapter title"
    tei_element: "head"
    attributes:
      type: "chapter"
    closes:
      - "paragraph"
      - "poetry"
    standalone: true
  
  "CustomLine:section_title":
    description: "Section title"
    tei_element: "head"
    attributes:
      type: "section"
    closes:
      - "paragraph"
      - "poetry"
    standalone: true
```

## Testing New Types

1. **Add your configuration** to `config/alto_tei_mapping.yaml`
2. **Test with a small ALTO file** that contains your new type
3. **Check the TEI output** to ensure it's structured correctly
4. **Validate against TEI schema** if needed

## Configuration Validation

The system will warn you if:
- Unknown actions are used
- Required fields are missing
- Invalid combinations are specified

## Tips for Success

1. **Start simple** - Add basic support first, then enhance
2. **Check existing patterns** - Look at similar types for guidance
3. **Test incrementally** - Test each new type separately
4. **Document your additions** - Add clear descriptions
5. **Consider TEI compliance** - Ensure output follows TEI guidelines

## Getting Help

If you need to add a type that doesn't fit these patterns:
1. Check if you can use a combination of existing patterns
2. Look at the source code for inspiration
3. Consider whether you need a new action type
4. Create an issue if you need new framework features

The framework is designed to handle 95% of ALTO content types through configuration alone!
