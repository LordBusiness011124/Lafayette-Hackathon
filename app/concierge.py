"""Local, offline customer/owner simulation. No messages or payments leave the demo."""
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from html import unescape
from pathlib import Path
from threading import RLock
from typing import Literal
from uuid import uuid4
import json
import os
import re

from fastapi import APIRouter, HTTPException
from pydantic import Field
from app.config import ROOT
from app.schemas import Model

router = APIRouter(prefix="/api")
lock = RLock()
SOURCE = "https://julianschapelhill.com/products.json?limit=250"
FETCHED = "2026-10-08"
ACTIVE = {"NEEDS_CUSTOMER_DETAILS", "AWAITING_OWNER", "PAYMENT_PENDING", "PAID", "READY"}
ALTERATION_INTENT = re.compile(r"\b(?:hem(?:s|med|ming)?|alter(?:s|ed|ing|ations?)?|shorten(?:s|ed|ing)?|repair(?:s|ed|ing)?|tailor(?:s|ed|ing)?|zipper|tak(?:e|en|ing)\s+in|let\s+out)\b")


@lru_cache
def catalog():
    products = json.loads((ROOT / "catalog/products.json").read_text())["products"]
    return [{
        "id": str(p["id"]), "title": p["title"], "type": p["product_type"],
        "brand": p["vendor"], "description": unescape(re.sub(r"<[^>]+>", " ", p["body_html"] or "")),
        "tags": p["tags"], "url": "https://julianschapelhill.com/products/" + p["handle"],
        "image": p["images"][0]["src"] if p["images"] else None,
        "variants": [{"id": str(v["id"]), "title": v["title"], "price": v["price"],
                      "available": v["available"]} for v in p["variants"]],
        "price": min(Decimal(v["price"]) for v in p["variants"]).__str__(),
    } for p in products if p["variants"]]


def store_path():
    return Path(os.getenv("CONCIERGE_PATH", str(ROOT / "data/sessions.json")))


def read_store():
    path = store_path()
    return json.loads(path.read_text()) if path.exists() else {}


def save_store(store):
    # ponytail: one local server process; use a database before running multiple workers.
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(store, indent=2), encoding="utf-8")
    temp.replace(path)


def get_session(store, sid):
    if sid not in store:
        raise HTTPException(404, "Conversation not found. Start a new demo.")
    return store[sid]


def now():
    return datetime.now().astimezone().isoformat()


def say(s, lane, sender, text):
    s["messages"].append({"id": str(uuid4()), "lane": lane, "sender": sender, "text": text, "at": now()})


def event(s, text):
    s["events"].append({"at": now(), "text": text})


def handoff(s, text):
    s["status"] = "AWAITING_OWNER"
    say(s, "owner", "agent", text)
    event(s, "Agent handed the request to the owner; waiting for a decision.")


def alteration_intake(s, text, origin="customer"):
    from app.main import make_ticket
    from app.llm.mock import MockProvider
    from app.schemas import ExtractedRequest
    from app.policy import evaluate
    from app.compose import compose
    from app.guard import guard
    from app.config import load_business
    from app.dates import resolve_deadline
    previous = s.get("ticket")
    if not previous or s["kind"] != "alteration":
        s["initial_request"] = text
        s["request_origin"] = origin
    combined = previous["raw_message"] + "\nCustomer follow-up: " + text if previous and s["kind"] == "alteration" else text
    ticket = make_ticket(combined, provider=MockProvider()).model_dump(mode="json")
    if previous and s["kind"] == "alteration":
        ticket["id"] = previous["id"]
        ticket["created_at"] = previous["created_at"]
    # ponytail: repeated references to the same garment type are one demo item;
    # use explicit item IDs when handling several separate garments of the same type.
    merged = {}
    for item in ticket["extraction"]["items"]:
        if item["garment"] not in merged:
            merged[item["garment"]] = item
        else:
            for field in ["alteration_types", "material_flags"]:
                merged[item["garment"]][field] = list(dict.fromkeys(merged[item["garment"]][field] + item[field]))
    ticket["extraction"]["items"] = list(merged.values())
    current = make_ticket(text, provider=MockProvider()).model_dump(mode="json")["extraction"]
    for key, value in current["contact"].items():
        if value:
            ticket["extraction"]["contact"][key] = value
        elif previous:
            ticket["extraction"]["contact"][key] = previous["extraction"]["contact"][key]
    deadline_text, deadline_date = resolve_deadline(text, datetime.now().astimezone())
    if deadline_text:
        ticket["extraction"]["deadline_text"] = deadline_text
        ticket["extraction"]["deadline_date"] = deadline_date.isoformat() if deadline_date else None
    elif previous:
        for key in ["deadline_text", "deadline_date"]:
            ticket["extraction"][key] = previous["extraction"][key]
    reasons, missing = evaluate(ExtractedRequest.model_validate(ticket["extraction"]), load_business(), datetime.now().astimezone(), combined)
    ticket["handoff_reasons"] = [r.value for r in reasons]
    ticket["missing_fields"] = missing
    ticket["customer_reply"] = guard(compose(reasons, missing), reasons, missing)
    s["kind"] = "alteration"
    s["ticket"] = ticket
    s["selected"] = None
    s["recommendations"] = []
    s["quote"] = None
    s["payment"] = None
    s["missing_details"] = ticket["missing_fields"]
    e = ticket["extraction"]
    brief = "Ticket " + ticket["id"][:8] + " updated\nGarments: " + "; ".join(i["garment"] + " — " + (", ".join(i["alteration_types"]) or "changes unspecified") for i in e["items"])
    original = s.get("initial_request") or combined.split("\nCustomer follow-up:", 1)[0]
    brief += "\nOriginal request (" + s.get("request_origin", "customer") + "): " + original
    brief += "\nRequested deadline: " + (e["deadline_text"] or "not specified") + "\nContact: " + json.dumps(e["contact"])
    brief += "\nReview flags: " + ", ".join(r.replace("_", " ").lower() for r in ticket["handoff_reasons"])
    if ticket["missing_fields"]:
        s["status"] = "NEEDS_CUSTOMER_DETAILS"
        question = "To complete your ticket for the owner, could you share " + " and ".join(ticket["missing_fields"]) + "? Your answer will update this same ticket."
        say(s, "customer", "agent", question)
        say(s, "owner", "agent", brief + "\nMissing: " + ", ".join(ticket["missing_fields"]) + ". I’ve asked the customer and will bring their answer back here.")
        event(s, "Agent detected missing ticket fields and requested them from the customer.")
    else:
        handoff(s, brief + "\nRequired intake details collected. You can ask another question with 'ask …', send 'quote $45 ready by Friday' (example only), or decline.")
        say(s, "customer", "agent", "Your ticket details are collected and sent to the owner. Pricing, service feasibility and timing still need their confirmation.")
        event(s, "Same ticket updated with customer details and returned to the owner.")


class MessageInput(Model):
    role: Literal["customer", "owner"]
    message: str = Field(min_length=1, max_length=5000)


class SelectionInput(Model):
    product_id: str
    variant_id: str


def update_preferences(profile, text):
    t = text.lower()
    budget = re.search(r"(?:under|budget(?:\s+is)?|up to|less than|max(?:imum)?|around)\s*\$?\s*(\d+(?:\.\d{1,2})?)", t)
    budget = budget or re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", t)
    if budget:
        profile["budget"] = budget[1]
    for occasion in ["graduation", "wedding", "interview", "birthday", "gameday", "anniversary"]:
        if occasion in t:
            profile["occasion"] = occasion
    if re.search(r"unc|carolina|tar heel|old well|argyle", t):
        profile["theme"] = "Carolina"
    if re.search(r"no (?:unc|carolina)|not carolina", t):
        profile.pop("theme", None)
    for word in ["dad", "mom", "father", "mother", "partner", "friend", "myself"]:
        if re.search(r"\b" + word + r"\b", t):
            profile["recipient"] = word
    categories = {"shirt": r"\b(?:shirt|shirts|polo|polos)\b", "blazer": r"\bblazer\b", "socks": r"\bsocks?\b", "tie": r"\b(?:tie|necktie)\b", "gift": r"\baccessor(?:y|ies)\b"}
    for category, pattern in categories.items():
        if re.search(pattern, t):
            profile["category"] = category
    if re.search(r"anything|any type|any category", t):
        profile.pop("category", None)
    for color in ["navy", "white", "black", "blue", "brown", "green"]:
        if re.search(r"\b" + color + r"\b", t):
            profile["color"] = color
    sizes = {"small": "S", "medium": "M", "large": "L", "extra large": "XL", "xxl": "XXL", "xxxl": "XXXL", "xs": "XS"}
    for word, value in sizes.items():
        if re.search(r"\b" + word + r"\b", t):
            profile["size"] = value
    match = re.search(r"\b(?:size\s*)?(XS|S|M|L|XL|XXL|XXXL)\b", text)
    if match:
        profile["size"] = match[1]
    if "pickup" in t or "pick up" in t:
        profile["fulfillment"] = "pickup"
    elif "ship" in t or "delivery" in t:
        profile["fulfillment"] = "shipping"
    deadline = re.search(r"(?:today|tomorrow|this afternoon|(?:by|on)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))", t)
    if deadline:
        profile["requested_timing"] = deadline[0]


def matching_variants(product, profile):
    result = []
    for v in product["variants"]:
        if not v["available"]:
            continue
        if profile.get("budget") and Decimal(v["price"]) > Decimal(profile["budget"]):
            continue
        if profile.get("size") and not re.search(r"(?:^|\s|/)" + re.escape(profile["size"]) + r"(?:$|\s|/)", v["title"], re.I):
            continue
        if profile.get("color"):
            aliases = {"blue": r"blue", "navy": r"navy"}
            if not re.search(aliases.get(profile["color"], re.escape(profile["color"])), v["title"], re.I):
                continue
        result.append(v)
    return result


def recommend(profile):
    results = []
    for p in catalog():
        haystack = (p["title"] + " " + p["type"] + " " + " ".join(p["tags"])).lower()
        if profile.get("theme") and not re.search(r"carolina|old well|argyle|unc\b|true blues", haystack):
            continue
        category = profile.get("category")
        patterns = {"shirt": r"shirt|polo", "blazer": r"blazer", "socks": r"sock", "tie": r"necktie", "gift": r"tie|sock|tote|tumbler|pin|cufflink|wallet|tray|cooler"}
        if category and not re.search(patterns[category], p["type"].lower() + " " + p["title"].lower()):
            continue
        variants = matching_variants(p, profile)
        if variants:
            best = min(variants, key=lambda v: Decimal(v["price"]))
            reasons = ["Listed as available in the Oct 8 catalog snapshot"]
            if profile.get("budget"):
                reasons.append(f"${best['price']} fits your ${profile['budget']} budget before tax/shipping")
            for key in ["theme", "size", "color", "category"]:
                if profile.get(key):
                    reasons.append(f"Matches {key}: {profile[key]}")
            results.append({**p, "variants": variants, "price": best["price"], "reasons": reasons})
    # Consistent demo ordering: Carolina staples first, then price.
    results.sort(key=lambda p: (not ("old well" in p["title"].lower() and "polo" in p["title"].lower()), Decimal(p["price"])))
    return results[:6]


def customer_message(s, text):
    t = text.lower()
    if re.search(r"return|refund|exchange", t):
        say(s, "customer", "agent", "Julian’s publishes a 30-day return/exchange policy. Worn, soiled, altered, customized, final-sale, special-order and custom-tailored goods are excluded. Custom tailoring includes 90 days of complimentary alterations. Source: https://julianschapelhill.com/policies/refund-policy. For a specific order, ask the owner to review; this demo cannot issue a real refund.")
        return
    if re.search(r"discount|coupon|% off", t):
        say(s, "customer", "agent", "I can’t approve an unpublished discount. I’ve passed your question to the owner in the demo.")
        say(s, "owner", "agent", "Customer asks about a discount: " + text + ". Please reply to clarify; no discount has been applied.")
        event(s, "Discount question escalated; prices unchanged.")
        return
    if re.search(r"\b(?:what(?:'s| is| are)?|where|when|tell me|give me|show me)\b.*\b(?:hours|address|location|phone)\b|where are you|opening hours", t):
        say(s, "customer", "agent", "Julian’s lists 135 E Franklin St, Chapel Hill; Tuesday–Saturday, 10am–5pm; (919) 942-4563. Source: https://julianschapelhill.com/. These are published hours, not a confirmation of today’s operating status.")
        return
    if re.search(r"\bcancel\b", t):
        if s["status"] in {"NEEDS_CUSTOMER_DETAILS", "AWAITING_OWNER", "PAYMENT_PENDING"}:
            s["status"] = "CANCELLED"
            say(s, "customer", "agent", "Your demo request is cancelled. No payment was taken.")
            say(s, "owner", "agent", "Customer cancelled this unpaid request.")
            event(s, "Customer cancelled the unpaid request.")
        else:
            say(s, "customer", "agent", "For a paid or completed request, the owner needs to review cancellation. I’ve sent them your message.")
            say(s, "owner", "agent", "Cancellation review requested: " + text)
        return
    if s["status"] == "NEEDS_CUSTOMER_DETAILS":
        question = s.get("owner_question")
        if question:
            say(s, "owner", "agent", "Customer answered your question: " + question + "\nAnswer: " + text)
            s["owner_question"] = None
            event(s, "Customer answer relayed to the owner and attached to the request.")
        if s["kind"] == "alteration":
            alteration_intake(s, text)
        else:
            update_preferences(s["preferences"], text)
            s["missing_details"] = []
            handoff(s, "Customer details received: " + text + "\nUpdated brief: " + json.dumps(s["preferences"]) + ". Review the selected item before approving.")
            say(s, "customer", "agent", "Thanks. I’ve updated your request and returned your answer to the owner for review.")
        return
    if s["kind"] == "alteration" and s["status"] == "AWAITING_OWNER":
        alteration_intake(s, text)
        return
    if s["status"] in ACTIVE:
        say(s, "owner", "agent", "Customer follow-up: " + text)
        say(s, "customer", "agent", "I’ve passed that to the owner. Your request is " + s["status"].lower().replace("_", " ") + ".")
        event(s, "Customer follow-up forwarded to the owner.")
        return
    if ALTERATION_INTENT.search(t):
        if s["status"] in {"COMPLETED", "DECLINED", "CANCELLED"}:
            s["ticket"] = None
        alteration_intake(s, text)
        return
    if re.search(r"can i (?:pick|collect)|ready by|available today", t):
        say(s, "customer", "agent", "Online availability does not confirm store stock or pickup timing. Choose an item and I’ll ask the owner to confirm in the demo.")
    update_preferences(s["preferences"], text)
    s["recommendations"] = recommend(s["preferences"])
    s["kind"] = "shopping"
    s["status"] = "DISCOVERY"
    if s["recommendations"]:
        prompt = " What’s your budget?" if not s["preferences"].get("budget") else ""
        say(s, "customer", "agent", f"I found {len(s['recommendations'])} matching options in the saved public catalog.{prompt} Choose a size/color on a product card, then ask the owner to confirm. Prices exclude tax and shipping; availability is a snapshot.")
        event(s, "Catalog filtered using budget, theme, category, size and color; " + str(len(s["recommendations"])) + " matches.")
    else:
        say(s, "customer", "agent", "I couldn’t verify a match in the 250 products loaded for this demo. Try a different budget, size or category. This is a partial catalog, so it does not mean the store has no options.")
        event(s, "No matching variant in the loaded catalog; no product invented.")


def owner_message(s, text):
    t = text.lower().strip()
    if re.match(r"^intake\b", t):
        if s["status"] in ACTIVE:
            say(s, "owner", "agent", "Finish or decline the current request before opening another intake.")
            return
        detail = re.sub(r"^intake\s*[:—-]?\s*", "", text, flags=re.I)
        if not detail:
            say(s, "owner", "agent", "Describe the customer’s request after intake, e.g. intake Alex needs pants hemmed by Friday.")
            return
        s["ticket"] = None
        say(s, "customer", "agent", "The owner opened an intake for you in this simulation: " + detail)
        event(s, "Owner opened an incomplete customer ticket; agent started follow-up.")
        alteration_intake(s, detail, origin="owner")
    elif re.match(r"^ask\b", t):
        if s["status"] not in {"AWAITING_OWNER", "NEEDS_CUSTOMER_DETAILS"}:
            say(s, "owner", "agent", "Ask for details on a request awaiting review. For other updates, type your message without an action prefix.")
            return
        question = re.sub(r"^ask\s+(?:(?:the\s+)?customer\s*)?[:—-]?\s*", "", text, flags=re.I).strip()
        if not question:
            say(s, "owner", "agent", "Add a question after ask, e.g. ask what is the garment’s material?")
            return
        s["owner_question"] = question
        s["status"] = "NEEDS_CUSTOMER_DETAILS"
        say(s, "customer", "agent", "The owner needs one more detail: " + question)
        say(s, "owner", "agent", "Question sent. I’ll collect the answer and update this same request.")
        event(s, "Owner requested clarification; agent texted the customer in the simulation.")
    elif re.match(r"^(approve|confirm)\b", t):
        if s["status"] != "AWAITING_OWNER" or not s["selected"]:
            say(s, "owner", "agent", "Approval needs a selected product awaiting owner confirmation. For alterations, reply with a quote, e.g. quote $45 ready by Friday.")
            return
        if s["preferences"].get("budget") and Decimal(s["selected"]["variant"]["price"]) > Decimal(s["preferences"]["budget"]):
            say(s, "owner", "agent", "The selected item exceeds the customer’s updated budget. Decline this selection and ask them to choose another item.")
            return
        s["quote"] = {"amount": s["selected"]["variant"]["price"], "details": text, "source": "Catalog price; owner confirmed in simulation"}
        s["status"] = "PAYMENT_PENDING"
        say(s, "owner", "agent", "Confirmation recorded. I’ve sent the customer the item price and your message. They can simulate checkout.")
        say(s, "customer", "agent", "Owner confirmed in this simulation: " + text + f"\nItem subtotal: ${s['quote']['amount']}. You can now simulate payment; no money will move.")
        event(s, "Owner confirmed item and fulfillment; simulated checkout unlocked.")
    elif re.match(r"^quote\b", t):
        amount = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", t)
        if s["status"] != "AWAITING_OWNER" or s["kind"] != "alteration" or not amount or Decimal(amount[1]) <= 0:
            say(s, "owner", "agent", "A quote needs an alteration awaiting review and a positive amount, e.g. quote $45 ready by Friday.")
            return
        s["quote"] = {"amount": str(Decimal(amount[1]).quantize(Decimal(".01"))), "details": text, "source": "Owner-entered demo quote, not a published shop price"}
        s["status"] = "PAYMENT_PENDING"
        say(s, "customer", "agent", "Owner’s simulated quote: " + text + ". Review it, then use Simulate payment to accept. No real appointment or charge is created.")
        say(s, "owner", "agent", "Quote sent to the customer for acceptance.")
        event(s, "Owner provided a demo alteration quote; checkout unlocked.")
    elif re.match(r"^(decline|reject)\b", t):
        if s["status"] not in {"NEEDS_CUSTOMER_DETAILS", "AWAITING_OWNER", "PAYMENT_PENDING"}:
            say(s, "owner", "agent", "Only an unpaid pending request can be declined. Paid requests need separate refund review.")
            return
        s["status"] = "DECLINED"
        say(s, "customer", "agent", "Owner declined this demo request: " + text + ". No charge was made. You can try another item or start a new request.")
        say(s, "owner", "agent", "Decline recorded and customer notified.")
        event(s, "Owner declined; no payment recorded.")
    elif re.match(r"^ready\b", t):
        if s["status"] != "PAID":
            say(s, "owner", "agent", "Mark ready after the customer has simulated payment.")
            return
        s["status"] = "READY"
        say(s, "customer", "agent", "Owner update in the simulation: " + text)
        say(s, "owner", "agent", "Ready notification delivered to the customer demo inbox.")
        event(s, "Owner marked request ready and customer was notified.")
    elif re.match(r"^(complete|collected|shipped)\b", t):
        if s["status"] != "READY":
            say(s, "owner", "agent", "Mark ready first, then complete after simulated collection or shipment.")
            return
        s["status"] = "COMPLETED"
        say(s, "customer", "agent", "Your demo request is complete. Owner update: " + text + ". Thank you for shopping with Julian’s in this independent simulation.")
        say(s, "owner", "agent", "Request closed. The activity log records the full handoff.")
        event(s, "Fulfillment complete; request closed.")
    else:
        say(s, "customer", "agent", "Message from the owner in this simulation: " + text)
        say(s, "owner", "agent", "I’ve relayed your message. To change status, start with approve, quote $…, decline, ready, or complete.")
        event(s, "Owner message relayed; order status unchanged.")


@router.get("/catalog")
def list_catalog():
    return {"products": catalog(), "source": SOURCE, "fetched_on": FETCHED, "partial": True}


@router.post("/sessions")
def create_session():
    s = {"id": str(uuid4()), "status": "DISCOVERY", "kind": "shopping", "preferences": {},
         "messages": [], "events": [], "recommendations": [], "selected": None, "quote": None, "ticket": None,
         "payment": None, "catalog_date": FETCHED, "missing_details": [], "owner_question": None,
         "initial_request": None, "request_origin": None}
    say(s, "customer", "agent", "Welcome to Julian’s Concierge. Who are you shopping for, what’s the occasion, and what’s your budget? I can also prepare an alteration request for owner review.")
    say(s, "owner", "agent", "Your demo inbox is connected. Customer requests appear here when an item needs confirmation or an alteration needs a quote. All messages stay on this computer.")
    event(s, "Local demo conversation started. Agent runs offline.")
    with lock:
        store = read_store()
        store[s["id"]] = s
        save_store(store)
    return s


@router.get("/sessions/{sid}")
def session(sid: str):
    with lock:
        return get_session(read_store(), sid)


@router.post("/sessions/{sid}/messages")
def message(sid: str, body: MessageInput):
    text = body.message.strip()
    if not text:
        raise HTTPException(422, "Message cannot be blank.")
    with lock:
        store = read_store()
        s = get_session(store, sid)
        say(s, body.role, body.role, text)
        (customer_message if body.role == "customer" else owner_message)(s, text)
        save_store(store)
        return s


@router.post("/sessions/{sid}/select")
def select(sid: str, body: SelectionInput):
    with lock:
        store = read_store()
        s = get_session(store, sid)
        if s["status"] in ACTIVE:
            raise HTTPException(409, "Finish or cancel the active request before selecting another item.")
        product = next((p for p in s["recommendations"] if p["id"] == body.product_id), None)
        variant = next((v for v in product["variants"] if v["id"] == body.variant_id), None) if product else None
        if not variant or not variant["available"]:
            raise HTTPException(422, "Choose an available variant from the current recommendations.")
        s["kind"] = "shopping"
        s["selected"] = {"product": {k: product[k] for k in ["id", "title", "url", "image"]}, "variant": variant}
        s["quote"] = None
        s["payment"] = None
        fulfillment = s["preferences"].get("fulfillment", "pickup")
        timing = s["preferences"].get("requested_timing", "not specified")
        say(s, "customer", "customer", f"Please ask the owner to confirm {product['title']} — {variant['title']} (${variant['price']}).")
        handoff(s, f"Please confirm stock and fulfillment for {product['title']}\nVariant: {variant['title']} · listed price ${variant['price']}\nCustomer preferences: {json.dumps(s['preferences'])}\nFulfillment: {fulfillment}; requested timing: {timing}. Snapshot availability is not store stock. Reply approve with timing, or decline with a reason.")
        say(s, "customer", "agent", "I’ve asked the owner to confirm the item and timing. Checkout stays locked until they approve in the demo.")
        save_store(store)
        return s


@router.post("/sessions/{sid}/pay")
def pay(sid: str):
    with lock:
        store = read_store()
        s = get_session(store, sid)
        if s["status"] != "PAYMENT_PENDING" or not s["quote"]:
            raise HTTPException(409, "Payment requires an owner-confirmed item or quote.")
        s["payment"] = {"reference": "DEMO-" + uuid4().hex[:8].upper(), "amount": s["quote"]["amount"], "simulated": True}
        s["status"] = "PAID"
        say(s, "customer", "agent", f"Simulated payment recorded: ${s['payment']['amount']} · {s['payment']['reference']}. No real charge. The owner will update you when it’s ready.")
        say(s, "owner", "agent", f"Customer accepted and simulated payment of ${s['payment']['amount']}. Prepare the item or alteration, then reply ready with collection/shipping details.")
        event(s, "Simulated payment recorded; owner notified to begin fulfillment.")
        save_store(store)
        return s
