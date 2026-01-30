"""Batch-based hydration of markdown placeholders with LLM-generated content.

This module provides a queue-based system for processing markdown documents
containing `<A, B, C, context_id>` placeholders, where A is the batch number, B is the
minimum character count, C is the maximum character count, and context_id (corresponding to a context string). The queue
processes placeholders in batch order, with all items in the same batch
resolved concurrently.

The main entry point is `hydrate`, which orchestrates the entire process
from parsing to final document generation with metadata tracking.

See Also:
    `doc_weaver.hydrate_batch`: Single-item hydration implementation.
    `doc_weaver.document.Document`: The document model passed to the LLM.
    `doc_weaver.parser.load_markdown`: Markdown parsing utilities.
"""
import asyncio
import re
import time
from typing import List, Tuple
from doc_weaver.document import Document
from doc_weaver.parser import load_markdown
from doc_weaver.hydrate_batch import hydrate_item

PLACEHOLDER_PATTERN = re.compile(r'<(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([A-Za-z_]\w*))?>')


class HydrationTask:
    """A single placeholder to be resolved, with its character bounds and unique marker."""

    def __init__(self, batch: int, min_chars: int, max_chars: int, raw: str, marker: str, context_id: str | None = None):
        """Initialize a hydration task from parsed placeholder data.

        Args:
            batch: The batch number determining processing order. Lower numbers
                are processed first; equal numbers are processed concurrently.
            min_chars: Minimum character count for the replacement text (inclusive).
            max_chars: Maximum character count for the replacement text (inclusive).
            raw: The original placeholder string as it appeared in the markdown,
                e.g. `"<1, 50, 200>"`.
            marker: Unique marker string replacing this placeholder during processing,
                e.g. `"<<TASK_0>>"`.
            context_id: Optional context identifier for task-specific context,
                e.g. `"dam_engineering"`.
        """
        self.batch = batch
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.raw = raw # the original placeholder string, e.g. "<1, 50, 200>"
        self.marker = marker # unique marker replacing this placeholder, e.g. "<<TASK_0>>"
        self.context_id = context_id # optional context ID, e.g. "dam_engineering"


class HydrateQueue:
    """Builds a queue of batches from a markdown document containing <A, B, C, context_id> placeholders.

    Takes a markdown document string and builds a queue by replacing <A, B, C, context_id>
    with actual content in batches. A determines the batch order where lower
    numbers come first and equal numbers are filled concurrently. B is the
    inclusive lower bound for number of characters allowed in the replacement
    text. C is the inclusive upper bound.

    Each batch depends on the previous batch's results, so the document is
    updated between batches. Members of the same batch do not depend on each
    other's completed responses.
    """

    def __init__(self, markdown: str):
        """Initialize the queue from a markdown document containing placeholders.

        Parses all `<A, B, C, context_id>` placeholders in the document, replaces them with
        unique markers, and prepares the batch processing queue sorted by batch
        number.

        Args:
            markdown: Markdown document string containing zero or more `<A, B, C, context_id>`
                placeholders. Placeholders are regex-matched as `<int, int, int>` or
                `<int, int, int, identifier>`.
        """
        self._original_markdown = markdown
        self._tasks = self._parse_tasks()
        self._current_markdown = self._inject_markers(markdown)
        self._batch_numbers = sorted(set(t.batch for t in self._tasks))
        self._batch_index = 0

    def _parse_tasks(self) -> List[HydrationTask]:
        """Extract and parse all placeholders from the original markdown.

        Scans the document for `<A, B, C, context_id>` patterns and creates a `HydrationTask`
        for each, assigning a unique sequential marker like `<<TASK_0>>`.

        Returns:
            List of `HydrationTask` objects in order of appearance in the document.
        """
        tasks = []
        for i, match in enumerate(PLACEHOLDER_PATTERN.finditer(self._original_markdown)):
            batch = int(match.group(1))
            min_chars = int(match.group(2))
            max_chars = int(match.group(3))
            context_id = match.group(4)  # None if not present
            marker = f"<<TASK_{i}>>"
            tasks.append(HydrationTask(batch, min_chars, max_chars, match.group(0), marker, context_id))
        return tasks

    def _inject_markers(self, markdown: str) -> str:
        """Replace each placeholder with its unique marker, working right-to-left
        so earlier offsets remain valid."""
        result = markdown
        matches = list(PLACEHOLDER_PATTERN.finditer(markdown))
        for task, match in reversed(list(zip(self._tasks, matches))):
            result = result[:match.start()] + task.marker + result[match.end():]
        return result

    @property
    def done(self) -> bool:
        """Check whether all batches have been processed.

        Returns:
            True if all batches have been processed and no more work remains,
            False otherwise.
        """
        return self._batch_index >= len(self._batch_numbers)

    @property
    def current_batch_number(self) -> int | None:
        """Get the batch number currently being processed.

        Returns:
            The integer batch number (A value from `<A, B, C, context_id>`) for the current
            batch, or None if all batches are complete.
        """
        if self.done:
            return None
        return self._batch_numbers[self._batch_index]

    def next_batch(self) -> List[Tuple[Document, int, int, str | None]]:
        """Returns the next batch as a list of (Document, min_chars, max_chars, context_id).

        For each task in the current batch, produces a Document where:
        - The current task's placeholder is replaced with <TODO>
        - All other unresolved placeholders are replaced with (will be filled later)
        """
        if self.done:
            raise StopIteration("All batches have been processed.")

        batch_num = self._batch_numbers[self._batch_index]
        batch_tasks = [t for t in self._tasks if t.batch == batch_num]

        marker_pattern = re.compile(r'<<TASK_\d+>>')

        results = []
        for task in batch_tasks:
            md = self._current_markdown
            # Replace the current task's marker with <TODO>
            md = md.replace(task.marker, '<TODO>')
            # Replace all other remaining markers with (will be filled later)
            md = marker_pattern.sub('(will be filled later)', md)
            doc = load_markdown(md, check_todo=True)
            results.append((doc, task.min_chars, task.max_chars, task.context_id))

        return results

    def submit_results(self, results: List[str]) -> None:
        """Accepts results for the current batch and advances to the next.

        Args:
            results: A list of replacement strings, one per task in the current
                     batch, in the same order returned by next_batch().
        """
        if self.done:
            raise StopIteration("All batches have been processed.")

        batch_num = self._batch_numbers[self._batch_index]
        batch_tasks = [t for t in self._tasks if t.batch == batch_num]

        if len(results) != len(batch_tasks):
            raise ValueError(
                f"Expected {len(batch_tasks)} results for batch {batch_num}, "
                f"got {len(results)}."
            )

        for task, replacement in zip(batch_tasks, results):
            self._current_markdown = self._current_markdown.replace(
                task.marker, replacement
            )

        self._batch_index += 1

    @property
    def current_markdown(self) -> str:
        """Get the current state of the markdown document.

        As batches are processed and results submitted, this property reflects
        the progressively hydrated document with completed placeholders replaced
        by their generated text.

        Returns:
            The markdown string with all processed placeholders replaced and
            any remaining placeholders still represented by their unique markers.
        """
        return self._current_markdown


async def hydrate(markdown: str, context: str = "", timeout: int = 30, model: str = "gpt-4o", contexts: dict[str, str] | None = None) -> tuple[str, dict]:
    """Resolves all <A, B, C, context_id> placeholders in a markdown document.

    Processes batches sequentially (lower A first), running all items within
    a batch concurrently. Each batch sees the results of all previous batches
    in the document context.

    Args:
        markdown: A markdown string containing placeholders.
        context: Optional global context/instructions to include alongside
                 the document preview for every placeholder.
        timeout: Maximum time in seconds to wait for each batch to complete.
        model: The LLM model to use for text generation.
        contexts: Optional mapping of context ID to context text. Tasks that
                  reference a context_id will have the corresponding text
                  prepended to their content in addition to the global context.

    Returns:
        A tuple of (hydrated_markdown, metadata) where metadata is a dict with:
            - tasks: list of per-task metadata dicts
            - total_elapsed_ms: total wall-clock time in milliseconds
            - model: the model used
    """
    if contexts is None:
        contexts = {}

    queue = HydrateQueue(markdown)

    # Validate that all referenced context IDs exist
    missing = [t.context_id for t in queue._tasks if t.context_id and t.context_id not in contexts]
    if missing:
        unique_missing = sorted(set(missing))
        raise ValueError(f"Missing context(s): {', '.join(unique_missing)}. Add them with `doc-weaver context add`.")

    task_metadata = []
    global_task_number = 0
    total_start = time.time()

    while not queue.done:
        batch_num = queue.current_batch_number
        batch = queue.next_batch()
        batch_tasks = [t for t in queue._tasks if t.batch == batch_num]

        coros = [
            hydrate_item(doc, min_c, max_c, context, model, task_context=contexts.get(ctx_id, "") if ctx_id else "")
            for doc, min_c, max_c, ctx_id in batch
        ]
        results_with_timing = await asyncio.wait_for(asyncio.gather(*coros), timeout=timeout)

        replacements = []
        for i, (text, elapsed_ms) in enumerate(results_with_timing):
            task = batch_tasks[i]
            task_metadata.append({
                "task_number": global_task_number,
                "marker": task.marker,
                "batch_num": batch_num,
                "char_range": [task.min_chars, task.max_chars],
                "total_chars": len(text),
                "elapsed_ms": round(elapsed_ms, 2),
                "model": model,
                "context_id": task.context_id,
            })
            replacements.append(text)
            global_task_number += 1

        queue.submit_results(replacements)

    total_elapsed_ms = (time.time() - total_start) * 1000

    # The marker document shows <<TASK_N>> placeholders instead of content
    marker_doc = queue._inject_markers(queue._original_markdown)

    metadata = {
        "tasks": task_metadata,
        "total_elapsed_ms": round(total_elapsed_ms, 2),
        "model": model,
        "marker_document": marker_doc,
    }

    return queue.current_markdown, metadata
