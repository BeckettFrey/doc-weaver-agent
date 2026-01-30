"""LangGraph node functions for iterative text length adjustment.

This module provides the core node functions for a LangGraph-based state graph
that morphs text to fit within a target character range. The graph orchestrates
an iterative process of expansion and summarization using LLM calls until the
text fits the specified constraints or retries are exhausted.

Each node function operates on `AgentState`, a TypedDict that tracks the
morphing operation's progress, LLM conversation history, and success status.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
from langchain_core.messages import SystemMessage, HumanMessage


def get_system_prompt() -> str:
    """Generate the system prompt for the text morphing LLM.

    Constructs a system-level instruction that directs the LLM to act as a text
    morphing agent, adjusting text length while preserving meaning and outputting
    only the morphed text without preamble.

    Returns:
        The system prompt string to be wrapped in a `SystemMessage`.
    """
    return (
        "You are a text morphing agent. Your goal is to adjust the length of the provided text "
        "to fit within specified character limits by either summarizing or expanding it as needed. "
        "Always maintain the original meaning and context of the text while performing these modifications."
        "Always respond with only the morphed text, without any additional commentary or explanations."
        "I repeat, output ONLY the morphed text."
    )

def track_progress(state: AgentState) -> AgentState:
    """Update retry counter and success flag based on the latest LLM response.

    Checks the most recent response length against the target character range,
    decrements the retry counter, and sets the success flag to True if the
    response is within range.

    Args:
        state: The current agent state containing responses and target_chars.

    Returns:
        The updated state with decremented max_retries and potentially updated
        success flag.
    """
    last_response = state["responses"][-1] if state["responses"] else None
    target_chars = state["target_chars"]

    if not last_response:
        return state
    elif len(last_response) < target_chars[0]:
        state['max_retries'] -= 1
    elif len(last_response) > target_chars[1]:
        state['max_retries'] -= 1
    else:
        state["max_retries"] -= 1
        state['success'] = True
    return state

def should_continue(state: AgentState) -> str:
    """Determine the next graph edge based on current text length and retry count.

    This is the routing function for the LangGraph conditional edge. It evaluates
    whether the text is within the target character range, too short, too long,
    or if retries are exhausted.

    Args:
        state: The current agent state with text, responses, target_chars, and max_retries.

    Returns:
        One of "expand", "summarize", or "done" to route the graph flow:
        - "expand": text is too short and retries remain
        - "summarize": text is too long and retries remain
        - "done": text is within range or retries are exhausted
    """
    text = state["text"]
    last_response = state["responses"][-1] if state["responses"] else text
    target_chars = state["target_chars"]

    if state['max_retries'] <= 0 and state["responses"]:
        return "done"
    elif last_response and len(last_response) < target_chars[0]:
        return "expand"
    elif last_response and len(last_response) > target_chars[1]:
        return "summarize"
    else:
        return "done"

def summarizer(state: AgentState) -> AgentState:
    """Invoke the LLM to summarize text into the target character range.

    Constructs a summarization prompt based on whether this is the first attempt
    or a retry, calls the LLM using the model specified in state, and appends
    the response to the state's conversation history.

    The prompt includes both character and approximate word count targets (using
    a 5 characters per word heuristic). For retries, the prompt references the
    previous response length to guide the model.

    Args:
        state: The current agent state with text, target_chars, messages, and responses.

    Returns:
        The updated state with the LLM's summarized text appended to responses
        and the conversation extended with the new prompt and response.
    """
    llm = ChatOpenAI(model=state["model"])
    text = state["text"]
    target_chars = state["target_chars"]
    target_words = (target_chars[0] // 5, target_chars[1] // 5)  # Approximate target words

    prompt = None
    if len(state["responses"]) > 0:
        prompt = (
            f"That is {len(state['responses'][-1])} characters. "
            f"Make it shorter. Summarize the following text in {target_chars[0]}-{target_chars[1]} characters "
            f"({target_words[0]} to {target_words[1]} words). "
            "Be concise. Output ONLY the summary, no preamble.\n\n"
            f"Text:\n{text}\n"
        )
    else:
        prompt = (
            f"Summarize the following text in {target_chars[0]}-{target_chars[1]} characters "
            f"({target_words[0]} to {target_words[1]} words). "
            "Be concise. Output ONLY the summary, no preamble.\n\n"
            f"Text:\n{text}\n"
        )

    response = llm.invoke(state["messages"] + [HumanMessage(content=prompt)])

    state["responses"].append(response.content.strip())
    state["messages"].extend([HumanMessage(content=prompt), response])

    return state

def expander(state: AgentState) -> AgentState:
    """Invoke the LLM to expand text into the target character range.

    Constructs an expansion prompt based on whether this is the first attempt
    or a retry, calls the LLM using the model specified in state, and appends
    the response to the state's conversation history.

    The prompt includes both character and approximate word count targets (using
    a 5 characters per word heuristic) and instructs the model to maintain the
    original meaning while adding relevant details. For retries, the prompt
    references the previous response length to guide the model.

    Args:
        state: The current agent state with text, target_chars, messages, and responses.

    Returns:
        The updated state with the LLM's expanded text appended to responses
        and the conversation extended with the new prompt and response.
    """
    llm = ChatOpenAI(model=state["model"])
    text = state["text"]
    target_chars = state["target_chars"]
    target_words = (target_chars[0] // 5, target_chars[1] // 5)  # Approximate target words

    prompt = None
    if len(state["responses"]) > 0:
        prompt = (
            f"That is {len(state['responses'][-1])} characters. "
            f"Make it longer. Expand the following text to be between {target_chars[0]} and {target_chars[1]} characters "
            f"({target_words[0]} to {target_words[1]} words). "
            "Maintain the original meaning while adding relevant details.\n\n"
            f"Text:\n{text}\n"
        )
    else:
        prompt = (
            f"Expand the following text to be between {target_chars[0]} and {target_chars[1]} characters "
            f"({target_words[0]} to {target_words[1]} words). "
            "Maintain the original meaning while adding relevant details.\n\n"
            f"Text:\n{text}\n"
        )

    response = llm.invoke(state["messages"] + [HumanMessage(content=prompt)])

    state["responses"].append(response.content.strip())
    state["messages"].extend([HumanMessage(content=prompt), response])

    return state

def validate_start(state: AgentState) -> AgentState:
    """Validate input state and initialize the morphing task.

    Performs validation checks on the input state, ensures the system prompt is
    present in the message history, and handles the edge case where the input
    text already fits within the target character range.

    This node is the entry point to the morphing graph and should be invoked
    before any routing or LLM calls occur.

    Args:
        state: The initial agent state to validate.

    Returns:
        The validated and initialized state with:
        - System prompt injected into messages if not already present
        - success set to True and text added to responses if already in range
        - All other fields unchanged

    Raises:
        ValueError: If text is empty, target_chars min >= max, or messages list
            has more than 2 items (violating the pre-condition constraint).
    """
    text = state["text"]
    target_chars = state["target_chars"]

    if not text or not text.strip():
        raise ValueError("Invalid: text to morph is empty.")
    if target_chars[0] >= target_chars[1]:
        raise ValueError("Invalid: target_chars min must be less than max.")
    if len(state["messages"]) > 2:
        raise ValueError("Invalid: too many messages, maximum of 2.")
    if len(text) >= target_chars[0] and len(text) <= target_chars[1]:
        state['success'] = True
        state['responses'].append(text)
    if state["messages"] and not isinstance(state["messages"][0], SystemMessage):
        state["messages"].insert(0, SystemMessage(content=get_system_prompt()))
    if not state["messages"]:
        state["messages"] = [SystemMessage(content=get_system_prompt())]

    return state
