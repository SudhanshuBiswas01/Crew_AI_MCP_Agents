"""
CrewAI Task Definitions
========================
Three tasks, one per agent:
  1. research_task  — gather evidence from documents and records
  2. write_task     — produce a sourced markdown report
  3. validate_task  — verify every claim and approve or flag the report
"""

from crewai import Task


def build_tasks(researcher, writer, validator, question: str) -> tuple:
    """
    Build and return the three crew tasks for a given business question.

    Args:
        researcher: The Researcher Agent instance.
        writer:     The Writer Agent instance.
        validator:  The Validator Agent instance.
        question:   The business question to answer.

    Returns:
        Tuple of (research_task, write_task, validate_task).
    """

    research_task = Task(
        description=(
            f"Answer the following business question by searching the company documents "
            f"and records:\n\n  QUESTION: {question}\n\n"
            "Steps:\n"
            "1. Call search_documents() with relevant keywords.\n"
            "2. For any record IDs mentioned, call read_record() to get the full row.\n"
            "3. Compile a structured list of findings. For each finding, state:\n"
            "   - The fact\n"
            "   - The source (filename or record ID)\n"
            "4. If no relevant information is found, state that explicitly — do NOT invent an answer."
        ),
        expected_output=(
            "A bullet-pointed evidence list. Each bullet must include the fact and its source. "
            "Example:\n"
            "- Order #42 was fulfilled on 2024-03-15. [Source: records.csv, id=42]\n"
            "- The return policy allows 30 days. [Source: return_policy.txt]"
        ),
        agent=researcher,
    )

    write_task = Task(
        description=(
            "Using ONLY the evidence list from the Researcher, write a professional markdown report "
            "that answers the original business question.\n\n"
            "Requirements:\n"
            "- Start with a one-paragraph executive summary.\n"
            "- Use sections with headings for each theme.\n"
            "- Every factual sentence must end with a citation in brackets, e.g. [Source: filename].\n"
            "- End with a 'Limitations' section noting anything the evidence did not cover.\n"
            "- Call save_report() with the title and your markdown content to persist the report."
        ),
        expected_output=(
            "A complete markdown report saved to the output/ folder via save_report(). "
            "The tool call result (saved file path) should be included in the output."
        ),
        agent=writer,
        context=[research_task],
    )

    validate_task = Task(
        description=(
            "Review the report written by the Writer against the Researcher's evidence list.\n\n"
            "For each factual claim in the report:\n"
            "1. Check that a citation is present.\n"
            "2. Verify the citation matches actual evidence from the Researcher's output.\n"
            "3. Flag any claim that is unsupported, missing a citation, or contradicts the source.\n\n"
            "Output a validation summary: APPROVED if all claims are grounded, "
            "or FLAGGED with a list of specific issues if not."
        ),
        expected_output=(
            "A validation summary: either 'APPROVED — all claims are grounded.' "
            "or 'FLAGGED — <list of specific issues with claim text and why it is ungrounded>'."
        ),
        agent=validator,
        context=[research_task, write_task],
    )

    return research_task, write_task, validate_task
