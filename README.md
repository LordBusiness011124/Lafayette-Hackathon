# Rush Alteration Intake

An independent tailor-intake demo. A customer message becomes a structured ticket and a reply for human review. Every ticket remains `PENDING_SHOP_CONFIRMATION`.

Independent demo built from public information. Not affiliated with the business.

## Run locally

Python 3.11 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
LLM_PROVIDER=mock uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The mock needs no API key. Each submission writes a separate line to `data/tickets.jsonl`. `/demo` accepts the same JSON as `/chat`: `{"message":"Please hem my pants tomorrow"}`. `/docs` has the API interface. Use fictional contact details; ticket storage contains the raw message and contact fields. This is a local demo without authentication, retention controls, or production deployment configuration.

## Test and evaluate

```sh
.venv/bin/python -m pytest -q
.venv/bin/python eval/run_eval.py
```

The evaluation writes `eval/report.md` and exits unsuccessfully on mismatches or claim violations. Its 30 cases are self-authored fictional examples. `curveballs.yaml` contains eight additional demo inputs.

## Providers

`LLM_PROVIDER` accepts `mock` (default), `openai`, or `anthropic`. Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for a live provider. Override models with `OPENAI_MODEL` or `ANTHROPIC_MODEL`. Keys stay on the server. Live adapters are included but have not been tested against paid APIs. The offline mock recognizes a limited English vocabulary; it does not translate. Provider failures retry once and then request human review.

## Architecture

`extract.py` validates provider output using Pydantic. `dates.py` resolves deadlines against an injected New York time. `policy.py` evaluates both extraction and raw input using deterministic rules. `compose.py` uses fixed templates. `guard.py` permits only the exact approved composition and rejects unsafe phrases; arbitrary generated phrasing is never sent. `main.py` creates and saves the ticket. The frontend renders user content as text.

## Business configuration

Edit `config/business.yaml`. Each fact has a value, verification status, source, and retrieval date. Only a verified service list can suppress an unknown-service handoff; use alteration enum values such as `hem` and `sleeve_length`. All requests still need tailor confirmation. The reply conservatively leaves pricing, rush handling, and turnaround to the tailor even if future config records those facts. Swap the config to change the business profile. The UI reads the profile name from the config.

Julian's Tailor Shop is the user-selected demo business. Its address and website are unknown. Phone, website, hours, services, prices, rush policy, capacity, turnaround, and current open status remain unknown. No shop contact was made.

## iPhone demo

The demo runs as a mobile website in Simulator Safari; it does not require a native app build. At narrow widths, Request and Review ticket links stay at the top. Submitting a request moves to the ticket, which shows garments, requested alterations, and the requested deadline. Unknown facts and JSON are expandable.

Start the server, then on a Mac with full Xcode and an installed iOS Simulator runtime:

```sh
bash scripts/ios-demo.sh
```

If only Command Line Tools are selected:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer bash scripts/ios-demo.sh
```

The script boots an available iPhone and opens http://127.0.0.1:8000 in Safari. For a physical iPhone on the same network, start Uvicorn with `--host 0.0.0.0` and open the Mac's local network address with port 8000. Use fictional data and a trusted network for this unauthenticated demo.

Verification on the current Mac uses browser testing at iPhone screen dimensions. Actual iOS Safari verification remains pending because Xcode/Simulator is unavailable.
