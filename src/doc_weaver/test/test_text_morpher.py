import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from doc_weaver.text_morpher.nodes import (
    get_system_prompt,
    track_progress,
    should_continue,
    validate_start,
    summarizer,
    expander,
)
from doc_weaver.text_morpher.state import AgentState


def _make_state(**overrides) -> AgentState:
    defaults = dict(
        model="gpt-4o",
        text="Some text here.",
        target_chars=(10, 50),
        messages=[],
        responses=[],
        max_retries=3,
        success=False,
    )
    defaults.update(overrides)
    return AgentState(**defaults)


class TestGetSystemPrompt:

    def test_returns_string(self):
        result = get_system_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mentions_text_morphing(self):
        assert "text morphing" in get_system_prompt().lower()

class TestTrackProgress:

    def test_no_responses_returns_state_unchanged(self):
        state = _make_state(responses=[])
        result = track_progress(state)
        assert result["max_retries"] == 3
        assert result["success"] is False

    def test_response_too_short_decrements_retries(self):
        state = _make_state(target_chars=(20, 50), responses=["Hi"])
        result = track_progress(state)
        assert result["max_retries"] == 2
        assert result["success"] is False

    def test_response_too_long_decrements_retries(self):
        state = _make_state(target_chars=(1, 5), responses=["This is way too long"])
        result = track_progress(state)
        assert result["max_retries"] == 2
        assert result["success"] is False

    def test_response_in_range_sets_success(self):
        state = _make_state(target_chars=(1, 50), responses=["Perfect length"])
        result = track_progress(state)
        assert result["success"] is True
        assert result["max_retries"] == 2


class TestShouldContinue:
    def test_no_responses_and_text_in_range_returns_done(self):
        state = _make_state(text="Hello world!", target_chars=(1, 50), responses=[])
        assert should_continue(state) == "done"

    def test_retries_exhausted_returns_done(self):
        state = _make_state(max_retries=0, responses=["short"], target_chars=(100, 200))
        assert should_continue(state) == "done"

    def test_response_too_short_returns_expand(self):
        state = _make_state(responses=["Hi"], target_chars=(20, 50))
        assert should_continue(state) == "expand"

    def test_response_too_long_returns_summarize(self):
        state = _make_state(responses=["A" * 100], target_chars=(1, 10))
        assert should_continue(state) == "summarize"

    def test_response_in_range_returns_done(self):
        state = _make_state(responses=["Just right"], target_chars=(1, 50))
        assert should_continue(state) == "done"


class TestValidateStart:
    def test_empty_text_raises(self):
        state = _make_state(text="   ")
        with pytest.raises(ValueError, match="empty"):
            validate_start(state)

    def test_min_gte_max_raises(self):
        state = _make_state(target_chars=(50, 30))
        with pytest.raises(ValueError, match="less than"):
            validate_start(state)

    def test_too_many_messages_raises(self):
        state = _make_state(messages=[
            SystemMessage(content="a"),
            HumanMessage(content="b"),
            AIMessage(content="c"),
        ])
        with pytest.raises(ValueError, match="too many messages"):
            validate_start(state)

    def test_text_already_in_range_sets_success(self):
        state = _make_state(text="Hello world!", target_chars=(5, 50))
        result = validate_start(state)
        assert result["success"] is True
        assert result["responses"] == ["Hello world!"]

    def test_inserts_system_prompt_when_missing(self):
        state = _make_state(messages=[HumanMessage(content="hi")])
        result = validate_start(state)
        assert isinstance(result["messages"][0], SystemMessage)

    def test_adds_system_prompt_when_empty(self):
        state = _make_state(messages=[])
        result = validate_start(state)
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], SystemMessage)

    def test_keeps_existing_system_prompt(self):
        msg = SystemMessage(content="Custom prompt")
        state = _make_state(messages=[msg])
        result = validate_start(state)
        assert result["messages"][0] is msg


class TestSummarizer:

    def _mock_llm(self, response_text):
        mock_response = MagicMock()
        mock_response.content = response_text
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = mock_response
        return mock_llm_instance

    @patch("doc_weaver.text_morpher.nodes.ChatOpenAI")
    def test_summarizer_no_prior_responses(self, mock_chat):
        mock_chat.return_value = self._mock_llm("Short summary")
        state = _make_state(text="Long text to summarize", target_chars=(5, 20), responses=[])
        result = summarizer(state)
        assert result["responses"][-1] == "Short summary"
        assert len(result["messages"]) == 2  # HumanMessage + AIMessage

    @patch("doc_weaver.text_morpher.nodes.ChatOpenAI")
    def test_summarizer_with_prior_responses(self, mock_chat):
        mock_chat.return_value = self._mock_llm("Shorter")
        state = _make_state(
            text="Long text to summarize",
            target_chars=(5, 20),
            responses=["Previous attempt that was too long"],
            messages=[SystemMessage(content="sys")],
        )
        result = summarizer(state)
        assert result["responses"][-1] == "Shorter"
        assert len(result["responses"]) == 2


class TestExpander:

    def _mock_llm(self, response_text):
        mock_response = MagicMock()
        mock_response.content = response_text
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = mock_response
        return mock_llm_instance

    @patch("doc_weaver.text_morpher.nodes.ChatOpenAI")
    def test_expander_no_prior_responses(self, mock_chat):
        mock_chat.return_value = self._mock_llm("Expanded text with more detail")
        state = _make_state(text="Short.", target_chars=(20, 50), responses=[])
        result = expander(state)
        assert result["responses"][-1] == "Expanded text with more detail"
        assert len(result["messages"]) == 2

    @patch("doc_weaver.text_morpher.nodes.ChatOpenAI")
    def test_expander_with_prior_responses(self, mock_chat):
        mock_chat.return_value = self._mock_llm("Even more expanded text with details")
        state = _make_state(
            text="Short.",
            target_chars=(20, 50),
            responses=["Too short still"],
            messages=[SystemMessage(content="sys")],
        )
        result = expander(state)
        assert result["responses"][-1] == "Even more expanded text with details"
        assert len(result["responses"]) == 2


class TestSimpleMorph:
    
    @patch("doc_weaver.text_morpher.TextMorphGraph")
    def test_success_with_morph(self, mock_graph):
        mock_graph.invoke.return_value = {
            "text": "Original text",
            "target_chars": (10, 50),
            "messages": [],
            "responses": ["Morphed text here"],
            "model": "gpt-4o",
            "max_retries": 1,
            "success": True,
        }
        from doc_weaver.text_morpher import simple_morph

        result = simple_morph("Original text", max_chars=50, min_chars=10, max_retries=3)
        assert result[0] is True
        assert result[1] == "Morphed text here"
        assert isinstance(result[4], float)

    @patch("doc_weaver.text_morpher.TextMorphGraph")
    def test_failure_returns_original(self, mock_graph):
        mock_graph.invoke.return_value = {
            "text": "Original",
            "target_chars": (100, 200),
            "messages": [],
            "responses": ["Still too short"],
            "model": "gpt-4o",
            "max_retries": 0,
            "success": False,
        }
        from doc_weaver.text_morpher import simple_morph

        result = simple_morph("Original", max_chars=200, min_chars=100, max_retries=3)
        assert result[0] is False
        assert result[1] == "Original"

    @patch("doc_weaver.text_morpher.TextMorphGraph")
    def test_text_already_in_range(self, mock_graph):
        text = "Already good"
        mock_graph.invoke.return_value = {
            "text": text,
            "target_chars": (5, 50),
            "messages": [],
            "responses": [text],
            "model": "gpt-4o",
            "max_retries": 3,
            "success": True,
        }
        from doc_weaver.text_morpher import simple_morph

        result = simple_morph(text, max_chars=50, min_chars=5, max_retries=3)
        assert result[0] is True
        assert result[1] == text
        assert result[2] == 0  # No LLM calls since text == response

    @patch("doc_weaver.text_morpher.TextMorphGraph")
    def test_exception_propagates(self, mock_graph):
        mock_graph.invoke.side_effect = ValueError("bad input")
        from doc_weaver.text_morpher import simple_morph

        with pytest.raises(ValueError, match="bad input"):
            simple_morph("text", max_chars=50, min_chars=10, max_retries=3)

    @patch("doc_weaver.text_morpher.TextMorphGraph")
    def test_custom_model_passed(self, mock_graph):
        mock_graph.invoke.return_value = {
            "text": "test",
            "target_chars": (1, 50),
            "messages": [],
            "responses": ["result"],
            "model": "gpt-4o-mini",
            "max_retries": 2,
            "success": True,
        }
        from doc_weaver.text_morpher import simple_morph

        simple_morph("test", max_chars=50, min_chars=1, max_retries=3, model="gpt-4o-mini")
        call_args = mock_graph.invoke.call_args[0][0]
        assert call_args["model"] == "gpt-4o-mini"
