"""
MCP Operations Assistant Server
================================
FastMCP server exposing three tools over local data:
  - search_documents(query)   → full-text search across docs/
  - read_record(id)           → look up a row in records.csv by ID
  - save_report(title, body)  → write a markdown report to output/

Run directly:
    uv run python server/server.py

Test in MCP Inspector:
    npx @modelcontextprotocol/inspector uv run python server/server.py
"""

import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

DOCS_DIR   = Path(os.getenv("DOCS_DIR",   "./docs")).resolve()
RECORDS_CSV = Path(os.getenv("RECORDS_CSV", "./data/inventory_orders.csv")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="ops-assistant",
    instructions="Operations Assistant MCP server — search docs and records, save reports.",
)


# ── Input schemas ─────────────────────────────────────────────────────────────
class SearchInput(BaseModel):
    query: str = Field("", max_length=500, description="Search query string")
    max_results: Optional[int] = Field(5, description="Maximum number of results to return (1-20)")

    def get_max_results(self) -> int:
        if self.max_results is None or self.max_results <= 0:
            return 5
        return min(20, self.max_results)


class ReadRecordInput(BaseModel):
    record_id: str = Field(..., min_length=1, max_length=100, description="Record ID to look up")


class SaveReportInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Report title")
    content: str = Field(..., min_length=1, description="Markdown content of the report")


# ── Tool: search_documents ────────────────────────────────────────────────────
@mcp.tool()
def search_documents(query: str, max_results: Optional[int] = 5) -> str:
    """
    Search across all documents in the docs/ folder using simple keyword matching.
    Returns matching excerpts with the source file name for citation.

    Args:
        query: The search query string.
        max_results: Maximum number of matching snippets to return (1–20).

    Returns:
        JSON string with a list of {source, excerpt} dicts, or an error message.
    """
    if not query or not query.strip():
        raise ValueError("query must not be empty")

    # Validate inputs
    validated = SearchInput(query=query, max_results=max_results)

    if not DOCS_DIR.exists():
        return json.dumps({"error": f"Documents directory not found: {DOCS_DIR}"})

    doc_files = list(DOCS_DIR.glob("*.txt")) + list(DOCS_DIR.glob("*.md"))
    if not doc_files:
        return json.dumps({"error": "No documents found in docs/ folder."})

    # Split query into words to allow simple token matching rather than exact phrase matches
    words = [w.strip(".,!?\"'") for w in validated.query.lower().split()]
    words = [w for w in words if len(w) > 2 and w not in {"the", "and", "for", "our", "what", "how", "with", "this", "that"}]
    if not words:
        # Fallback to the whole string if it's too short or contains only stopwords
        words = [validated.query.lower()] if validated.query.strip() else ["policy", "shipping", "return"]

    results = []
    max_limit = validated.get_max_results()

    for filepath in sorted(doc_files):
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception as exc:
            continue

        text_lower = text.lower()
        # Find matches for any of the keywords
        matched_positions = []
        for word in words:
            for m in re.finditer(re.escape(word), text_lower):
                matched_positions.append(m.start())

        # Sort and deduplicate match positions that are close to each other
        matched_positions = sorted(list(set(matched_positions)))
        last_end = -1
        for pos in matched_positions:
            if pos < last_end:
                continue
            start = max(0, pos - 100)
            end = min(len(text), pos + 200)
            excerpt = text[start:end].strip().replace("\n", " ")
            results.append({"source": filepath.name, "excerpt": excerpt})
            last_end = end
            if len(results) >= max_limit:
                break
        if len(results) >= max_limit:
            break

    if not results:
        return json.dumps({"results": [], "message": f"No documents matched '{validated.query}'."})

    return json.dumps({"results": results, "total_found": len(results)}, ensure_ascii=False)


# ── Tool: read_record ─────────────────────────────────────────────────────────
@mcp.tool()
def read_record(record_id: str) -> str:
    """
    Look up a single row in records.csv by its ID column.
    Returns the full row as a JSON object, citing the CSV as its source.

    Args:
        record_id: The value of the 'id' column to look up.

    Returns:
        JSON string with {source, record} dict, or an error message.
    """
    # Validate input
    validated = ReadRecordInput(record_id=record_id.strip())

    if not RECORDS_CSV.exists():
        return json.dumps({"error": f"Records CSV not found: {RECORDS_CSV}"})

    try:
        with RECORDS_CSV.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            id_col = "id" if "id" in fields else ("order_id" if "order_id" in fields else None)
            if not id_col:
                return json.dumps({"error": "CSV does not have an 'id' or 'order_id' column."})
            for row in reader:
                if row.get(id_col, "").strip() == validated.record_id:
                    return json.dumps(
                        {"source": RECORDS_CSV.name, "record": dict(row)},
                        ensure_ascii=False,
                    )
    except Exception as exc:
        return json.dumps({"error": f"Failed to read CSV: {exc}"})

    return json.dumps({"error": f"No record found with id='{validated.record_id}'."})


# ── Tool: save_report ─────────────────────────────────────────────────────────
@mcp.tool()
def save_report(title: str, content: str) -> str:
    """
    Save a sourced markdown report to the output/ folder.
    The filename is derived from the title and a UTC timestamp.

    Args:
        title:   Report title (used as the filename slug).
        content: Full markdown content of the report.

    Returns:
        JSON string with the saved file path, or an error message.
    """
    # Validate inputs
    validated = SaveReportInput(title=title, content=content)

    slug = re.sub(r"[^\w\-]", "_", validated.title.lower())[:80]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{slug}_{timestamp}.md"
    filepath = OUTPUT_DIR / filename

    try:
        full_content = f"# {validated.title}\n\n_Generated: {datetime.utcnow().isoformat()}Z_\n\n{validated.content}"
        filepath.write_text(full_content, encoding="utf-8")
    except Exception as exc:
        return json.dumps({"error": f"Failed to write report: {exc}"})

    return json.dumps({"saved_to": str(filepath), "filename": filename})


# ── Resource: list documents ──────────────────────────────────────────────────
@mcp.resource("docs://list")
def list_documents() -> str:
    """List all available documents in the docs/ folder."""
    if not DOCS_DIR.exists():
        return "Documents directory not found."
    files = sorted(
        [f.name for f in DOCS_DIR.iterdir() if f.suffix in (".txt", ".md")]
    )
    if not files:
        return "No documents available."
    return "\n".join(f"- {name}" for name in files)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    """Entry point for the `ops-server` console script defined in pyproject.toml."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
