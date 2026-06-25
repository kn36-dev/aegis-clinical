CREATE TABLE IF NOT EXISTS checkpoint_blob (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_id TEXT,             -- The previous step's checkpoint_id
    checkpoint BLOB NOT NULL,   -- The state (what has happened)
    metadata BLOB NOT NULL,     -- The how (llm model, token consume)
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- We can use CheckpointNotLatest error
-- To provide 409 by using thread_id and checkpoint_id
-- Example code in src/aegis/graphs/optimistic_locking.py

-- Instead of a full BLOB, refer to what's available in OTel
-- Read more about the metadata and OTel in limitations and tradeoffs.md

-- ### Separation of Checkpoint State and Telemetry Data
-- Checkpoint metadata intentionally stores only trace correlation identifiers (for example, `trace_id`) rather than full OpenTelemetry span payloads. This keeps checkpoint storage compact and optimized for workflow resumption, Human-in-the-Loop (HITL) interactions, and state recovery.
-- Detailed execution telemetry, including span timing, token usage metrics, and runtime diagnostics, is emitted separately through OpenTelemetry exporters and written to local development logs. This allows workflow state and observability data to evolve independently while keeping the checkpoint database lightweight and easy to inspect.
-- For production-scale deployments, telemetry would typically be exported via OTLP to a dedicated observability platform such as Jaeger, Grafana Tempo, OpenObserve, or another OpenTelemetry-compatible backend. The portfolio implementation intentionally keeps observability infrastructure minimal to prioritize reproducibility and ease of setup while still demonstrating trace correlation and instrumentation patterns.