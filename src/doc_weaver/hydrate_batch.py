"""Batch processing for resolving TODO placeholders in documents.

This module provides a single-item hydration function that combines LLM-based
TODO placeholder resolution with text length adjustment. The primary use case
is processing individual document items where a `<TODO>` marker needs to be
replaced with generated content that fits within specified character bounds.

The hydration workflow consists of two stages:
1. Call the responder (`doc_weaver.responder.todo_injector`) to generate
   replacement text based on document context.
2. If the generated text falls outside the target character range, use the
   text morphing graph (`doc_weaver.text_morpher.simple_morph`) to iteratively
   expand or summarize the text until it fits.

This module is designed to be called as part of a larger batch or queue-based
document hydration system, where multiple TODO items are processed in parallel
or sequentially.

See Also:
    `doc_weaver.hydrate_queue`: Queue-based TODO resolution with concurrency.
    `doc_weaver.responder.todo_injector`: LLM-based TODO placeholder filler.
    `doc_weaver.text_morpher.simple_morph`: Text length adjustment via LangGraph.
"""

import time
from doc_weaver.document import Document
from doc_weaver.responder import todo_injector
from doc_weaver.text_morpher import simple_morph
from langchain_core.messages import HumanMessage


async def hydrate_item(doc: Document, min_chars: int, max_chars: int, context: str = "", model: str = "gpt-4o", task_context: str = "") -> tuple[str, float]:
    """Resolves a single <TODO> placeholder in a Document.

    Calls the responder to fill in the <TODO>, then uses text_morpher
    to adjust the result to fit within the character bounds [min_chars, max_chars].

    Args:
        doc: A Document with exactly one <TODO> placeholder.
        min_chars: Inclusive lower bound for replacement character count.
        max_chars: Inclusive upper bound for replacement character count.
        context: Optional global context/instructions to include alongside
                 the document preview.
        model: The LLM model to use for text generation.
        task_context: Optional per-task context text to include between the
                      global context and the document preview.

    Returns:
        A tuple of (replacement_string, elapsed_ms).

    Raises:
        RuntimeError: If the responder returns no result or text morphing fails.
    """
    start = time.time()

    preview = doc.preview()
    parts = [p for p in [context, task_context, preview] if p]
    content = "\n\n".join(parts)
    message = HumanMessage(content=content)
    response = await todo_injector(message, model=model)

    if response is None:
        raise RuntimeError("Responder returned no result for <TODO> placeholder.")

    text = response.text

    if min_chars <= len(text) <= max_chars:
        elapsed_ms = (time.time() - start) * 1000
        return text, elapsed_ms

    # Can expand metadata here later if needed
    success, morphed_text, _, _, _ = simple_morph(
        text=text,
        max_chars=max_chars,
        min_chars=min_chars,
        max_retries=3,
        model=model,
    )

    if not success:
        raise RuntimeError(
            f"Text morphing failed. Got {len(morphed_text)} chars, "
            f"needed [{min_chars}, {max_chars}]."
        )

    elapsed_ms = (time.time() - start) * 1000
    return morphed_text, elapsed_ms
