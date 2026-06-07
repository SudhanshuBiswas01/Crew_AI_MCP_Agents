"""
Unit Tests — MCP Tools
=======================
Tests call the MCP tool functions directly (not through the server transport)
to verify correct behaviour, input validation, and error handling.

Run:
    uv run pytest tests/test_tools.py -v
"""

import csv
import json
import os
import tempfile
from pathlib import Path

import pytest

# Point server at temporary dirs so tests are isolated
os.environ["DOCS_DIR"]    = ""   # will be overridden per test via monkeypatch
os.environ["RECORDS_CSV"] = ""
os.environ["OUTPUT_DIR"]  = ""

# Import after env is set
from server.server import search_documents, read_record, save_report


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_docs(tmp_path, monkeypatch):
    """Create a temporary docs/ folder with two text files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "return_policy.txt").write_text(
        "Our return policy allows customers to return items within 30 days of purchase.",
        encoding="utf-8",
    )
    (docs_dir / "shipping_info.txt").write_text(
        "Standard shipping takes 5-7 business days. Express shipping is 1-2 days.",
        encoding="utf-8",
    )
    import server.server as srv
    monkeypatch.setattr(srv, "DOCS_DIR", docs_dir)
    return docs_dir


@pytest.fixture()
def tmp_records(tmp_path, monkeypatch):
    """Create a temporary records.csv with three rows."""
    csv_file = tmp_path / "records.csv"
    rows = [
        {"id": "1", "product": "Widget A", "status": "fulfilled",  "amount": "99.99"},
        {"id": "2", "product": "Widget B", "status": "pending",    "amount": "49.50"},
        {"id": "3", "product": "Widget C", "status": "cancelled",  "amount": "19.00"},
    ]
    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    import server.server as srv
    monkeypatch.setattr(srv, "RECORDS_CSV", csv_file)
    return csv_file


@pytest.fixture()
def tmp_output(tmp_path, monkeypatch):
    """Create a temporary output/ folder."""
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    import server.server as srv
    monkeypatch.setattr(srv, "OUTPUT_DIR", out_dir)
    return out_dir


# ── search_documents tests ────────────────────────────────────────────────────

class TestSearchDocuments:
    def test_finds_matching_document(self, tmp_docs):
        result = json.loads(search_documents("return policy"))
        assert "results" in result
        assert len(result["results"]) >= 1
        assert any("return_policy.txt" in r["source"] for r in result["results"])

    def test_returns_empty_when_no_match(self, tmp_docs):
        result = json.loads(search_documents("zzz_nonexistent_term_zzz"))
        assert result["results"] == []

    def test_excerpt_contains_query_context(self, tmp_docs):
        result = json.loads(search_documents("shipping"))
        assert any("shipping" in r["excerpt"].lower() for r in result["results"])

    def test_respects_max_results(self, tmp_docs):
        result = json.loads(search_documents("shipping", max_results=1))
        assert len(result.get("results", [])) <= 1

    def test_missing_docs_dir_returns_error(self, monkeypatch):
        import server.server as srv
        monkeypatch.setattr(srv, "DOCS_DIR", Path("/nonexistent/path"))
        result = json.loads(search_documents("anything"))
        assert "error" in result

    def test_empty_query_raises(self):
        with pytest.raises(Exception):
            search_documents("")


# ── read_record tests ─────────────────────────────────────────────────────────

class TestReadRecord:
    def test_finds_existing_record(self, tmp_records):
        result = json.loads(read_record("1"))
        assert "record" in result
        assert result["record"]["product"] == "Widget A"

    def test_returns_error_for_missing_id(self, tmp_records):
        result = json.loads(read_record("999"))
        assert "error" in result

    def test_cites_source_file(self, tmp_records):
        result = json.loads(read_record("2"))
        assert "source" in result
        assert "records.csv" in result["source"]

    def test_missing_csv_returns_error(self, monkeypatch):
        import server.server as srv
        monkeypatch.setattr(srv, "RECORDS_CSV", Path("/nonexistent/records.csv"))
        result = json.loads(read_record("1"))
        assert "error" in result

    def test_empty_id_raises(self):
        with pytest.raises(Exception):
            read_record("")


# ── save_report tests ─────────────────────────────────────────────────────────

class TestSaveReport:
    def test_saves_file_to_output_dir(self, tmp_output):
        result = json.loads(save_report("Test Report", "## Summary\nAll good."))
        assert "saved_to" in result
        saved = Path(result["saved_to"])
        assert saved.exists()
        assert saved.parent == tmp_output

    def test_saved_file_contains_title_and_content(self, tmp_output):
        save_report("My Report", "## Details\nSome details here.")
        files = list(tmp_output.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "My Report" in content
        assert "Some details here." in content

    def test_filename_slug_derived_from_title(self, tmp_output):
        result = json.loads(save_report("Order Status Q1", "content"))
        assert "order_status_q1" in result["filename"]

    def test_empty_title_raises(self, tmp_output):
        with pytest.raises(Exception):
            save_report("", "content")

    def test_empty_content_raises(self, tmp_output):
        with pytest.raises(Exception):
            save_report("Title", "")
