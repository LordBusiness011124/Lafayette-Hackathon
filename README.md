# Julian’s Concierge — Owner-driven local demo

An independent hackathon prototype. A customer sends their initial request, and the offline agent creates the owner's ticket, asks for missing details, updates the **same ticket**, and returns it to the owner. The original customer request stays visible in the owner's brief. Owner questions are relayed to the customer and the answer is returned to the owner's inbox. Owner decisions unlock simulated acceptance, payment and fulfillment. Owners can also open an intake themselves.

## Run locally

From this folder (the app lives inside the nested `Lafayette-Hackathon/` directory):

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
LLM_PROVIDER=mock .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000 and click **Play owner workflow** for the seven-step walkthrough. Both inboxes are interactive. On mobile, use Customer / Owner / Operations tabs. No deployment, native build or API key is required.

## Manual owner scenario

1. In Customer, send `I need my pants hemmed by Friday for a wedding`. It appears as a customer message and creates a pants/hem ticket for Owner.
2. The agent asks Customer for a phone or email and tells Owner which fields are missing.
3. In Customer, send `My email is demo@example.com`. The ticket keeps its ID and returns to Owner.
4. In Owner, send `ask customer what material are the pants?`.
5. In Customer, send `The pants are silk`. The material and answer are returned to Owner on the same ticket.
6. Owner sends `quote $45 ready by Friday at 3pm` (fictional demo price). Customer clicks **Simulate payment**.
7. Owner sends `ready — collect Friday`, then `complete — collected`.

Quick-action buttons fill the owner composer; press Send to execute. A quote is blocked while required fields are missing. Payment requires owner confirmation. Ready requires simulated payment; completion requires Ready. An unpaid request can be declined or cancelled. Normal owner messages are relayed without changing status.

For an owner-started request instead, send `intake Alex needs pants hemmed by Friday for a wedding` in Owner. The guided walkthrough starts with the customer's own message.

## Shopping scenario

In Customer, use **Carolina gift** or text `Carolina gift for dad under $160, blue polo size M`. The agent filters a saved public catalog by budget, category, theme, size, color and variant availability. Choose a variant and **Ask owner to confirm**. Owner sends `approve — stock checked; pickup tomorrow at 2pm`; Customer can then simulate payment. No online availability snapshot is treated as store stock.

`catalog/products.json` contains 250 products from the first page of Julian’s public Shopify endpoint, downloaded October 8, 2026. It is a partial catalog, not a live stock feed. Product cards retain official links and images. Images load from the store CDN and require internet; the workflow and saved catalog run locally. Prices exclude tax and shipping.

## What was upgraded

The original FastAPI alteration intake, extraction, deterministic policy evaluation, response guards and 30-case evaluation remain available at `/intake`, `/chat`, and `/demo`. The main page now adds linked customer/owner inboxes, persistent multi-turn sessions, owner-started intake, missing-field follow-up, owner clarification, catalog recommendations, approval/decline, simulated checkout, ready/completed notifications, an activity log and JSON export.

The new workflow is in `app/concierge.py`; the browser uses plain HTML, CSS and JavaScript with no frontend dependencies. Both inboxes are controlled on the same page. Reload restores that browser’s session. **New conversation** creates another session without deleting previous records.

## Verify

```sh
.venv/bin/python -m pytest -q
.venv/bin/python eval/run_eval.py
node --check web/demo.js
```

Tests cover the original intake plus owner/customer detail roundtrips, stable ticket IDs, corrected contact/deadline, material flags, blocked premature quotes/payments/fulfillment, catalog filtering, invalid selection, declines, policy responses and persistence.

## iOS option

This is a responsive website, so iOS Simulator is optional. With a working installed runtime and the server running:

```sh
bash scripts/ios-demo.sh
```

This opens the same localhost app in Simulator Safari. No native app is built. Browser and actual simulator visual verification remain pending in this session because computer control/runtime access was not approved.

## Local demo boundaries

The concierge is **deterministic and offline**, not a live language model. Existing OpenAI/Anthropic adapters apply only to the original intake; the new demo explicitly uses the mock extractor. No real SMS, reservations, appointments, payment, stock deductions or refunds occur. Every owner decision/quote/timing claim is simulated and attributed to the owner. Use fictional customer details.

Sessions live in ignored `data/sessions.json`, original intake submissions in ignored `data/tickets.jsonl`. Run a single process on loopback: the demo has no authentication, roles are simulated, and file persistence is not safe for multiple workers. Garments of the same type are merged in multi-turn intake; separate item IDs and a stronger extractor are needed for several distinct garments of the same type. Arbitrary natural language and correction/removal of previously stated garment changes are not fully supported. The original intake ticket contains its initial pending status; the surrounding session is the workflow state.
