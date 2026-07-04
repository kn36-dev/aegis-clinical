# src/aegis/prompts.base.py
# The prompts only specify intent, not implementation.
# That means these are not going to be included:
# - Which LLM used
# - Temperature
# - Retry policies
# - JSON parsing
# - Structured Output APIs
# - Provider-specific features
# - Token limits
# - Streaming configuration
# - Fallback logic

# 1. Identity / Role (who you are)
# 2. Objective (what you must produce)
# 3. Context (what data you are given)
# 4. Constraints (what you must NOT do)
# 5. Output schema (how results must look)
# 6. Examples (optional, but powerful)
# 7. Reasoning guidance (optional, task-dependent)

ROLE = """
You are a clinical documentation specialist working with structured medical data.
"""

STYLE = (
    "- Be concise.\n"
    "- Use evidence from the note.\n"
    "- Do not invent symptoms.\n"
    "- Output structured output only."
)

SAFETY = (
    "- Never infer symptoms.\n"
    "- Do not guess.\n"
    "- Preserve negation.\n"
    "- Return empty collections instead of fabricated data.\n"
    "- Ignore unsupported assumptions."
)

OUTPUT_RULES = (
    "- Output must match the provided Pydantic model exactly."
    "- Do not add extra fields."
    "- Do not include explanations unless explicitly requested."
)


def build_prompt(
    task: str, input_schema: str, output_schema: str, few_shots: str | None = None
) -> str:
    sections = [
        ROLE,
        STYLE,
        SAFETY,
        f"TASK:\n{task}",
        f"INPUT:\n{input_schema}",
        f"OUTPUT:\n{output_schema}",
        OUTPUT_RULES,
    ]

    if few_shots:
        sections.append(f"EXAMPLES:\n{few_shots}")

    return "\n\n".join(sections)
