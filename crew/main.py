"""
CrewAI Crew Entry Point
========================
Connects the CrewAI crew to the MCP server via MCPServerAdapter (stdio),
runs the full research → write → validate pipeline, and saves a trace.

Usage:
    uv run python crew/main.py
    uv run python crew/main.py --question "What is our return policy?"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from crewai import Crew, Process
from crewai_tools import MCPServerAdapter
from crewai.utilities import Logger
from dotenv import load_dotenv
from mcp import StdioServerParameters

# Add project root to path so relative imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
from crew.agents import build_agents
from crew.tasks  import build_tasks

load_dotenv()

TRACES_DIR   = Path(os.getenv("TRACES_DIR",   "./traces")).resolve()
CREW_VERBOSE = os.getenv("CREW_VERBOSE", "true").lower() == "true"
TRACES_DIR.mkdir(parents=True, exist_ok=True)

# ── MCP server parameters ─────────────────────────────────────────────────────
SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=[str(Path(__file__).parent.parent / "server" / "server.py")],
    env=None,  # inherits the current environment (including .env variables)
)


def run_crew(question: str) -> dict:
    """
    Run the full ops-assistant crew for a given question.

    Args:
        question: The business question to answer.

    Returns:
        Dict with 'result' (crew output) and 'trace_file' (path of saved trace).
    """
    print(f"\n{'='*60}")
    print(f"  Operations Assistant — CrewAI + MCP")
    print(f"  Question: {question}")
    print(f"{'='*60}\n")

    # Connect to MCP server and get its tools
    with MCPServerAdapter(SERVER_PARAMS) as mcp_tools:
        print(f"[INFO] MCP tools loaded: {[t.name for t in mcp_tools]}\n")

        # Build agents and tasks
        researcher, writer, validator = build_agents(mcp_tools)
        research_task, write_task, validate_task = build_tasks(
            researcher, writer, validator, question
        )

        # Assemble crew
        crew = Crew(
            agents=[researcher, writer, validator],
            tasks=[research_task, write_task, validate_task],
            process=Process.sequential,
            verbose=CREW_VERBOSE,
        )

        # Run
        start_time = datetime.utcnow()
        result = crew.kickoff()
        end_time = datetime.utcnow()

    # Save trace
    trace = {
        "question": question,
        "started_at":  start_time.isoformat() + "Z",
        "finished_at": end_time.isoformat() + "Z",
        "duration_seconds": (end_time - start_time).total_seconds(),
        "result": str(result),
        "research_output": str(research_task.output.raw if research_task.output else ""),
        "write_output": str(write_task.output.raw if write_task.output else ""),
        "validate_output": str(validate_task.output.raw if validate_task.output else ""),
    }
    ts = start_time.strftime("%Y%m%d_%H%M%S")
    trace_file = TRACES_DIR / f"trace_{ts}.json"
    trace_file.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[INFO] Trace saved to: {trace_file}")

    return {
        "result": result,
        "trace_file": str(trace_file),
        "research_output": trace["research_output"],
        "write_output": trace["write_output"],
        "validate_output": trace["validate_output"]
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    """Entry point for the `ops-crew` console script defined in pyproject.toml."""
    parser = argparse.ArgumentParser(description="Run the Operations Assistant crew.")
    parser.add_argument(
        "--question",
        default="What is the current status of our top 3 orders and what does our return policy say?",
        help="The business question for the crew to answer.",
    )
    args = parser.parse_args()

    output = run_crew(args.question)
    print("\n" + "="*60)
    print("CREW RESULT:")
    print("="*60)
    print(output["result"])


if __name__ == "__main__":
    main()
