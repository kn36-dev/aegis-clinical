Why Sqlite instead of a proper relational database like PostgreSQL
- Yes I know that using PostgreSQL allows better database performance, like better concurrency, sharding, indexing, partitioning read and write databases etc, but this project's primary purpose is to demonstrate strong AI Engineering vigor, so the database setup is kept intentionally light-weight.
- It also allows easier reproduction if a repository visitor decides to clone the project and have a go at it.
- In exchange, a proper database setup command will be included in the repository, which is not something commonly required in production systems.

The patient_identity_vault seems to be not properly secured
- Yes, in production systems, the Personally Identifiable Information (PII) must be rigourously protected by: 
   - Encryption of the actual disk
   - AES-256 for the exact columns and the secret key kept in a cloud key management service
   - Secured in isolated virtual private network with no public IP Address
   - Application-Layer Encryption (CLE) to encrypt and decrypt sensitive texts before sending it over the wire
- But it does not add to the AI Engineering experise showcase, so it is currently kept extremely minimal


### Separation of Checkpoint State and Telemetry Data

Checkpoint metadata intentionally stores only trace correlation identifiers (for example, `trace_id`) rather than full OpenTelemetry span payloads. This keeps checkpoint storage compact and optimized for workflow resumption, Human-in-the-Loop (HITL) interactions, and state recovery.

Detailed execution telemetry, including span timing, token usage metrics, and runtime diagnostics, is emitted separately through OpenTelemetry exporters and written to local development logs. This allows workflow state and observability data to evolve independently while keeping the checkpoint database lightweight and easy to inspect.

For production-scale deployments, telemetry would typically be exported via OTLP to a dedicated observability platform such as Jaeger, Grafana Tempo, OpenObserve, or another OpenTelemetry-compatible backend. The portfolio implementation intentionally keeps observability infrastructure minimal to prioritize reproducibility and ease of setup while still demonstrating trace correlation and instrumentation patterns.

In real life, a clinical system would need these, which are definitely impossible to be within scope for a portfolio demonstration:
- Backup strategy
- Migration strategy
- Encryption at rest
- PHI key management
- Role-based access control
- Retention policies
- Audit immutability
- Disaster recovery