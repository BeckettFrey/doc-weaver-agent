import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from doc_weaver.hydrate_queue import HydrateQueue, HydrationTask, PLACEHOLDER_PATTERN, hydrate


SAMPLE_MD = """# John Doe - Software Engineer

> Experienced engineer building great software.

## Experience
### Work Experience
- Lead engineer at TechCorp
- <1, 20, 100>
- <1, 10, 50>

## Skills
### Technical Skills
- <2, 5, 30>

### Soft Skills
- <3, 10, 60>"""


class TestHydrationTask:

    def test_creation(self):
        task = HydrationTask(batch=1, min_chars=10, max_chars=50, raw="<1, 10, 50>", marker="<<TASK_0>>")
        assert task.batch == 1
        assert task.min_chars == 10
        assert task.max_chars == 50
        assert task.raw == "<1, 10, 50>"
        assert task.marker == "<<TASK_0>>"


class TestPlaceholderPattern:

    def test_matches_basic(self):
        assert PLACEHOLDER_PATTERN.search("<1, 20, 100>") is not None

    def test_matches_no_spaces(self):
        assert PLACEHOLDER_PATTERN.search("<1,20,100>") is not None

    def test_no_match_on_todo(self):
        assert PLACEHOLDER_PATTERN.search("<TODO>") is None

    def test_finds_all_in_document(self):
        matches = PLACEHOLDER_PATTERN.findall(SAMPLE_MD)
        assert len(matches) == 4


class TestHydrateQueue:

    def test_parses_tasks(self):
        queue = HydrateQueue(SAMPLE_MD)
        assert len(queue._tasks) == 4

    def test_batch_ordering(self):
        queue = HydrateQueue(SAMPLE_MD)
        assert queue._batch_numbers == [1, 2, 3]

    def test_not_done_initially(self):
        queue = HydrateQueue(SAMPLE_MD)
        assert not queue.done
        assert queue.current_batch_number == 1

    def test_first_batch_has_two_items(self):
        queue = HydrateQueue(SAMPLE_MD)
        batch = queue.next_batch()
        assert len(batch) == 2

    def test_batch_items_have_correct_bounds(self):
        queue = HydrateQueue(SAMPLE_MD)
        batch = queue.next_batch()
        _, min1, max1, _ = batch[0]
        _, min2, max2, _ = batch[1]
        assert (min1, max1) == (20, 100)
        assert (min2, max2) == (10, 50)

    def test_batch_documents_contain_todo(self):
        queue = HydrateQueue(SAMPLE_MD)
        batch = queue.next_batch()
        for doc, _, _, _ in batch:
            preview = doc.preview()
            assert "<TODO>" in preview
            assert preview.count("<TODO>") == 1

    def test_batch_documents_replace_others_with_placeholder(self):
        queue = HydrateQueue(SAMPLE_MD)
        batch = queue.next_batch()
        for doc, _, _, _ in batch:
            preview = doc.preview()
            assert "(will be filled later)" in preview
            assert PLACEHOLDER_PATTERN.search(preview) is None

    def test_submit_advances_batch(self):
        queue = HydrateQueue(SAMPLE_MD)
        _ = queue.next_batch()
        queue.submit_results(["Built REST APIs", "Led team of 5"])
        assert queue.current_batch_number == 2

    def test_submit_updates_markdown(self):
        queue = HydrateQueue(SAMPLE_MD)
        _ = queue.next_batch()
        queue.submit_results(["Built REST APIs", "Led team of 5"])
        md = queue.current_markdown
        assert "Built REST APIs" in md
        assert "Led team of 5" in md
        assert "<1, 20, 100>" not in md
        assert "<1, 10, 50>" not in md

    def test_second_batch_sees_previous_results(self):
        queue = HydrateQueue(SAMPLE_MD)
        _ = queue.next_batch()
        queue.submit_results(["Built REST APIs", "Led team of 5"])
        batch2 = queue.next_batch()
        assert len(batch2) == 1
        doc, min_c, max_c, _ = batch2[0]
        preview = doc.preview()
        assert "Built REST APIs" in preview
        assert "Led team of 5" in preview
        assert "<TODO>" in preview
        assert (min_c, max_c) == (5, 30)

    def test_full_run(self):
        queue = HydrateQueue(SAMPLE_MD)

        # Batch 1
        batch = queue.next_batch()
        assert len(batch) == 2
        queue.submit_results(["Built REST APIs", "Led team of 5"])

        # Batch 2
        batch = queue.next_batch()
        assert len(batch) == 1
        queue.submit_results(["Python, Go"])

        # Batch 3
        batch = queue.next_batch()
        assert len(batch) == 1
        queue.submit_results(["Strong communicator"])

        assert queue.done
        md = queue.current_markdown
        assert "Built REST APIs" in md
        assert "Led team of 5" in md
        assert "Python, Go" in md
        assert "Strong communicator" in md
        assert PLACEHOLDER_PATTERN.search(md) is None

    def test_submit_wrong_count_raises(self):
        queue = HydrateQueue(SAMPLE_MD)
        _ = queue.next_batch()
        try:
            queue.submit_results(["only one"])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Expected 2" in str(e)

    def test_each_task_gets_unique_marker(self):
        queue = HydrateQueue(SAMPLE_MD)
        markers = [t.marker for t in queue._tasks]
        assert len(markers) == len(set(markers))

    def test_duplicate_placeholders_resolved_independently(self):
        """Two identical <1, 20, 100> placeholders should each get their own result."""
        md = """# Test Doc

> A tagline.

## Section
### Sub
- <1, 20, 100>
- <1, 20, 100>"""

        queue = HydrateQueue(md)
        assert len(queue._tasks) == 2
        assert queue._tasks[0].marker != queue._tasks[1].marker

        batch = queue.next_batch()
        assert len(batch) == 2

        # Each document should have exactly one <TODO>
        for doc, _, _, _ in batch:
            preview = doc.preview()
            assert preview.count("<TODO>") == 1

        queue.submit_results(["First result here!!", "Second result here!"])
        md = queue.current_markdown
        assert "First result here!!" in md
        assert "Second result here!" in md
        assert queue.done

    def test_duplicate_placeholders_full_run(self):
        """Duplicate placeholders across different batches."""
        md = """# Test Doc

> A tagline.

## Section
### Sub
- <1, 10, 50>
- <1, 10, 50>
- <2, 10, 50>"""

        queue = HydrateQueue(md)
        assert len(queue._tasks) == 3

        # Batch 1: two identical placeholders
        batch = queue.next_batch()
        assert len(batch) == 2
        queue.submit_results(["Result AAA!!", "Result BBB!!"])

        # Batch 2: should see both batch 1 results
        batch = queue.next_batch()
        assert len(batch) == 1
        doc, _, _, _ = batch[0]
        preview = doc.preview()
        assert "Result AAA!!" in preview
        assert "Result BBB!!" in preview
        queue.submit_results(["Result CCC!!"])

        assert queue.done
        md = queue.current_markdown
        assert "Result AAA!!" in md
        assert "Result BBB!!" in md
        assert "Result CCC!!" in md

    def test_next_batch_when_done_raises(self):
        queue = HydrateQueue(SAMPLE_MD)
        queue.next_batch()
        queue.submit_results(["a" * 20, "b" * 10])
        queue.next_batch()
        queue.submit_results(["c" * 5])
        queue.next_batch()
        queue.submit_results(["d" * 10])
        assert queue.done
        try:
            queue.next_batch()
            assert False, "Should have raised StopIteration"
        except StopIteration:
            pass

    def test_current_batch_number_none_when_done(self):
        queue = HydrateQueue(SAMPLE_MD)
        queue.next_batch()
        queue.submit_results(["a" * 20, "b" * 10])
        queue.next_batch()
        queue.submit_results(["c" * 5])
        queue.next_batch()
        queue.submit_results(["d" * 10])
        assert queue.done
        assert queue.current_batch_number is None

    def test_submit_results_when_done_raises(self):
        queue = HydrateQueue(SAMPLE_MD)
        queue.next_batch()
        queue.submit_results(["a" * 20, "b" * 10])
        queue.next_batch()
        queue.submit_results(["c" * 5])
        queue.next_batch()
        queue.submit_results(["d" * 10])
        assert queue.done
        try:
            queue.submit_results(["extra"])
            assert False, "Should have raised StopIteration"
        except StopIteration:
            pass


class TestHydrate:

    @pytest.mark.asyncio
    async def test_full_hydration(self):
        results = iter(["Built REST APIs", "Led team of 5", "Python, Go", "Strong communicator"])

        async def mock_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            text = next(results)
            return text, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=mock_hydrate_item):
            result, metadata = await hydrate(SAMPLE_MD)

        assert "Built REST APIs" in result
        assert "Led team of 5" in result
        assert "Python, Go" in result
        assert "Strong communicator" in result
        assert PLACEHOLDER_PATTERN.search(result) is None

    @pytest.mark.asyncio
    async def test_passes_context_to_hydrate_item(self):
        calls = []

        async def mock_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            calls.append(context)
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=mock_hydrate_item):
            await hydrate(SAMPLE_MD, context="Write for a senior role")

        assert all(c == "Write for a senior role" for c in calls)

    @pytest.mark.asyncio
    async def test_batches_run_sequentially(self):
        """Earlier batch results should appear in later batch documents."""
        seen_previews = []

        async def mock_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            seen_previews.append(doc.preview())
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=mock_hydrate_item):
            await hydrate(SAMPLE_MD)

        # Batch 2 and 3 previews should contain results from batch 1
        # Batch 1 has 2 items, batch 2 has 1, batch 3 has 1
        batch2_preview = seen_previews[2]
        assert "x" * 20 in batch2_preview  # result from batch 1 item 1
        assert "x" * 10 in batch2_preview  # result from batch 1 item 2

    @pytest.mark.asyncio
    async def test_timeout_raises_on_slow_batch(self):
        async def slow_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            await asyncio.sleep(10)
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=slow_hydrate_item):
            with pytest.raises(asyncio.TimeoutError):
                await hydrate(SAMPLE_MD, timeout=0.01)

    @pytest.mark.asyncio
    async def test_no_timeout_when_batch_completes_quickly(self):
        async def fast_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=fast_hydrate_item):
            result, metadata = await hydrate(SAMPLE_MD, timeout=10)

        assert PLACEHOLDER_PATTERN.search(result) is None

    @pytest.mark.asyncio
    async def test_concurrent_items_in_same_batch(self):
        """Items within a batch should run concurrently, not sequentially."""
        call_times = []

        async def tracking_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.05)
            end = asyncio.get_event_loop().time()
            call_times.append((start, end))
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=tracking_hydrate_item):
            await hydrate(SAMPLE_MD, timeout=5)

        # Batch 1 has 2 items — they should overlap in time
        t1_start, t1_end = call_times[0]
        t2_start, t2_end = call_times[1]
        assert t2_start < t1_end  # second task started before first finished

    @pytest.mark.asyncio
    async def test_passes_model_to_hydrate_item(self):
        models_seen = []

        async def mock_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            models_seen.append(model)
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=mock_hydrate_item):
            await hydrate(SAMPLE_MD, model="gpt-4o-mini")

        assert all(m == "gpt-4o-mini" for m in models_seen)

    @pytest.mark.asyncio
    async def test_default_model_is_gpt4o(self):
        models_seen = []

        async def mock_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            models_seen.append(model)
            return "x" * min_c, 1.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=mock_hydrate_item):
            await hydrate(SAMPLE_MD)

        assert all(m == "gpt-4o" for m in models_seen)

    @pytest.mark.asyncio
    async def test_missing_context_raises(self):
        """Hydrate should raise ValueError when a placeholder references a missing context."""
        md = """# Test Doc

> A tagline.

## Section
### Sub
- <1, 10, 50, myctx>"""

        with pytest.raises(ValueError, match="Missing context"):
            await hydrate(md, contexts={})

    @pytest.mark.asyncio
    async def test_metadata_structure(self):
        """Hydrate should return metadata with per-task info and totals."""
        async def mock_hydrate_item(doc, min_c, max_c, context="", model="gpt-4o", task_context=""):
            return "x" * min_c, 42.0

        with patch("doc_weaver.hydrate_queue.hydrate_item", side_effect=mock_hydrate_item):
            result, metadata = await hydrate(SAMPLE_MD, model="gpt-4o-mini")

        assert "tasks" in metadata
        assert "total_elapsed_ms" in metadata
        assert "model" in metadata
        assert "marker_document" in metadata
        assert metadata["model"] == "gpt-4o-mini"
        assert len(metadata["tasks"]) == 4

        for i, task in enumerate(metadata["tasks"]):
            assert task["task_number"] == i
            assert "marker" in task
            assert "<<TASK_" in task["marker"]
            assert "batch_num" in task
            assert "char_range" in task
            assert "total_chars" in task
            assert "elapsed_ms" in task
            assert "model" in task
