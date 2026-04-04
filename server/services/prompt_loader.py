"""
Prompt loading and rendering for all AI service modules.

All production prompts live in server/prompts/*.md.
Do not duplicate prompt text inside Python files.
To change a prompt, edit the .md file — not the call site.
"""

import json
import os
import re
from functools import lru_cache
from typing import Any

PROMPTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "prompts"))


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load raw prompt text from server/prompts/{name}.md. Results are cached in memory."""
    path = os.path.join(PROMPTS_DIR, f"{name}.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


def render_prompt(name: str, **kwargs) -> str:
    """Load a prompt and substitute {key} placeholders with the provided values.

    Only keys explicitly passed are replaced. Any other {placeholder} text in
    the prompt file is left untouched, so JSON examples in prompts are safe.
    """
    text = load_prompt(name)
    for key, value in kwargs.items():
        text = text.replace(f"{{{key}}}", str(value))
    return text


def parse_json_response(text: str) -> Any:
    """Parse model output into JSON, tolerating fenced code blocks and wrappers.

    Claude sometimes wraps otherwise-valid JSON in ```json fences. This helper
    also tries to recover the first top-level object/array if extra prose slips
    in around the payload.
    """
    text = text.strip()

    candidates = [text]
    if text.startswith("```"):
        unfenced = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        unfenced = re.sub(r"\n?```$", "", unfenced)
        candidates.append(unfenced.strip())

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    for opening, closing in (("{", "}"), ("[", "]")):
        start = text.find(opening)
        end = text.rfind(closing)
        if start == -1 or end == -1 or end <= start:
            continue
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Unable to parse model response as JSON", text, 0)
