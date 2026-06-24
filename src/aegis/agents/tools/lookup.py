# READ Pattern: An agent uses an icd11_lookup_tool to query
# a local SQLite mirror or vector index for semantic matches.

# UPSERT Pattern (Rare & Restricted): If an agent needs to
# write (e.g., caching a newly discovered medical term translation),
# it does so through a highly restricted tool that handles
# its own transactional boundaries and error isolation.

from crewai.tools import tool

from aegis.database.connection import get_db_context
from aegis.database.repository import ClinicalRegistryRepository


@tool("ICD-11 Official Database Lookup")
def lookup_icd11_code(medical_term: str) -> str:
    """Queries the internal registry mirror to verify clinical term alignment."""
    with get_db_context() as db:
        # Strict read-only interaction for worker enrichment
        repo = ClinicalRegistryRepository(db)
        official_taxonomy = repo.query_taxonomy_code(medical_term)

    return official_taxonomy if official_taxonomy else "No direct match found."
