"""
End-to-End Test — Crew on a Fixed Question
============================================
Runs the full crew pipeline against the sample data in docs/ and data/.
This test requires:
  - A running Ollama instance (or configured model) accessible via env vars
  - The sample data files to exist

Skip this test in CI unless a model is available:
    uv run pytest tests/test_crew_e2e.py -v -m e2e

Run it locally:
    uv run pytest tests/test_crew_e2e.py -v
"""

import json
from pathlib import Path

import pytest

# Mark all tests in this file as e2e
pytestmark = pytest.mark.e2e

FIXED_QUESTION = "What is our return policy and are there any pending orders?"


@pytest.fixture(scope="module")
def crew_result():
    """Run the crew once for the module and return the result dict."""
    # Import lazily so unit tests don't fail if crewai isn't installed
    from crew.main import run_crew
    return run_crew(FIXED_QUESTION)


class TestCrewE2E:
    def test_crew_returns_result(self, crew_result):
        """Crew must return a non-empty result."""
        assert crew_result is not None
        assert str(crew_result["result"]).strip() != ""

    def test_trace_file_created(self, crew_result):
        """A trace JSON file must be saved after each run."""
        trace_path = Path(crew_result["trace_file"])
        assert trace_path.exists(), f"Trace file not found: {trace_path}"

    def test_trace_contains_required_fields(self, crew_result):
        """Trace file must contain question, timestamps, and result."""
        trace_path = Path(crew_result["trace_file"])
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        assert "question"         in trace
        assert "started_at"       in trace
        assert "finished_at"      in trace
        assert "duration_seconds" in trace
        assert "result"           in trace

    def test_result_contains_citation(self, crew_result):
        """Final output must contain at least one [Source: ...] citation."""
        result_text = str(crew_result["result"]).lower()
        assert "source" in result_text, (
            "Expected at least one citation '[Source: ...]' in the crew output."
        )

    def test_output_report_saved(self):
        """save_report() should have written a .md file to output/."""
        output_dir = Path("./output").resolve()
        if not output_dir.exists():
            pytest.skip("output/ directory does not exist yet.")
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) >= 1, "Expected at least one .md report in output/"
