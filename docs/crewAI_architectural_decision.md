# CrewAI Architectural Decision

## Why does the portfolio currently use only a single CrewAI agent?

At first glance, a single-agent CrewAI workflow may appear unnecessary. However, the architectural purpose of CrewAI in this project is not to maximize the number of agents, but to establish a dedicated **clinical reasoning boundary** within the overall AI pipeline.

The system deliberately separates responsibilities into three distinct layers:

* **LangGraph** orchestrates long-running workflows, checkpointing, retries, and Human-in-the-Loop (HITL) interactions.
* **CrewAI** encapsulates domain-specific clinical reasoning.
* **PydanticAI** performs deterministic structured inference, guaranteeing strongly typed outputs for downstream processing.

The current implementation consolidates the clinical reasoning process into a single specialist agent responsible for interpreting physician notes, evaluating semantically retrieved ICD-11 candidates, and producing structured coding suggestions. This keeps the portfolio implementation compact while still demonstrating the separation between workflow orchestration and AI reasoning.

## Why not remove CrewAI?

Removing CrewAI would tightly couple clinical reasoning directly into the LangGraph workflow. Introducing CrewAI establishes a stable architectural boundary that allows the reasoning engine to evolve independently of the surrounding orchestration.

As the project grows, this reasoning boundary naturally supports decomposition into additional specialist agents without requiring changes to the LangGraph state machine.

Examples of future specialist agents include:

* Symptom Extraction Agent
* ICD-11 Validation Agent
* Negation & Context Analysis Agent
* Temporal Clinical Reasoning Agent
* Trial Eligibility Reasoning Agent

Because these agents would remain internal to the CrewAI layer, the external workflow and API surface would remain unchanged.

## Tradeoff

The portfolio intentionally implements only a single specialist agent to keep inference cost, orchestration complexity, evaluation scope, and repository size manageable. The abstraction is introduced not as speculative future-proofing, but because it cleanly separates **workflow orchestration** from **clinical reasoning**, allowing each layer to evolve independently while preserving architectural stability.
