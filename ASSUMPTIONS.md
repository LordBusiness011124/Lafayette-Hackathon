# Assumptions and limits

- The user changed the selected business to Julian's Tailor Shop and reported Glenn's permanently closed. No Glenn's address or directory facts are used for Julian's. Julian's spelling, address, website, and open status still need verification.
- Every ticket requires human confirmation, including requests with no specific handoff reasons.
- A deadline at most two calendar days away, including overdue dates, triggers urgent review. This is our heuristic, not a shop policy.
- Bare weekdays include today when it matches. “Next Saturday” means the Saturday in the following occurrence week: the upcoming Saturday plus seven days. “This weekend” means the next Saturday, including today if Saturday. These conventions are explicit and may differ from customer intent; the tailor must confirm.
- Vague urgency keeps a null deadline date. Unsupported date wording may need a human to identify the deadline; the mock is not a general date parser.
- The deterministic mock is an offline demonstration, not a language model. It handles the authored test vocabulary and can misassign alterations or materials in complex multi-item sentences.
- Live extraction uses OpenAI JSON schema or Anthropic tool output. Real-provider connectivity, model availability, and extraction accuracy are unverified.
- Prompt-injection detection is a heuristic. Safety does not depend on detecting all attacks: output is restricted to templates and tickets always remain pending.
- Messages are independent requests; chat display does not imply multi-turn context or ticket edits.
- JSONL persistence uses a process-local lock. Run one server process; no database, concurrent multi-process coordination, appointments, payments, or communications are included.
- Runtime used for verification was Python 3.14. Python 3.11 compatibility has not been separately exercised.
