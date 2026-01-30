"""LLM-based responder for filling TODO placeholders in documents.

This module provides an async agent that uses OpenAI's GPT models to generate
content for `<TODO>` placeholders within document templates. The responder
leverages LangChain for LLM orchestration and Pydantic for structured output
validation.

The primary use case is document hydration workflows where certain sections
are marked as TODO and need to be filled in programmatically based on context.

See Also:
    `doc_weaver.hydrate_queue`: Queue-based document hydration system.
    `doc_weaver.hydrate_batch`: Batch processing for multiple documents.
"""
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import asyncio

class Response(BaseModel):
    """Structured output model for TODO placeholder responses.

    This model captures the generated text that should replace a `<TODO>`
    placeholder in a document. The LLM returns instances of this model via
    LangChain's structured output capabilities.

    Attributes:
        text: The generated text content to fill in the TODO item.
    """
    text: str = Field(description="The text that fills in the <TODO> item.")

async def todo_injector(message: HumanMessage, model: str = "gpt-4o") -> Response | None:
    """Fill a TODO placeholder in a message using an LLM.

    Sends the provided message to an OpenAI GPT model via LangChain and
    requests structured output in the form of a `Response` object. The
    message must contain a `<TODO>` placeholder, which the LLM will
    attempt to fill in based on surrounding context.

    The function enforces a 30-second timeout on the LLM call and returns
    None if the timeout is exceeded.

    Args:
        message: A LangChain HumanMessage containing the document preview
            with a `<TODO>` placeholder. The message content is used as
            the primary prompt for the LLM.
        model: The OpenAI model identifier to use for generation.
            Defaults to "gpt-4o".

    Returns:
        A Response object containing the generated text, or None if the
        request times out after 30 seconds.

    Raises:
        ValueError: If the message content does not contain a `<TODO>`
            placeholder.
    """
    if '<TODO>' not in message.content:
        raise ValueError("Input message must contain a <TODO> placeholder.")

    llm = ChatOpenAI(model=model).with_structured_output(Response)

    messages = [
        SystemMessage(content="You are a helpful assistant that fills in the <TODO> item in the provided document preview."),
        message
    ]

    try:
        # Added safety measure to avoid hanging requests since it should never take this long
        response = await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=30.0
        )
        return response
    except asyncio.TimeoutError:
        print("Request timed out!")
        return None