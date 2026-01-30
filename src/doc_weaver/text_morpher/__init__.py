"""Text Morphing Module

This module provides functionality for morphing text to fit within specified character limits
by either expanding or summarizing the content. It utilizes a state graph to manage the
morphing process, allowing for iterative adjustments until the desired text length is achieved.

Exports
-------
TextMorphGraph : The compiled state graph for text morphing.
TextMorphState : The state and API for text morphing operations.
simple_morph : A wrapper function that provides a higher level API for text morphing.
"""

import time
from .nodes import validate_start, track_progress, should_continue, summarizer, expander
from .state import AgentState as TextMorphState
from langgraph.graph import StateGraph, START, END

nodes = StateGraph(TextMorphState)

# Node registrations
nodes.add_node("validate_start", validate_start)
nodes.add_node("summarizer", summarizer)
nodes.add_node("expander", expander)
nodes.add_node("track_progress", track_progress)

# Edge registrations
nodes.add_edge(START, "validate_start")
nodes.add_conditional_edges("validate_start", should_continue, {
    "expand": "expander",
    "summarize": "summarizer",
    "done": END
})

# Loop edges
nodes.add_edge("expander", "track_progress")
nodes.add_edge("summarizer", "track_progress")
nodes.add_conditional_edges("track_progress", should_continue, {
    "expand": "expander",
    "summarize": "summarizer",
    "done": END
})

TextMorphGraph = nodes.compile()

def simple_morph(text, max_chars, min_chars, max_retries, model: str = "gpt-4o") -> list[bool, str, int]:
    """A simple morph function that runs the TextMorphGraph.

    Args:
        text (str): The text to be morphed.
        max_chars (int): The maximum target character length.
        min_chars (int): The minimum target character length.
        max_retries (int): The maximum number of retries for LLM calls.

    Returns:
        list[bool, str, int, int, float]: A list containing:
            - success (bool): Whether the morphing was successful.
            - morphed_text (str): The morphed text.
            - total_calls (int): The total number of LLM calls made.
            - num_characters (int): The number of characters in the morphed text.
            - elapsed_ms (float): The time taken in milliseconds.

    Raises:
        Exception: If an error occurs during the morphing process.
    """

    start = time.time()

    try:
        result: TextMorphState = TextMorphGraph.invoke(TextMorphState(
            text=text,
            target_chars=(min_chars, max_chars),
            messages=[],
            responses=[],
            model=model,
            max_retries=max_retries,
            success=False
        ))

    except Exception as e:
        print(f"Error during text morphing: {e}")
        raise e

    elapsed_ms = (time.time() - start) * 1000

    total_calls = max_retries - result['max_retries'] + 1

    if result['responses'][-1] == text:
        # No initial attempt
        total_calls -= 1

    if not result['success']:
        return [False, text, total_calls, len(text), elapsed_ms]
    else:
        return [True, result['responses'][-1], total_calls, len(result['responses'][-1]), elapsed_ms]
        

__all__ = [
    "TextMorphGraph",
    "TextMorphState",
    "simple_morph"
]