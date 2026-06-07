# Decision Log

_What I tried, what I chose, and what I rejected — with reasons._

---

## Transport: stdio vs SSE/HTTP

**Chose:** stdio (default)

**Why:** stdio requires zero infrastructure — the MCP server runs as a subprocess of the crew script. No ports, no auth, no process management. Perfect for a laptop-runnable project.

**Rejected:** SSE/HTTP — adds real value for multi-client scenarios or remote deployment, but is overkill for a single-crew local project. Kept as a stretch goal.

---

## Model: Ollama (local) vs OpenAI API

**Chose:** Ollama with `llama3` (or `mistral`)

**Why:** Free, fully local, no key required, reproducible from a fresh clone on any machine. The project requirement explicitly says "do not require a paid API."

**Rejected:** `gpt-4o` / `gpt-4o-mini` — would require a paid key and make the project non-reproducible for reviewers without billing set up.

---

## MCP SDK: FastMCP vs low-level `mcp` Server class

**Chose:** FastMCP (`from mcp.server.fastmcp import FastMCP`)

**Why:** Decorator-based API (`@mcp.tool()`, `@mcp.resource()`) is concise and readable. Input validation integrates naturally with Pydantic models. Official SDK, actively maintained.

**Rejected:** Raw `mcp.Server` class — more verbose boilerplate for the same result. Useful for advanced routing, not needed here.

---

## Input validation: Pydantic models vs manual checks

**Chose:** Pydantic `BaseModel` with `Field` constraints on every tool

**Why:** Raises a clear `ValidationError` before any file I/O or data access happens. Forces schema documentation. Follows the project's "treat every tool input as untrusted" safety rule.

**Rejected:** Manual `if/else` checks — error-prone, harder to read, no automatic schema introspection for the Inspector.

---

## Agent count: 2 vs 3

**Chose:** 3 agents (Researcher, Writer, Validator)

**Why:** The Validator is the key safety mechanism — it catches hallucinations before the report is finalised. Two-agent crews (Researcher + Writer only) pass the MVP bar but skip a critical grounding check.

**Rejected:** 2 agents — meets MVP, but leaves claims unverified. The Validator adds ~10 lines of code for a significant reliability gain.

---

## Process type: sequential vs hierarchical

**Chose:** `Process.sequential`

**Why:** Tasks have a natural linear dependency: research → write → validate. Sequential is easier to trace and debug. Each agent's `context` list makes the dependency explicit.

**Rejected:** `Process.hierarchical` — useful when a planner needs to dynamically assign tasks. Overkill here since the task order is fixed. Kept as a stretch goal.

---

## Loop control: `max_iter` setting

**Chose:** `max_iter=10` per agent (configurable via `AGENT_MAX_ITER` env var)

**Why:** Prevents runaway loops if a tool returns unexpected output or the model gets stuck retrying. 10 iterations is generous for simple retrieval tasks.

**Considered:** `max_iter=5` — too tight for multi-step retrieval tasks where the agent may need several tool calls. `max_iter=20` — too loose; a stuck agent wastes time and tokens.
