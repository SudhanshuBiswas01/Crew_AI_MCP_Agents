"""
CrewAI Agent Definitions
=========================
Three agents:
  1. Researcher  — searches documents and looks up records via MCP tools
  2. Writer      — drafts a sourced markdown report from the evidence
  3. Validator   — checks every claim in the report against retrieved evidence
"""

import os

from crewai import Agent
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME   = os.getenv("MODEL_NAME", "ollama/llama3")
AGENT_MAX_ITER = int(os.getenv("AGENT_MAX_ITER", "10"))


def build_agents(mcp_tools: list) -> tuple[Agent, Agent, Agent]:
    """
    Build and return the three crew agents.

    Args:
        mcp_tools: List of tools returned by MCPServerAdapter (passed at runtime).

    Returns:
        Tuple of (researcher, writer, validator) Agent instances.
    """

    researcher = Agent(
        role="Operations Researcher",
        goal=(
            "Search company documents and records to find accurate, relevant evidence "
            "that answers the given business question. "
            "Always name the source file or record ID for every fact you report."
        ),
        backstory=(
            "You are a meticulous operations analyst with access to the company's knowledge base. "
            "You never guess — if the documents don't contain an answer, you say so clearly."
        ),
        tools=mcp_tools,
        llm=MODEL_NAME,
        max_iter=AGENT_MAX_ITER,
        verbose=True,
    )

    writer = Agent(
        role="Report Writer",
        goal=(
            "Take the evidence gathered by the Researcher and write a clear, concise markdown report. "
            "Every factual claim must cite its source (document name or record ID). "
            "Do not add information that was not in the evidence."
        ),
        backstory=(
            "You are a business analyst who specialises in turning raw research into "
            "clear, actionable reports. You are rigorous about attribution and never hallucinate."
        ),
        tools=mcp_tools,
        llm=MODEL_NAME,
        max_iter=AGENT_MAX_ITER,
        verbose=True,
    )

    validator = Agent(
        role="Claim Validator",
        goal=(
            "Review the drafted report and verify that every claim is supported by the retrieved evidence. "
            "Flag any statement that lacks a citation or contradicts the source material. "
            "Approve the report only when all claims are grounded."
        ),
        backstory=(
            "You are a quality-assurance specialist for AI-generated reports. "
            "Your job is to catch hallucinations before they reach the end user."
        ),
        tools=mcp_tools,
        llm=MODEL_NAME,
        max_iter=AGENT_MAX_ITER,
        verbose=True,
    )

    return researcher, writer, validator
