import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from doc_weaver.responder import todo_injector, Response
from langchain_core.messages import HumanMessage


class TestTodoInjector:

    @pytest.mark.asyncio
    async def test_raises_without_todo_placeholder(self):
        msg = HumanMessage(content="No placeholder here")
        with pytest.raises(ValueError, match="<TODO>"):
            await todo_injector(msg)

    @pytest.mark.asyncio
    async def test_returns_response_on_success(self):
        msg = HumanMessage(content="Fill in: <TODO>")
        expected = Response(text="Filled content")

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=expected)
        mock_chat = MagicMock()
        mock_chat.with_structured_output.return_value = mock_llm

        with patch("doc_weaver.responder.ChatOpenAI", return_value=mock_chat):
            result = await todo_injector(msg)

        assert result == expected
        assert result.text == "Filled content"

    @pytest.mark.asyncio
    async def test_uses_specified_model(self):
        msg = HumanMessage(content="Fill in: <TODO>")
        expected = Response(text="Result")

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=expected)
        mock_chat = MagicMock()
        mock_chat.with_structured_output.return_value = mock_llm

        with patch("doc_weaver.responder.ChatOpenAI", return_value=mock_chat) as mock_cls:
            await todo_injector(msg, model="gpt-4o-mini")

        mock_cls.assert_called_once_with(model="gpt-4o-mini")

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        import asyncio as aio
        msg = HumanMessage(content="Fill in: <TODO>")

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=aio.TimeoutError)
        mock_chat = MagicMock()
        mock_chat.with_structured_output.return_value = mock_llm

        with patch("doc_weaver.responder.ChatOpenAI", return_value=mock_chat), \
             patch("doc_weaver.responder.asyncio.wait_for", side_effect=aio.TimeoutError):
            result = await todo_injector(msg)

        assert result is None


class TestResponseModel:

    def test_response_fields(self):
        r = Response(text="hello")
        assert r.text == "hello"
