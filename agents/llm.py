"""
The agent loop (Groq function calling).

This is what makes the program an *agent* instead of a fixed pipeline:

    1. The LLM gets its role, the user's goal and a list of tools.
    2. It decides: answer now, or call one or more tools (with arguments).
    3. We run the tools and send the results back ("observations").
    4. It reads them and decides again: another tool, or the final answer.

Steps 2-4 repeat until the LLM answers or MAX_STEPS is reached, so the
path is chosen by the model at run time, not written in our code.

Safety and error handling:
- only the agent's own tools can be called; unknown tools/arguments are refused
- tool errors are sent back to the LLM so it can correct itself
- the same tool call is never run twice (its earlier result is reused)
- Groq errors (bad tool call, rate limit, timeout) are retried once
- a hard step limit stops endless loops; the agent is then asked to answer
- every LLM decision and tool call is recorded by the Tracker

Reuses the existing Groq client, model and prompt-injection rule from
resume_parser/ai_client.py.
"""

import json
import re
import time

from resume_parser import ai_client

from agents import tools as toolbox


MAX_STEPS = 6
MAX_TOOL_CALLS_PER_STEP = 4


class LLMUnavailable(Exception):
    pass


def available():
    return ai_client.client is not None


# ---------------------------------------------------------
# One LLM call (tests replace this function with a fake)
# ---------------------------------------------------------

def complete(messages, tool_schemas=None, tool_choice="auto"):
    """
    Returns {"content": str, "tool_calls": [{"id", "name", "arguments"}]}.
    Raises LLMUnavailable if there is no API key or the call keeps failing.
    """

    if not available():
        raise LLMUnavailable("GROQ_API_KEY is not set.")

    kwargs = dict(
        model=ai_client.MODEL,
        messages=messages,
        temperature=0.1,
        max_completion_tokens=2048,
        reasoning_effort="low",
        timeout=60,
    )

    if tool_schemas:
        kwargs["tools"] = tool_schemas
        kwargs["tool_choice"] = tool_choice

    last_error = None

    for attempt in range(2):

        try:
            response = ai_client.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            return {
                "content": message.content or "",
                "tool_calls": [
                    {"id": call.id, "name": call.function.name, "arguments": call.function.arguments or "{}"}
                    for call in (message.tool_calls or [])
                ],
            }

        except Exception as e:

            last_error = e
            text = str(e).lower()

            # Rate limit: wait a little, then try once more
            if "rate" in text and "limit" in text:
                time.sleep(4)
            # Malformed tool call from the model: retry once
            elif "tool_use_failed" in text or "tool call" in text:
                kwargs["temperature"] = 0.3
            else:
                time.sleep(1)

    raise LLMUnavailable(f"The AI service failed: {type(last_error).__name__}")


def ask_json(system_message, prompt):
    """
    One JSON answer without tools (planner and final answer). None on failure.
    """

    return ai_client.ask_ai_for_json(system_message, prompt, cache=False)


# ---------------------------------------------------------
# The agent loop
# ---------------------------------------------------------

def run_agent(agent_name, system_prompt, task, tool_names, ctx, tracker, max_steps=MAX_STEPS):
    """
    Runs one agent until it answers. Returns a report:
    {"agent", "ok", "summary", "tools_used", "error"}
    """

    messages = [
        {"role": "system", "content": system_prompt + ai_client.UNTRUSTED_INPUT_RULE},
        {"role": "user", "content": task},
    ]

    schemas = toolbox.schemas(tool_names)
    tools_used = []
    done_calls = {}

    for step in range(max_steps):

        started = time.time()

        try:
            reply = complete(messages, schemas)
        except LLMUnavailable as e:
            tracker.step(agent_name, "error", "llm", output_data=str(e), ok=False, started=started)
            return {"agent": agent_name, "ok": False, "summary": "", "tools_used": tools_used, "error": str(e)}

        calls = reply["tool_calls"][:MAX_TOOL_CALLS_PER_STEP]

        tracker.step(agent_name, "llm", "decide",
                     input_data=f"step {step + 1}",
                     output_data={"thought": reply["content"][:500],
                                  "tool_calls": [{"name": c["name"], "arguments": c["arguments"]} for c in calls]},
                     started=started)

        # No tool call: this is the agent's answer
        if not calls:
            return {"agent": agent_name, "ok": True, "summary": plain_text(reply["content"]),
                    "tools_used": tools_used, "error": ""}

        messages.append({
            "role": "assistant",
            "content": reply["content"] or "",
            "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ],
        })

        for call in calls:

            started = time.time()
            key = (call["name"], _normalise_args(call["arguments"]))

            if call["name"] not in tool_names:
                ok, text = False, json.dumps({"error": f"Tool '{call['name']}' is not available to this agent."})
            elif key in done_calls:
                ok, text = True, done_calls[key]
            else:
                ok, text, _ = toolbox.execute(ctx, call["name"], call["arguments"])
                if ok:
                    done_calls[key] = text
                    tools_used.append(call["name"])

            tracker.step(agent_name, "tool", call["name"], input_data=call["arguments"],
                         output_data=text, ok=ok, started=started)

            messages.append({"role": "tool", "tool_call_id": call["id"], "content": text})

    # Step limit reached: ask for the answer without tools
    started = time.time()

    messages.append({"role": "user", "content": "Stop calling tools now. Give your final answer from the results you have."})

    try:
        reply = complete(messages)
        summary = plain_text(reply["content"])
        tracker.step(agent_name, "llm", "final (step limit)", output_data=summary[:500], started=started)
        return {"agent": agent_name, "ok": True, "summary": summary, "tools_used": tools_used, "error": ""}
    except LLMUnavailable as e:
        tracker.step(agent_name, "error", "llm", output_data=str(e), ok=False, started=started)
        return {"agent": agent_name, "ok": False, "summary": "", "tools_used": tools_used, "error": str(e)}


def run_tools_without_llm(agent_name, plan, ctx, tracker):
    """
    Fallback when the AI is unavailable: run the agent's default tools in a
    fixed order, so the user still gets results (just without AI reasoning).
    plan: [(tool_name, arguments), ...]
    """

    tools_used = []
    errors = []

    for name, arguments in plan:

        started = time.time()

        ok, text, _ = toolbox.execute(ctx, name, arguments)

        tracker.step(agent_name, "tool", name, input_data=arguments, output_data=text, ok=ok, started=started)

        if ok:
            tools_used.append(name)
        else:
            errors.append(text)

    return {
        "agent": agent_name,
        "ok": bool(tools_used),
        "summary": "AI reasoning was unavailable, so the standard tools were run in a fixed order.",
        "tools_used": tools_used,
        "error": "; ".join(errors)[:500],
    }


def plain_text(text):
    """
    Removes markdown the model sometimes adds (**bold**, # headings), since
    answers are shown as plain text.
    """

    lines = []

    for line in (text or "").strip().splitlines():
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        line = re.sub(r"^\s*[*•]\s+", "- ", line)
        lines.append(line.replace("**", "").replace("__", ""))

    return "\n".join(lines).strip()


def _normalise_args(arguments):

    try:
        return json.dumps(json.loads(arguments or "{}"), sort_keys=True)
    except (TypeError, ValueError):
        return str(arguments)
