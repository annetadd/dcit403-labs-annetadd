from pathlib import Path
import json
import os
import re
import time
from dotenv import load_dotenv
import litellm
from litellm import completion

try:
    from tools import TOOLS
except ImportError:
    from lab02.tools import TOOLS

load_dotenv(override=True)
litellm.drop_params = True
MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")

SYSTEM_PROMPT = """You are a helpful market and general-knowledge assistant using a plain-text reasoning loop.
You have two helper tools:
- calculator: evaluate ONE arithmetic expression (for example: 4*185 + 3*95)
- wiki_lookup: look up ONE Wikipedia page title (for example: Bono East Region)

Always write plain text ONLY (no JSON, no code blocks, no tool-call objects) in this exact format:
Thought: <your reasoning for this single step>
Action: calculator | wiki_lookup | finish
Action Input: <arithmetic expression, page title, or final answer>
"""

ACTION_NAME_MAP = {
    "calc": "calculator",
    "calculator": "calculator",
    "wiki": "wiki_lookup",
    "wiki_lookup": "wiki_lookup",
    "finish": "finish",
}

ACTION_RE = re.compile(
    r"Action:\s*([A-Za-z_]+)\s*\nAction Input:\s*(.*)",
    re.DOTALL,
)
STOP_MARKERS = ("\nThought:", "\nAction:", "\nObservation:")
EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"


def parse(text: str):
    match = ACTION_RE.search((text or "").strip())
    if not match:
        return None, None
    raw_action = match.group(1).strip().lower()
    raw_input = match.group(2)
    cut_positions = [raw_input.find(m) for m in STOP_MARKERS if raw_input.find(m) != -1]
    if cut_positions:
        raw_input = raw_input[: min(cut_positions)]
    return ACTION_NAME_MAP.get(raw_action, raw_action), raw_input.strip()


def extract_from_failed_generation(err_text: str):
    """If Groq throws tool_use_failed, recover (action, action_input) from failed_generation."""
    m = re.search(r'"failed_generation"\s*:\s*"((?:\\.|[^"\\])*)"', err_text)
    if not m:
        return None, None
    try:
        raw_json = json.loads(f'"{m.group(1)}"')
        data = json.loads(raw_json)
        if isinstance(data, dict):
            name = str(data.get("name", "")).strip().lower()
            action = ACTION_NAME_MAP.get(name, name)
            args = data.get("arguments", {})
            if isinstance(args, dict):
                val = (
                    args.get("expression")
                    or args.get("input")
                    or args.get("title")
                    or args.get("query")
                    or (next(iter(args.values())) if args else "")
                )
                return action, str(val).strip()
            if args is not None:
                return action, str(args).strip()
    except Exception:
        return None, None
    return None, None


def call_model_with_retry(messages: list[dict], max_retries: int = 3):
    delay = 2
    last_err = None
    for attempt in range(max_retries):
        try:
            return completion(
                model=MODEL,
                temperature=0,
                messages=messages,
                stop=["Observation:"],
            )
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if ("429" in msg or "rate" in msg or "503" in msg or "502" in msg) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise last_err


def run_agent(question: str, max_steps: int = 6, trace_num: int | None = None) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    trace_lines = [f"Question: {question}", "=" * 60]
    last_obs = None
    final_answer = f"Stopped after reaching max_steps ({max_steps}) without finishing."

    for step in range(1, max_steps + 1):
        try:
            resp = call_model_with_retry(messages)
        except Exception as e:
            err_str = str(e)
            recovered_action, recovered_input = extract_from_failed_generation(err_str)
            if recovered_action:
                reply = (
                    f"Thought: Recovered tool call from model output.\n"
                    f"Action: {recovered_action}\n"
                    f"Action Input: {recovered_input}"
                )
                messages.append({"role": "assistant", "content": reply})
                trace_lines.append(f"[Step {step}] (recovered from tool_use_failed)\n{reply}")
                if recovered_action == "finish":
                    final_answer = recovered_input
                    trace_lines.append(f"Final Answer: {final_answer}")
                    break
                if recovered_action in TOOLS:
                    obs = TOOLS[recovered_action](recovered_input)
                else:
                    obs = f"Unknown action '{recovered_action}'. Choose only from: calculator, wiki_lookup, finish."
                last_obs = obs
                obs_line = f"Observation: {obs}"
                messages.append({"role": "user", "content": obs_line})
                trace_lines.append(obs_line)
                trace_lines.append("-" * 60)
                continue

            obs = (
                f"Model error ({err_str}). Do not output JSON or tool calls. "
                "Write plain text lines starting with Thought:, Action:, and Action Input:."
            )
            last_obs = obs
            trace_lines.append(f"[Step {step}] MODEL ERROR: {err_str}")
            obs_line = f"Observation: {obs}"
            messages.append({"role": "user", "content": obs_line})
            trace_lines.append(obs_line)
            trace_lines.append("-" * 60)
            continue

        reply = (resp.choices[0].message.content or "").strip()
        if not reply:
            obs = (
                "Empty response. Write one step using:\n"
                "Thought: <reasoning>\n"
                "Action: calculator | wiki_lookup | finish\n"
                "Action Input: <input or final answer>"
            )
            last_obs = obs
            trace_lines.append(f"[Step {step}] <empty reply>")
            obs_line = f"Observation: {obs}"
            messages.append({"role": "user", "content": obs_line})
            trace_lines.append(obs_line)
            trace_lines.append("-" * 60)
            continue

        messages.append({"role": "assistant", "content": reply})
        trace_lines.append(f"[Step {step}]\n{reply}")

        action, action_input = parse(reply)

        if not action:
            obs = (
                "Invalid format. Reply using exact plain-text lines:\n"
                "Thought: <reasoning>\n"
                "Action: calculator | wiki_lookup | finish\n"
                "Action Input: <input or final answer>"
            )
        elif action == "finish":
            final_answer = action_input
            trace_lines.append(f"Final Answer: {final_answer}")
            break
        elif action not in TOOLS:
            obs = f"Unknown action '{action}'. Choose only from: calculator, wiki_lookup, finish."
        else:
            obs = TOOLS[action](action_input)

        last_obs = obs
        obs_line = f"Observation: {obs}"
        messages.append({"role": "user", "content": obs_line})
        trace_lines.append(obs_line)
        trace_lines.append("-" * 60)
    else:
        if last_obs is not None:
            final_answer = f"Stopped after reaching max_steps ({max_steps}). Last observation: {last_obs}"
        trace_lines.append(f"Final Answer: {final_answer}")

    full_trace = "\n".join(trace_lines)
    if trace_num is not None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCE_DIR / f"trace_{trace_num}.txt").write_text(full_trace, encoding="utf-8")

    return final_answer


if __name__ == "__main__":
    test_questions = [
        "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left?",
        "What is the capital of the Bono East Region and how much is 25% of 480?",
        "How many grams of gold are in the Accra Central Treasury vault 2026?",
        "Tell me about NonexistentXYZPage987654321.",
        "Hello, how are you today?",
        "rice 4x185 oil 3x95 left from 1200 budget??",
    ]
    for idx, q in enumerate(test_questions, start=1):
        ans = run_agent(q, max_steps=6, trace_num=idx)
        print(f"Trace {idx} -> {ans}\n")
        time.sleep(2)