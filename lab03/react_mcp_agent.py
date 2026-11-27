import asyncio
import json
import os
from pathlib import Path
import re
from dotenv import load_dotenv
from litellm import acompletion
from litellm.exceptions import BadRequestError
import litellm
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(override=True)
litellm.drop_params = True

MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")
BASE_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = str(BASE_DIR / "server.py")
TRACE_PATH = BASE_DIR / "evidence" / "react_via_mcp.txt"

ACTION_RE = re.compile(r"Action:\s*([a-zA-Z0-9_-]+)\s*\nAction Input:\s*(.*)", re.DOTALL)


def parse_react_step(text: str) -> tuple[str | None, str | None]:
    cleaned = text.strip()
    m = ACTION_RE.search(cleaned)
    if not m:
        return None, None
    action = m.group(1).strip()
    raw_input = m.group(2).strip()
    for marker in ("\nThought:", "\nAction:", "\nObservation:"):
        idx = raw_input.find(marker)
        if idx != -1:
            raw_input = raw_input[:idx].strip()
    return action, raw_input


def _reply_from_failed_generation(exc: BadRequestError) -> str | None:
    match = re.search(r'"failed_generation"\s*:\s*"((?:\\.|[^"\\])*)"', str(exc))
    if not match:
        return None
    try:
        raw_payload = json.loads(f'"{match.group(1)}"')
        data = json.loads(raw_payload)
        if isinstance(data, dict) and "name" in data:
            args_str = json.dumps(data.get("arguments", {}))
            return f"Thought: Calling MCP tool {data['name']}.\nAction: {data['name']}\nAction Input: {args_str}"
    except Exception:
        return None
    return None


def _format_tool_catalog(tools) -> str:
    lines = []
    for t in tools:
        schema = t.inputSchema or {}
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        param_desc = ", ".join(
            f"{k}{'*' if k in required else ''}: {v.get('type', 'any')}"
            for k, v in props.items()
        )
        lines.append(f"- {t.name}({param_desc}): {t.description or 'No description.'}")
    lines.append("- finish(answer: str): Provide the final answer when ready.")
    return "\n".join(lines)


def _coerce_args(tool_obj, raw_input: str) -> dict:
    schema = (tool_obj.inputSchema or {}) if tool_obj else {}
    props = schema.get("properties", {})
    prop_names = list(props.keys())

    if raw_input:
        try:
            parsed = json.loads(raw_input)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    if len(prop_names) == 1:
        key = prop_names[0]
        ptype = props[key].get("type", "string")
        if ptype == "integer":
            try:
                return {key: int(raw_input)}
            except ValueError:
                pass
        return {key: raw_input}

    if raw_input and prop_names:
        return {prop_names[0]: raw_input}
    return {}


async def run_react_via_mcp(question: str, max_steps: int = 6) -> str:
    params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])
    trace_lines = [f"Question: {question}", "=" * 60]

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tool_map = {t.name: t for t in listed.tools}

            system_prompt = (
                "You are a pharmacy assistant using a ReAct loop.\n"
                "Available MCP tools:\n"
                f"{_format_tool_catalog(listed.tools)}\n\n"
                "For Action Input, pass a JSON object matching the tool parameters "
                "(or plain text if a single string parameter is expected).\n"
                "Respond in this exact format on every step (do not write Observation: yourself):\n"
                "Thought: <your reasoning>\n"
                "Action: <tool_name or finish>\n"
                "Action Input: <arguments or final answer>"
            )

            history = [{"role": "user", "content": question}]
            final_answer = "Stopped before reaching finish."

            for step in range(1, max_steps + 1):
                try:
                    resp = await acompletion(
                        model=MODEL,
                        messages=[{"role": "system", "content": system_prompt}, *history],
                        temperature=0,
                    )
                    reply = (resp.choices[0].message.content or "").strip()
                except BadRequestError as exc:
                    recovered = _reply_from_failed_generation(exc)
                    if not recovered:
                        raise
                    reply = recovered

                action, raw_input = parse_react_step(reply)

                trace_lines.append(f"[Step {step}]")
                trace_lines.append(reply if reply else "(empty model reply)")

                if not action:
                    obs = (
                        "Invalid format. Reply using 'Thought:', "
                        "'Action: <tool_name|finish>', and 'Action Input: <input>'."
                    )
                    trace_lines.append(f"Observation: {obs}")
                    trace_lines.append("-" * 60)
                    history.append({"role": "assistant", "content": reply or "Invalid format."})
                    history.append({"role": "user", "content": f"Observation: {obs}"})
                    continue

                if action == "finish":
                    final_answer = raw_input or reply
                    trace_lines.append(f"Final Answer: {final_answer}")
                    break

                if action not in tool_map:
                    obs = f"Unknown action '{action}'. Available tools: {', '.join(tool_map.keys())}, finish."
                else:
                    args = _coerce_args(tool_map[action], raw_input or "")
                    call_res = await session.call_tool(action, args)
                    chunks = [
                        getattr(b, "text", str(b))
                        for b in (getattr(call_res, "content", None) or [])
                    ]
                    obs = "\n".join(chunks) if chunks else "[]"

                trace_lines.append(f"Observation: {obs}")
                trace_lines.append("-" * 60)
                history.append({"role": "assistant", "content": reply})
                history.append({"role": "user", "content": f"Observation: {obs}"})

            TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
            TRACE_PATH.write_text("\n".join(trace_lines) + "\n", encoding="utf-8")
            return final_answer


if __name__ == "__main__":
    q = "Check stock for Amoxicillin 500mg and tell me how many packs are available."
    ans = asyncio.run(run_react_via_mcp(q))
    print("Final Answer:", ans)
    print(f"Saved trace to {TRACE_PATH}")