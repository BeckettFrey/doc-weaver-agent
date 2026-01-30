"""Providing a md document hydration and transformation toolkit.

Utilities for parsing structured (and interacting programmatically) with Markdown documents, hydrating
templates with AI-generated content, and applying text transformations.
"""

from doc_weaver.document import Document, SubSection, Content
from doc_weaver.parser import load_markdown, ValidationError
from doc_weaver.hydrate_queue import hydrate, HydrateQueue
from doc_weaver.hydrate_batch import hydrate_item
from doc_weaver.text_morpher import simple_morph

__all__ = [
    "Document",
    "SubSection",
    "Content",
    "load_markdown",
    "ValidationError",
    "hydrate",
    "HydrateQueue",
    "hydrate_item",
    "simple_morph",
]
