# CrewAI orchestrates autonomous parsing
# Concurrent SQLite taxonomy checks

# src/aegis/agents/parsing.py
from crewai import Agent, Crew, Task

from aegis.schemas.validation import ClinicalExtractionResult


def execute_extraction_crew(anonymized_note: str) -> ClinicalExtractionResult:
    parser_agent = Agent(
        role="Clinical Coding Expert",
        goal="Map loose medical symptoms into crisp ICD-11 definitions",
        backstory="An expert medical archivist trained on WHO taxonomies.",
        verbose=False,
    )

    parsing_task = Task(
        description=f"Parse the following text: {anonymized_note}",
        expected_output="A structured list of matching ICD-11 taxonomy codes.",
        agent=parser_agent,
        output_json=ClinicalExtractionResult,  # PydanticAI validation boundary layer
    )

    crew = Crew(agents=[parser_agent], tasks=[parsing_task])
    raw_output = crew.kickoff()

    return raw_output
