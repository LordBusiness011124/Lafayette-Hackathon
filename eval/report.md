# Intake evaluation

Self-authored; not real customer data. n=30 fictional cases. Provider: deterministic mock. Fixed time: 2026-10-08T12:00:00-04:00.

| Metric | Result | Computation |
| --- | --- | --- |
| Field extraction accuracy | 100.0% | 38/38 explicitly annotated field checks match exactly; unannotated fields are not scored |
| Handoff precision | 100.0% | 96 true positives / 96 predicted reasons, micro-averaged |
| Handoff recall | 100.0% | 96 true positives / 96 expected reasons, micro-averaged |
| Forbidden-claim violations | 0 | Number of replies failing deterministic scanner or per-case forbidden phrases; target zero |

This small test set measures these authored examples only. It does not establish real-world accuracy. Mock results do not measure a live LLM. Template allowlisting prevents arbitrary output claims; regex scanning alone is not a complete semantic safety test.

## Mismatches

None.
