"""Define structured document models for generating markdown content.

This module provides a hierarchical document model with three core classes:
`Content`, `SubSection`, and `Document`. Each level represents a progressively
higher-level abstraction in a markdown document structure, with automatic
UUID-based identification for content tracking.

The model is designed to support programmatic document generation workflows where
sections, subsections, and content items are dynamically created and assembled
into a final markdown preview.

See Also:
    `doc_weaver.parser`: Parses markdown into Document instances.
"""

from typing import *
from uuid import uuid4

class Content():
    """A single text content item with a unique identifier.

    Content represents the atomic unit of text in a document. Each instance
    is assigned a UUID-based identifier for tracking and referencing within
    subsections.

    Attributes:
        text: The text content of this item.
        id: A unique identifier for this content item. Auto-generated as a
            UUID string if not provided.

    Example:
        ```python
        content = Content(text="Revenue increased by 15% year-over-year.")
        print(content.id)  # "a1b2c3d4-..."
        print(str(content))  # "Revenue increased by 15% year-over-year."
        ```
    """
    text: str
    id: str

    def __init__(self, text: str, id = None) -> None:
        """Initialize a new Content item.

        Args:
            text: The text content.
            id: Optional identifier. If not provided, a new UUID is generated.
        """
        self.id = id if id else str(uuid4())
        self.text = text

    def __str__(self) -> str:
        """Return the text content as a string.

        Returns:
            The text attribute if non-empty, otherwise an empty string.
        """
        if self.text:
            return self.text
        return ""
    
class SubSection():
    """A titled subsection containing a list of content items.

    SubSection represents a markdown H3 heading followed by a bulleted list
    of `Content` items. Each subsection is assigned a unique identifier for
    referencing within the parent section.

    Attributes:
        title: The subsection title (rendered as an H3 heading in markdown).
        items: A list of `Content` instances contained in this subsection.
        id: A unique identifier for this subsection. Auto-generated as a
            UUID string if not provided.

    Example:
        ```python
        subsection = SubSection(title="Key Findings")
        subsection.add_content(Content("Finding 1"))
        subsection.add_content(Content("Finding 2"))

        print(str(subsection))
        # ### Key Findings
        # - Finding 1
        # - Finding 2
        ```
    """
    title: str
    items: List[Content]
    id: str

    def __init__(self, title: str, items: List[Content] = None, id=None) -> None:
        """Initialize a new SubSection.

        Args:
            title: The subsection title.
            items: Optional initial list of `Content` instances. Defaults to
                an empty list.
            id: Optional identifier. If not provided, a new UUID is generated.
        """
        self.id = id if id else str(uuid4())
        self.title = title
        self.items = items if items is not None else []

    def add_content(self, item: Content, index=None) -> None:
        """Add a content item to this subsection.

        Args:
            item: The `Content` instance to add.
            index: Optional position to insert the item. If not provided,
                the item is appended to the end of the list.
        """
        if index is not None:
            self.items.insert(index, item)
        else:
            self.items.append(item)

    def __str__(self) -> str:
        """Render the subsection as markdown.

        Returns:
            A markdown string with an H3 title followed by bulleted list items.
        """
        preview = f"### {self.title}\n"
        for item in self.items:
            preview += f"- {str(item)}\n"
        return preview


class Document():
    """A top-level document with header, tagline, and hierarchical sections.

    Document represents a complete markdown document with a title (H1), tagline
    (blockquote), and a collection of sections. Each section is a dictionary
    mapping section titles (rendered as H2) to lists of `SubSection` instances.

    The model provides convenience methods for creating sections, subsections,
    and content items, as well as a `preview` method that renders the entire
    document as markdown.

    Attributes:
        id: A unique identifier for this document. Auto-generated as a UUID
            string if not provided.
        sections: A dictionary mapping section titles to lists of `SubSection`
            instances.
        header: The document header (rendered as an H1 heading in markdown).
        tagline: The document tagline (rendered as a blockquote in markdown).

    Example:
        ```python
        doc = Document(header="Q1 Report", tagline="Summary of achievements")
        doc.create_section("Results")
        doc.create_subsection("Results", ["Revenue", "Costs"])

        # Get the first subsection's ID to add content
        revenue_id = doc.sections["Results"][0].id
        doc.create_content("Results", revenue_id, "Up 20%")

        markdown = doc.preview()
        ```
    """
    def __init__(self, header: str, tagline: str, sections = None, id=None) -> None:
        """Initialize a new Document.

        Args:
            header: The document header (H1 title).
            tagline: The document tagline (blockquote).
            sections: Optional initial sections dictionary. Defaults to an
                empty dictionary.
            id: Optional identifier. If not provided, a new UUID is generated.
        """
        self.id = id if id else str(uuid4())
        self.sections = sections if sections is not None else {}
        self.header = header
        self.tagline = tagline

    def create_section(self, title: str) -> None:
        """Create a new section in the document.

        If a section with the given title already exists, it will be
        overwritten with an empty list.

        Args:
            title: The section title (will be rendered as an H2 heading).
        """
        self.sections[title] = []

    def create_subsection(self, section_title: str, subsection_titles: Union[str, List[str]]) -> None:
        """Create one or more subsections within a section.

        If the section does not exist, it will be created automatically.
        Each subsection is initialized with an empty list of content items.

        Args:
            section_title: The parent section title.
            subsection_titles: A single subsection title string or a list of
                subsection title strings.
        """
        if section_title not in self.sections:
            self.sections[section_title] = []
        if isinstance(subsection_titles, str):
            subsection_titles = [subsection_titles]
        for title in subsection_titles:
            new_subsection = SubSection(title=title, items=[])
            self.sections[section_title].append(new_subsection)

    def create_content(self, section_title: str, subsection_id: str, text: str) -> None:
        """Create a content item within a specific subsection.

        Locates the subsection by ID within the specified section and adds
        a new `Content` instance with the provided text. If the section does
        not exist, it will be created. If the subsection ID is not found,
        the method returns without adding content.

        Args:
            section_title: The parent section title.
            subsection_id: The unique identifier of the target subsection.
            text: The text content to add.
        """
        if section_title not in self.sections:
            self.sections[section_title] = []
        for subsection in self.sections[section_title]:
            if subsection.id == subsection_id:
                subsection.add_content(Content(text))
                return

    def preview(self) -> str:
        """Render the entire document as markdown.

        Returns:
            A markdown string with H1 header, blockquote tagline, H2 sections,
            and H3 subsections with bulleted content items.
        """
        preview = f"# {self.header}\n\n> {self.tagline}\n\n"
        for key, section in self.sections.items():
            preview += f"## {key}\n"
            for sec in section:
                preview += str(sec) + "\n"

        return preview