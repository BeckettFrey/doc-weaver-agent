"""Parse structured markdown documents into Document objects.

This module provides functionality to load and validate markdown documents
that follow a specific structure: title, tagline, sections, subsections,
and bullet content. The parser enforces strict formatting rules and validates
that exactly one `<TODO>` placeholder exists on its own line in the rendered
document preview.

The expected markdown structure is:

```
# Title
> Tagline

## Section
### Subsection
- Content item
- Content item

### Another Subsection
- <TODO>
```

See Also:
    `doc_weaver.document.Document`: The structured document model produced by parsing.
    `ValidationError`: Exception raised for malformed markdown.
"""
from doc_weaver.document import Document, Content

class ValidationError(Exception):
    """Raised when markdown doesn't conform to expected structure"""
    pass

def load_markdown(markdown: str) -> Document:
    """Parse a structured markdown string into a Document object.

    Parses markdown text with a strict hierarchical structure and validates
    that it contains exactly one `<TODO>` placeholder on its own line. The
    parser expects the following structure:

    1. Title line starting with `# `
    2. Tagline starting with `> `
    3. Sections starting with `## `
    4. Subsections starting with `### `
    5. Bullet content starting with `- `

    The function validates structural integrity (e.g., subsections must belong
    to a section, content must belong to a subsection) and ensures that the
    rendered preview contains exactly one `<TODO>` placeholder as the sole
    non-markdown content on its line.

    Args:
        markdown: A markdown-formatted string adhering to the expected structure.
            Must contain a title, tagline, at least one section with subsections
            and content, and exactly one `<TODO>` placeholder.

    Returns:
        A `Document` object with parsed header, tagline, sections, subsections,
        and content items.

    Raises:
        ValidationError: If the markdown does not start with a title (`# `).
        ValidationError: If the title is not followed by a tagline (`> `).
        ValidationError: If a subsection is found before any section.
        ValidationError: If content is found before any subsection.
        ValidationError: If a line does not match the expected format.
        ValidationError: If the preview does not contain exactly one `<TODO>`.
        ValidationError: If `<TODO>` is not the only non-markdown content on its line.

    Example:
        ```python
        markdown = '''
        # Project Proposal
        > A groundbreaking new idea

        ## Overview
        ### Summary
        - This project aims to solve X
        - <TODO>
        '''

        doc = load_markdown(markdown)
        print(doc.header)  # "Project Proposal"
        print(doc.tagline)  # "A groundbreaking new idea"
        ```
    """
    lines = markdown.strip().split('\n')
    
    # Validate title (must be first non-empty line)
    if not lines or not lines[0].startswith('# '):
        raise ValidationError("Document must start with a title (# Title)")
    
    header = lines[0][2:].strip()
    
    # Validate tagline (must be second non-empty line)
    idx = 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    
    if idx >= len(lines) or not lines[idx].startswith('> '):
        raise ValidationError("Title must be followed by a tagline (> Tagline)")
    
    tagline = lines[idx][2:].strip()
    idx += 1
    
    doc = Document(header=header, tagline=tagline)
    current_section = None
    current_subsection = None
    
    while idx < len(lines):
        line = lines[idx].strip()
        
        if not line:
            idx += 1
            continue
            
        if line.startswith('## '):
            current_section = line[3:].strip()
            doc.create_section(current_section)
            current_subsection = None
            
        elif line.startswith('### '):
            if current_section is None:
                raise ValidationError("Subsection found before any section")
            subsection_title = line[4:].strip()
            doc.create_subsection(current_section, subsection_title)
            current_subsection = doc.sections[current_section][-1]
            
        elif line.startswith('- '):
            if current_subsection is None:
                raise ValidationError("Content found before any subsection")
            content_text = line[2:].strip()
            current_subsection.add_content(Content(content_text))
            
        else:
            raise ValidationError(f"Invalid line format: '{line}'. Expected ##, ###, or -")
        
        idx += 1
    
    # Validate exactly one <TODO> on its own line
    preview = doc.preview()
    
    todo_count = preview.count('<TODO>')
    
    if todo_count != 1:
        print(preview)
        raise ValidationError(f"Preview must contain exactly one <TODO>, found {todo_count}")
    
    # Check that <TODO> is alone on its line (aside from markdown markers)
    preview_lines = preview.split('\n')
    todo_line_found = False
    for line in preview_lines:
        if '<TODO>' in line:
            # Strip markdown markers (-, ##, ###, >, #, whitespace)
            stripped = line.lstrip('#').lstrip('>').lstrip('-').strip()
            if stripped != '<TODO>':
                raise ValidationError(f"<TODO> must be the only non-markdown content on its line, found: '{line.strip()}'")
            todo_line_found = True
            break
    
    if not todo_line_found:
        raise ValidationError("Preview must contain exactly one <TODO>")
    
    return doc