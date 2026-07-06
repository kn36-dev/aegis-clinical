"""
Repository-level persistence models.

These models represent raw data as it exists in the SQLite database
before any domain or indexing transformations occur.

They are intentionally separated from:
- Domain models (ICDConcept)
- Indexing models (RepresentationDocument)
- Orchestration (LangGraph)

This layer acts as the clean boundary between storage and application logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ============================================================================
# ICD Taxonomy Persistence Model
# ============================================================================


@dataclass(frozen=True, slots=True)
class ICDTaxonomyRecord:
    """
    Raw ICD-11 taxonomy record as stored in SQLite.

    This model reflects the ingestion structure of the ICD CSV file
    with minimal transformation.

    It is NOT a domain model and NOT used directly in retrieval.
    It is only used as input for:
        - ICDConcept construction
        - Representation building (indexing layer)
    """

    code: str
    title: str
    # Hierarchical and contextual metadata from ICD CSV
    context_path: Optional[str] = None

    # Optional structural metadata from ingestion layer
    chapter_no: Optional[str] = None

    # Flags derived from CSV but preserved for downstream use
    is_leaf: Optional[bool] = None
    is_residual: Optional[bool] = None
