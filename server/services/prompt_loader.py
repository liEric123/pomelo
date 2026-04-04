"""
Prompt loading and rendering for all AI service modules.

All production prompts live in server/prompts/*.md.
Do not duplicate prompt text inside Python files.
To change a prompt, edit the .md file — not the call site.
"""

import os
from functools import lru_cache

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
