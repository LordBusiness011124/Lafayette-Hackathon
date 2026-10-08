# Assumptions and limits

See README.md for the current workflow and demo boundaries. This extends the original independent alteration intake into an owner-driven local simulation for Julian’s Chapel Hill.

- Store name/address/contact/hours use the official website; labor pricing, service feasibility, rush policy and capacity remain unknown.
- The concierge uses offline rules and the original mock extractor. No live AI or communication is enabled.
- The agent collects required garment/change/contact fields. Owner-specific questions are relayed and customer answers recorded. The owner must confirm feasibility, prices and deadlines.
- Ticket IDs survive follow-up; workflow state is stored on the enclosing session. The original intake schema always records `PENDING_SHOP_CONFIRMATION`.
- Same-type garment references are merged. Distinct garments of the same type, arbitrary corrections/removals and unrestricted language require richer extraction.
- Bare weekdays include today when it matches. Next Saturday follows the original project’s convention. Vague urgency has no exact date. Dates use New York time.
- The catalog snapshot is the first 250 products, not the entire store or live stock. Tax/shipping, real payments, inventory quantities and appointments are outside this local simulation.
- File persistence supports one server process. Roles are simulated, with no authentication. Use fictional details and bind to loopback.
- Existing prompt heuristics and approved composition templates remain in the legacy intake. Owner text is attributed as owner input and does not acquire independent verification.
