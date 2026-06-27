                 New Clinical Note
                         │
                         ▼
                 Phase 1 Anonymize
                         │
                         ▼
                  Normalize Text
                         │
                         ▼
                    SHA-256 Hash
                         │
                         ▼
                  Redis Cache Lookup
                  ┌───────────────┐
                  │               │
             Cache Hit        Cache Miss
                  │               │
                  ▼               ▼
         Return ICD Codes    Generate Embedding
                  │               │
                  │               ▼
                  │      taxonomy_lookup
                  │               │
                  │               ▼
                  │      Candidate ICD Codes
                  │               │
                  │               ▼
                  │      CrewAI Validation
                  │               │
                  │               ▼
                  │      Physician Review
                  │               │
                  │               ▼
                  └──────► SQLite Commit ◄──────┐
                                   │            │
                                   ▼            │
                            Redis Cache Write ──┘