"""
Execution tracking: records every step of an agent run.

A step is one thing that happened: the planner's decision, an LLM call,
a tool call (with its input and output), an error, or the final answer.
Steps are kept in memory and written to the agent_steps table, so the
"how the agent worked" trace can be shown on the run page.

If the upgrade_v7 tables do not exist yet, tracking still works in memory
and nothing is saved (the app never breaks because of tracking).
"""

import json
import time

from models.repository import _execute, has_table


MAX_STORED_CHARS = 6000


def _to_text(value):

    if value is None:
        return ""

    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)

    return text[:MAX_STORED_CHARS]


class Tracker:

    def __init__(self, user_id, goal, save=True):

        self.user_id = user_id
        self.goal = goal
        self.steps = []
        self.run_id = None
        self.save = save and _tables_ready()

        if self.save:
            try:
                self.run_id, _ = _execute(
                    "INSERT INTO agent_runs (user_id, goal, status) VALUES (%s, %s, 'running')",
                    (user_id, goal[:5000])
                )
            except Exception as e:
                print("Agent tracking disabled:", e)
                self.save = False

    # ---------------------------------------------------------

    def step(self, agent, kind, name="", input_data=None, output_data=None, ok=True, started=None):
        """
        Records one step. kind: plan | llm | tool | error | final | memory.
        started: time.time() when the step began (for its duration).
        """

        duration_ms = int((time.time() - started) * 1000) if started else 0

        record = {
            "step_no": len(self.steps) + 1,
            "agent": agent,
            "kind": kind,
            "name": name,
            "input": _to_text(input_data),
            "output": _to_text(output_data),
            "ok": bool(ok),
            "duration_ms": duration_ms,
        }

        self.steps.append(record)

        if self.save and self.run_id:
            try:
                _execute(
                    """INSERT INTO agent_steps
                       (run_id, step_no, agent, kind, name, input_data, output_data, ok, duration_ms)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (self.run_id, record["step_no"], agent[:50], kind[:20], (name or "")[:100],
                     record["input"], record["output"], record["ok"], duration_ms)
                )
            except Exception as e:
                print("Agent step not saved:", e)

        return record

    # ---------------------------------------------------------

    def finish(self, status, plan=None, final_answer="", result=None, error=""):

        if not (self.save and self.run_id):
            return

        try:
            _execute(
                """UPDATE agent_runs
                   SET status = %s, plan = %s, final_answer = %s, result = %s, error = %s,
                       finished_at = CURRENT_TIMESTAMP
                   WHERE run_id = %s AND user_id = %s""",
                (status, json.dumps(plan or []), final_answer or "",
                 json.dumps(result or {}, ensure_ascii=False, default=str), (error or "")[:2000],
                 self.run_id, self.user_id)
            )
        except Exception as e:
            print("Agent run not saved:", e)


def _tables_ready():

    try:
        return has_table("agent_runs") and has_table("agent_steps")
    except Exception:
        return False
