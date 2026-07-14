RetrievalCandidate

Purpose
-------
Represents a single ICD-11 taxonomy concept returned by semantic retrieval.

Identity
--------
- icd_code

Knowledge
---------
- title
- hierarchy_context
- chapter_number
- semantic_representation

Retrieval Signals
-----------------
- similarity_score

Metadata
--------
- retrieval_metadata

Explicitly Does NOT Contain
---------------------------
- confidence
- ranking
- physician decision
- reasoning
- diagnosis
- workflow state
- infrastructure-specific concepts (Upstash IDs, namespaces, providers)