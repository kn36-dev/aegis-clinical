# Aegis-Clinical Verification & Metric Validation Matrix

| Evaluation Dimension | Metric Vector | Target Threshold | Production Verification Protocol |
| :--- | :--- | :--- | :--- |
| **Clinical Taxonomy Accuracy** | Extraction Precision & Recall ($F_1$ Score) | $$F_1 \ge 0.94$$ | Evaluated continuously via Braintrust across a 500-case synthetic validation dataset. |
| **System Cache Efficiency** | Financial Token Reduction Curve | $\ge 75\%$ Cost Elimination | Measured by tracking telemetry span metrics comparing raw ingress tokens against cache write-backs. |
| **State Chart Determinism** | Path Invariance Under Adversarial Loads | $100\%$ Compliant Routing | Verified by injecting randomized exceptions across 1,000 parallel test graph runs. |
| **Schema Integrity** | Boundary Rejection Resilience | $100\%$ Catchment Rate | Validated via property-based data fuzzing tools targeted directly at input schemas. |
| **HITL Persistence Stability** | Thread Recovery Fidelity | $100\%$ Hydration Success | Verified by forcing sudden system restarts while multiple execution threads are suspended. |