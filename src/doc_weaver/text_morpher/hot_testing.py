"""These tests require API access and may incur high costs, thus they are disconnected from pytest to reduce api calls in case testing is automated or agents are trigger happy."""

import pytest
from langchain_core.messages import SystemMessage

from dotenv import load_dotenv
load_dotenv()

class TestUnit:

    class TestShouldContinue:

        def test_should_continue_expand(self):
            """Tests should_continue when expansion is needed."""
            from .nodes import should_continue
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Some text",
                target_chars=(10, 50),
                messages=[],
                responses=["Short"],
                max_retries=2,
                success=False
            )
            action = should_continue(state)
            assert action == "expand"

        def test_should_continue_done(self):
            """Tests should_continue when the last response is within target range."""
            from .nodes import should_continue
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Some text",
                target_chars=(1, 50),
                messages=[],
                responses=["This text is within the target range."],
                max_retries=2,
                success=False
            )
            action = should_continue(state)
            assert action == "done"

        def test_should_continue_summarize(self):
            """Tests should_continue when summarization is needed."""
            from .nodes import should_continue
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Some text",
                target_chars=(1, 10),
                messages=[],
                responses=["This text is way too long and needs to be shortened."],
                max_retries=2,
                success=False
            )
            action = should_continue(state)
            assert action == "summarize"

    class TestTrackProgress:

        def test_track_progress_success(self):
            """Tests track_progress when the last response is within range."""
            from .nodes import track_progress
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Some text",
                target_chars=(1, 50),
                messages=[],
                responses=["This text is within the target range."],
                max_retries=2,
                success=False
            )
            updated_state = track_progress(state)
            assert updated_state['success'] is True

        def test_track_progress_retry_decrement(self):
            """Tests track_progress when the last response is out of range."""
            from .nodes import track_progress
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Some text",
                target_chars=(10, 20),
                messages=[],
                responses=["Short"],
                max_retries=2,
                success=False
            )
            updated_state = track_progress(state)
            assert updated_state['max_retries'] == 1

        def test_track_progress_no_response(self):
            """Tests track_progress when there is no last response."""
            from .nodes import track_progress
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Some text",
                target_chars=(10, 20),
                messages=[],
                responses=[],
                max_retries=2,
                success=False
            )
            updated_state = track_progress(state)
            assert updated_state == state  # No changes expected

    class TestExpander:

        def test_expander_success(self):
            """Tests the expander when it can meet the target character range."""
            from .nodes import expander
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Short text.",
                target_chars=(50, 100),
                messages=[],
                responses=[],
                max_retries=2,
                success=False
            )
            result = expander(state)

            assert len(result["responses"][-1]) >= 50 and len(result["responses"][-1]) <= 100
            assert isinstance(result, type(AgentState(
                model="gpt-4o",
                text="",
                target_chars=(1, 1),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )))
        
        def test_expander_failure(self):
            """Tests the expander when it cannot meet the target character range."""
            from .nodes import expander
            from .state import AgentState

            state = AgentState(
                model="gpt-4o",
                text="Short text.",
                target_chars=(1000, 2000),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )
            result = expander(state)

            assert len(result["responses"][-1]) < 1000 or len(result["responses"][-1]) > 2000
            assert isinstance(result, type(AgentState(
                model="gpt-4o",
                text="",
                target_chars=(1, 1),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )))

    class TestSummarizer:
        def test_summarizer_success(self):
            """Tests the summarizer when it can meet the target character range."""
            from .nodes import summarizer
            from .state import AgentState

            result = summarizer(AgentState(
                model="gpt-4o",
                text="This is a long text that needs to be summarized.",
                target_chars=(1, 30),
                messages=[],
                responses=[],
                max_retries=3,
                success=False
            ))
            
            assert len(result["responses"][-1]) >= 1 and len(result["responses"][-1]) <= 30
            assert isinstance(result, type(AgentState(
                model="gpt-4o",
                text="",
                target_chars=(1, 1),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )))

        def test_summarizer_failure(self):
            """Tests the summarizer when it cannot meet the target character range."""
            from .nodes import summarizer
            from .state import AgentState

            result = summarizer(AgentState(
                model="gpt-4o",
                text="This is a long text that needs to be summarized.",
                target_chars=(5, 5),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            ))

            assert len(result["responses"][-1]) < 5 or len(result["responses"][-1]) > 5
            assert isinstance(result, type(AgentState(
                model="gpt-4o",
                text="",
                target_chars=(1, 1),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )))

# Helper function to verify successful invocation
def verify_success(state):
        print(state["responses"][-1])
        assert state['success'] is True
        assert isinstance(state['responses'][-1], str)
        assert len(state['responses'][-1]) >= state['target_chars'][0]
        assert len(state['responses'][-1]) <= state['target_chars'][1]
        assert len(state['responses']) > 0
        
class TestIntegration:

    @pytest.mark.integration
    def test_simple_extend(self):
        """Tests a scenario where the LLM hits the target character range on the first try."""
        from . import TextMorphGraph, TextMorphState

        result = TextMorphGraph.invoke(
            TextMorphState(
                model="gpt-4o",
                text="Once upon a time in a land far",
                target_chars=(50, 100),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )
        )

        verify_success(result)

    @pytest.mark.integration
    def test_simple_summarize(self):
        """Tests a scenario where the LLM hits the target character range on the first try."""
        from . import TextMorphGraph, TextMorphState

        result = TextMorphGraph.invoke(
            TextMorphState(
                model="gpt-4o",
                text=("In a village of La Mancha, the name of which I have no desire to call to mind, "
                      "there lived not long since one of those gentlemen that keep a lance in the lance-rack, "
                      "an old buckler, a lean hack, and a greyhound for coursing."),
                target_chars=(50, 100),
                messages=[],
                responses=[],
                max_retries=0,
                success=False
            )
        )

        verify_success(result)

    def test_multi_attempt_summarize(self):
        """Tests a scenario where the LLM overshoots the target character range when expanding."""
        from . import TextMorphGraph, TextMorphState

        result = TextMorphGraph.invoke(
            TextMorphState(
                model="gpt-4o",
                text="Hockey is a fast-paced sport played on ice, where two teams compete to score goals by hitting a puck into the opponent's net using sticks. The game requires a combination of speed, skill, and teamwork, as players skate across the rink, passing the puck and attempting to outmaneuver their opponents. With physical contact allowed, hockey is known for its intensity and excitement, making it a favorite among sports enthusiasts worldwide.",
                target_chars=(20, 38),
                messages=[],
                responses=[],
                max_retries=3, # Remember
                success=False
            )
        )

        verify_success(result)
        assert result['max_retries'] < 3  # Some retries used
        assert len(result['responses']) == 3 - result['max_retries']  # Initial + attempts

    class TestPositiveScenarios:

        @pytest.mark.integration
        def test_multi_attempt_expand(self):
            """Tests a scenario where the LLM undershoots the target character range when summarizing."""
            from . import TextMorphGraph, TextMorphState

            result = TextMorphGraph.invoke(
                TextMorphState(
                    model="gpt-4o",
                    text="Augustus here.",
                    target_chars=(41,50),
                    messages=[],
                    responses=[],
                    max_retries=3, # Remember
                    success=False
                )
            )
            
            verify_success(result)
            assert result['max_retries'] < 3  # Some retries used
            assert len(result['responses']) == 3 - result['max_retries']  # Initial + attempts

        @pytest.mark.integration
        def test_already_in_range(self):
            """Tests a scenario where the LLM hits the target character range on the first try."""
            from . import TextMorphGraph, TextMorphState

            result = TextMorphGraph.invoke(
                TextMorphState(
                    model="gpt-4o",
                    text="To be or not to be.",
                    target_chars=(18,20),
                    messages=[],
                    responses=[],
                    max_retries=3, # Remember
                    success=False
                )
            )

            verify_success(result)
            assert len(result["messages"]) == 1 and isinstance(result['messages'][0], SystemMessage)
            assert result['max_retries'] == 3  # No retries used
            assert len(result['responses']) == 1

        @pytest.mark.integration
        def test_difficult_range(self):
            """Tests a scenario where the target character range is very tight."""
            from . import TextMorphGraph, TextMorphState

            result = TextMorphGraph.invoke(
                TextMorphState(
                    model="gpt-4o",
                    text="The quick brown fox jumps over the lazy dog.",
                    target_chars=(72,88),
                    messages=[],
                    responses=[],
                    max_retries=5, # Remember
                    success=False
                )
            )

            verify_success(result)
            assert result['max_retries'] < 5  # Some retries used
            assert len(result['responses']) == 5 - result['max_retries']  # Initial + attempts

    class TestNegativeScenarios:

        @pytest.mark.integration
        def test_invalid_range(self):
            """Tests a scenario where the target character range is invalid (min >= max)."""
            from . import TextMorphGraph, TextMorphState

            with pytest.raises(ValueError) as excinfo:
                TextMorphGraph.invoke(
                    TextMorphState(
                        model="gpt-4o",
                        text="Some text.",
                        target_chars=(50, 30),  # Invalid range
                        messages=[],
                        responses=[],
                        max_retries=2,
                        success=False
                    )
                )
            assert "Invalid:" in str(excinfo.value)

        @pytest.mark.integration
        def test_empty_text(self):
            """Tests a scenario where the input text is empty."""
            from . import TextMorphGraph, TextMorphState

            with pytest.raises(ValueError) as excinfo:
                TextMorphGraph.invoke(
                    TextMorphState(
                        model="gpt-4o",
                        text="   ",  # Empty text
                        target_chars=(10, 20),
                        messages=[],
                        responses=[],
                        max_retries=2,
                        success=False
                    )
                )
            assert "Invalid:" in str(excinfo.value)