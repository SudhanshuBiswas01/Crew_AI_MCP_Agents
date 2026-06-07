# Reflection

_Post-project answers — required submission document._

---

### 1. Why these tools and these agent roles, over the alternatives you considered?

<!-- Fill in after completing the project -->
<!-- Hint: Refer to decision_log.md for the pre-build reasoning. Here, reflect on whether those choices held up in practice. -->

**FastMCP** was chosen because its decorator-based API (`@mcp.tool`) made it fast to write and easy to read — each tool is a plain Python function with a docstring that becomes the tool description in the Inspector. The Pydantic validation schemas meant errors were caught before any file I/O, which caught several edge cases during development.

**Three agents (Researcher / Writer / Validator)** matched the real workflow: find evidence, write it up, check the claims. The Validator turned out to be the most valuable agent — it caught [describe an instance here] where the Writer added a claim not present in the retrieved evidence.

---

### 2. What broke first when you connected the crew to the server, and what did you change?

<!-- Fill in with your actual experience -->

**What broke:** <!-- e.g. MCPServerAdapter couldn't find the server process / tool names didn't match / the connection closed before the crew finished -->

**What I changed:** <!-- e.g. Added the `with` context manager to keep the connection alive / fixed the StdioServerParameters command path / set env=None to inherit dotenv variables -->

---

### 3. Show one answer the crew got wrong or ungrounded. How did your guardrail catch it, or why did it slip through?

<!-- Fill in with a real example from your runs -->

**The question asked:** <!-- ... -->

**What the crew said:** <!-- paste the problematic claim here -->

**What the evidence actually said:** <!-- ... -->

**How the Validator responded:** <!-- APPROVED / FLAGGED — and what it flagged -->

**Root cause and fix:** <!-- e.g. the model paraphrased the policy inaccurately / the search_documents query was too broad -->

---

### 4. Where is the biggest security risk in your server, and how did you reduce it?

**Risk:** The `search_documents` tool accepts a user-supplied query string that is used in a regex search across the file system. A malicious agent (or prompt-injected input) could supply a crafted regex that causes catastrophic backtracking (ReDoS), or a path-like string designed to escape the `docs/` directory.

**Mitigations applied:**
- `re.escape()` wraps every query before compilation — disabling regex metacharacters.
- Pydantic `Field(max_length=500)` caps query length.
- `DOCS_DIR` is resolved to an absolute path at startup; only `.txt` and `.md` files in that directory are ever opened.
- File paths are never constructed from user input.

**Remaining risk:** A very long query (up to 500 chars) could still be slow on large document sets. A production hardening step would add a timeout on the file-read loop.

---

### 5. What would you change before letting this touch real company data?

1. **Authentication on the MCP server** — even stdio transport should verify the calling process is the expected crew, not an arbitrary local script.
2. **Audit logging** — every tool call should be written to an append-only log with timestamps, the caller identity, and the full input/output. Currently only the crew trace is saved.
3. **Data encryption at rest** — `docs/` and `inventory_orders.csv` should be encrypted if they contain sensitive information.
4. **Human-in-the-loop approval** before `save_report` writes anything — adds a confirmation step so a person reviews the report before it is persisted.
5. **Prompt-injection testing** — hide adversarial instructions in one document and verify the server's guardrails refuse them before going live.
6. **Rate limiting** — limit how many tool calls the crew can make per session to prevent runaway costs if a remote model is used.
