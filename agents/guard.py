"""
Output guard: checks what the agents WRITE before the user sees it.

Prompts ask the LLM to use only facts from the tools, but a prompt is a
request, not a guarantee (a live test produced "reduced page load time by
30%" - a number that exists nowhere). So every agent summary, the final
answer and the next steps are checked in code:

- a sentence that names a skill/technology found neither in the resume nor
  in any tool result is removed (it would be an invented claim or advice)
- a number that appears neither in the resume nor in the tool results is
  replaced by [add real number] (same rule as the resume assistant)

Missing skills, scores, resource times etc. are allowed because they come
from the tool results.
"""

import json
import re

from resume_parser.improvement import remove_invented_numbers
from resume_parser.skill_extractor import extract_skills


def allowed_text(ctx):
    """
    Everything the agents are allowed to talk about: the resume, the job
    description and every tool result of this run.
    """

    return "\n".join([
        ctx.resume_text,
        ctx.jd_text,
        json.dumps(ctx.artifacts, ensure_ascii=False, default=str),
    ])


def _sentences(line):
    return [s for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]


def check(text, allowed):
    """
    Returns (clean_text, removed_sentences).
    """

    known_skills = {s.lower() for s in extract_skills(allowed)}

    kept_lines = []
    removed = []

    for line in (text or "").splitlines():

        if not line.strip():
            kept_lines.append("")
            continue

        kept = []

        for sentence in _sentences(line):

            invented = {s.lower() for s in extract_skills(sentence)} - known_skills

            if invented:
                removed.append(sentence.strip())
            else:
                kept.append(sentence)

        if kept:
            kept_lines.append(" ".join(kept))

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()

    cleaned, _ = remove_invented_numbers(cleaned, allowed)

    return cleaned, removed


def clean_steps(steps):
    """
    Next steps as a flat list: splits items that contain several lines and
    removes "1." style numbering (the page numbers them).
    """

    flat = []

    for item in steps or []:
        for part in str(item).splitlines():
            part = re.sub(r"^\s*(?:\d+[.)]|-)\s*", "", part).strip()
            if part:
                flat.append(part)

    return flat
