CLINIC QUEUE DASHBOARD (Dashboard.tsx)
+----------------------------------------------------------------------------------------------------+
| 🛡️ AEGIS CLINICAL  |  Active Environment: Local Simulation  |  Role: [ Dr. Sarah Evans ▾ ]        |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ CLINICAL WORKLIST ]                                                                             |
|                                                                                                    |
|  Filter by State: [All]  [⏱️ Pending Review (3)]  [⚙️ Processing (1)]  [✅ Completed (14)]        |
|                                                                                                    |
|  +----------------------------------------------------------------------------------------------+  |
|  | PATIENT ID | INGRESS TIMESTAMP   | EXTRACTED PATHOLOGY          | STATUS         | ACTIONS   |  |
|  +----------------------------------------------------------------------------------------------+  |
|  | #PT-9021   | 2026-06-14 14:02:11 | Malignant melanoma of skin   | ⏱️ PENDING HITL| [Review]  |  |
|  | #PT-4412   | 2026-06-14 13:58:44 | Chronic Type B Hepatitis    | ⏱️ PENDING HITL| [Review]  |  |
|  | #PT-1109   | 2026-06-14 13:45:12 | Acute myeloid leukemia       | ⚙️ PROCESSING  | [View Log]|  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+

PHYSICIAN REVIEW CONSOLE (ReviewConsole.tsx)
+----------------------------------------------------------------------------------------------------+
| 🛡️ AEGIS CLINICAL  |  ‹ Back to Dashboard  |  Reviewing Case: #PT-9021                             |
+----------------------------------------------------------------------------------------------------+
|                                                                                                     |
|  +--------------------------------------------+--+-----------------------------------------------+  |
|  | UNSTRUCTURED CLINICAL NOTES (READ-ONLY)    |  | STRUCTURED TAXONOMY RESOLUTION (EDITABLE)     |  |
|  +--------------------------------------------+  +-----------------------------------------------+  |
|  | "Patient presents with an irregularly      |  |                                               |  |
|  |  shaped, asymmetric dark mole on the upper |  |  Extracted ICD-11 Classification Code:         | |
|  |  back. Lesion has evolved rapidly over     |  |  [ 2C81.0 ] ✍️                                |  |
|  |  the last 3 months..."                     |  |                                               |  |
|  |                                            |  |  Canonical Title:                             |  |
|  |                                            |  |  Malignant melanoma of skin, trunk            |  |
|  |                                            |  |                                               |  |
|  |                                            |  |  Confidence Score: [||||||||||... 84%]        |  |
|  |                                            |  |  Orchestrator Node: `parsing.py` -> `lookup.py` |  |
|  +--------------------------------------------+  +-----------------------------------------------+  |
|                                                                                                    |
|  +----------------------------------------------------------------------------------------------+  |
|  | DIFF VIEWER (`DiffViewer.tsx`)                                                                |  |
|  +----------------------------------------------------------------------------------------------+  |
|  |  [Colloquial Phrase] "asymmetric dark mole on the upper back"                                 |  |
|  |  [Mapped Database Entry] -> ICD-11: 2C81.0 (Melanoma of trunk)                                |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                                                                    |
|  [❌ Reject Ingestion ]                             [🛡️ Sign Off & Hydrate State Machine Token ]  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+