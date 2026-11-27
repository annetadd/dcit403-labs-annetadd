# AI-Use Log

Add one row every time you use an AI tool for lab work (see Lab Manual Section 4).
Copy the rows for each lab into that lab's report.

| Date | Lab | Tool | What I asked | What I used | What I changed or checked |
|---|---|---|---|---|---|
| 26 Nov 2026 | Lab 2 | Gemini | Help debugging syntax/import errors, Groq `tool_use_failed` errors, and structuring `tools.py`, `react_agent.py`, `concept_check.md`, and the Lab 2 report | Regex parser boundary fix, exponential backoff retry logic, `failed_generation` JSON fallback parser, and outlines for `concept_check.md` and `report.md` | Tested `baseline.py` and `react_agent.py` across all 6 traces (`trace_1.txt`–`trace_6.txt`), verified all arithmetic/Wikipedia outputs, and rewrote concept check answers and report sections in my own words |
| 26 Nov 2026 | Lab 3 | Gemini | Help building `server.py` with FastMCP tools, `client_agent.py` with `tool_calls.jsonl` logging, MCP Inspector steps, and `concept_check.md` | FastMCP tool structure, `stdio_client` + `ClientSession` loop with LiteLLM `acompletion` and JSONL logging, and `concept_check.md` outline | Tested all four tools (`check_stock`, `search_items`, `list_expiring`, `record_sale`) in MCP Inspector, ran the six-question suite, verified `tool_calls.jsonl` and screenshots in `lab03/evidence/`, and adapted answers into my own words |