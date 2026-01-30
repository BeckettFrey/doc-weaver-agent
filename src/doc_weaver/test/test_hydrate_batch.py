import pytest
from unittest.mock import patch, AsyncMock
from doc_weaver.hydrate_batch import hydrate_item
from doc_weaver.responder import Response
from doc_weaver.parser import load_markdown


SAMPLE_MD = """# John Doe - Software Engineer

> Experienced engineer building great software.

## Experience
### Work Experience
- <TODO>
- Senior Dev at StartupXYZ"""


def make_doc():
    return load_markdown(SAMPLE_MD, check_todo=True)


class TestHydrateItem:

    @pytest.mark.asyncio
    async def test_returns_response_when_in_bounds(self):
        doc = make_doc()
        mock_response = Response(text="Built REST APIs in Python")

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response):
            result, elapsed_ms = await hydrate_item(doc, min_chars=10, max_chars=50)

        assert result == "Built REST APIs in Python"
        assert isinstance(elapsed_ms, float)
        assert elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_calls_morph_when_too_long(self):
        doc = make_doc()
        long_text = "A" * 200
        mock_response = Response(text=long_text)

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response), \
             patch("doc_weaver.hydrate_batch.simple_morph", return_value=[True, "Shortened text here", 1, 19, 5.0]) as mock_morph:
            result, elapsed_ms = await hydrate_item(doc, min_chars=10, max_chars=50)

        mock_morph.assert_called_once_with(text=long_text, max_chars=50, min_chars=10, max_retries=3, model="gpt-4o")
        assert result == "Shortened text here"

    @pytest.mark.asyncio
    async def test_calls_morph_when_too_short(self):
        doc = make_doc()
        mock_response = Response(text="Hi")

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response), \
             patch("doc_weaver.hydrate_batch.simple_morph", return_value=[True, "Expanded text content", 1, 21, 5.0]) as mock_morph:
            result, elapsed_ms = await hydrate_item(doc, min_chars=10, max_chars=50)

        mock_morph.assert_called_once_with(text="Hi", max_chars=50, min_chars=10, max_retries=3, model="gpt-4o")
        assert result == "Expanded text content"

    @pytest.mark.asyncio
    async def test_skips_morph_at_exact_lower_bound(self):
        doc = make_doc()
        text = "A" * 10
        mock_response = Response(text=text)

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response), \
             patch("doc_weaver.hydrate_batch.simple_morph") as mock_morph:
            result, elapsed_ms = await hydrate_item(doc, min_chars=10, max_chars=50)

        mock_morph.assert_not_called()
        assert result == text

    @pytest.mark.asyncio
    async def test_skips_morph_at_exact_upper_bound(self):
        doc = make_doc()
        text = "A" * 50
        mock_response = Response(text=text)

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response), \
             patch("doc_weaver.hydrate_batch.simple_morph") as mock_morph:
            result, elapsed_ms = await hydrate_item(doc, min_chars=10, max_chars=50)

        mock_morph.assert_not_called()
        assert result == text

    @pytest.mark.asyncio
    async def test_raises_on_none_response(self):
        doc = make_doc()

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=None):
            with pytest.raises(RuntimeError, match="Responder returned no result"):
                await hydrate_item(doc, min_chars=10, max_chars=50)

    @pytest.mark.asyncio
    async def test_raises_on_morph_failure(self):
        doc = make_doc()
        mock_response = Response(text="A" * 200)

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response), \
             patch("doc_weaver.hydrate_batch.simple_morph", return_value=[False, "A" * 200, 3, 200, 5.0]):
            with pytest.raises(RuntimeError, match="Text morphing failed"):
                await hydrate_item(doc, min_chars=10, max_chars=50)

    @pytest.mark.asyncio
    async def test_context_included_in_message(self):
        doc = make_doc()
        mock_response = Response(text="Built REST APIs in Python")

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response) as mock_injector:
            await hydrate_item(doc, min_chars=10, max_chars=50, context="Write for a senior role")

        message = mock_injector.call_args[0][0]
        assert "Write for a senior role" in message.content
        assert "<TODO>" in message.content

    @pytest.mark.asyncio
    async def test_no_context_sends_preview_only(self):
        doc = make_doc()
        preview = doc.preview()
        mock_response = Response(text="Built REST APIs in Python")

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response) as mock_injector:
            await hydrate_item(doc, min_chars=10, max_chars=50)

        message = mock_injector.call_args[0][0]
        assert message.content == preview

    @pytest.mark.asyncio
    async def test_passes_model_to_todo_injector(self):
        doc = make_doc()
        mock_response = Response(text="Built REST APIs in Python")

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response) as mock_injector:
            await hydrate_item(doc, min_chars=10, max_chars=50, model="gpt-4o-mini")

        assert mock_injector.call_args[1]["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_passes_model_to_simple_morph(self):
        doc = make_doc()
        mock_response = Response(text="A" * 200)

        with patch("doc_weaver.hydrate_batch.todo_injector", new_callable=AsyncMock, return_value=mock_response), \
             patch("doc_weaver.hydrate_batch.simple_morph", return_value=[True, "Shortened text", 1, 14, 5.0]) as mock_morph:
            await hydrate_item(doc, min_chars=10, max_chars=50, model="gpt-4o-mini")

        assert mock_morph.call_args[1]["model"] == "gpt-4o-mini"
