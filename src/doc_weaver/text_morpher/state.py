"""Define the state schema for text morphing operations.

This module contains the `AgentState` TypedDict that represents the complete
state for the text_morpher LangGraph workflow, including input text, target
character ranges, LLM configuration, and execution tracking.
"""
from typing import List, TypedDict

class AgentState(TypedDict):
    """TypedDict representing the state for text morphing operations.
    Attributes:
        model (str): The model to use for inference. Defaults to "gpt-4o".
        text (str): The text to be morphed.
        target_chars (tuple[int, int]): The target character range as a tuple (min, max).
        max_retries (int): Maximum number of retries allowed for total LLM calls. Defaults to 3.
        messages (List[dict]): The message history for the LLM (maximum 2 messages at invocation).
        responses (List[str]): The list of content received from the LLM.
        success (bool): Whether the morphing was successful. Defaults to False.
    """
    model: str = "gpt-4o"
    text: str
    target_chars: tuple[int, int]
    max_retries: int = 3
    messages: List[dict]
    responses: List[str]
    success: bool = False
    
   