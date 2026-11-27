import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from dotenv import load_dotenv
from litellm import acompletion
import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(override=True)
litellm.drop_params = True

MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")
BASE_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = str(BASE_DIR / "server.py")
LOG_PATH = BASE_DIR / "evidence" / "tool_calls.jsonl"

SYSTEM_PROMPT = """You are a helpful community pharmacy assistant.
Use the available pharmacy inventory tools to look up stock, search items, check expiring stock, and record sales.
Never guess stock counts, prices, or expiry dates when a tool can check them.
When recording a sale, check availability if needed and clearly report whether the sale was recorded or refused and why."""


def _summarize_result(text: str, max_len: int = 180) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= max_len else compact[: max_len - 3] + "..."


def _log_tool_call(
    tool_name: str,
    arguments: dict,
    summary: str,
    duration_ms: float,
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "arguments": arguments,
        "summary": summary,
        "duration_ms": round(duration_ms, 2),
    }
    with open(LOG_PATH, mode="a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _extract_mcp_text(call_result) -> str:
    parts = []
    for block in getattr(call_result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(block))
    if getattr(call_result, "isError", False):
        return f"MCP Tool Error: {' '.join(parts)}"
    return "\n".join(parts) if parts else "[]"


async def ask_agent(session: ClientSession, schemas: list[dict], question: str, max_steps: int = 6) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(max_steps):
        resp = await acompletion(
            model=MODEL,
            messages=messages,
            tools=schemas,
            temperature=0,
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            return (msg.content or "").strip()

        messages.append(msg.model_dump())

        for tc in tool_calls:
            name = tc.function.name
            raw_args = tc.function.arguments or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                args = {"_raw": raw_args}

            start = time.perf_counter()
            call_res = await session.call_tool(name, args if isinstance(args, dict) else {})
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            result_text = _extract_mcp_text(call_res)
            _log_tool_call(
                tool_name=name,
                arguments=args if isinstance(args, dict) else {"raw": raw_args},
                summary=_summarize_result(result_text),
                duration_ms=elapsed_ms,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                }
            )

    return "Stopped after reaching maximum tool steps."


async def run_suite(questions: list[str], clear_log: bool = False) -> None:
    if clear_log and LOG_PATH.exists():
        LOG_PATH.unlink()

    params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            schemas = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                }
                for t in listed.tools
            ]

            for i, q in enumerate(questions, start=1):
                answer = await ask_agent(session, schemas, q)
                print(f"[Q{i}] {q}\n-> {answer}\n")


if __name__ == "__main__":
    sample_questions = [
        "Do we have Amoxicillin 500mg in stock?",
        "Which items expire within 60 days?",
        "Search for tablets in stock.",
        "Record a sale of 5 packs of Paracetamol 500mg.",
        "Try to sell 500 packs of Amlodipine 10mg.",
        "How much would 2 packs of Ibuprofen 400mg cost in total?",
    ]
    asyncio.run(run_suite(sample_questions, clear_log=True))