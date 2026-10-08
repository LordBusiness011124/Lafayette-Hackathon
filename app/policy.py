import re
from app.schemas import HandoffReason as H
from app.dates import resolve_deadline
LABELS={h:h.value.replace("_"," ").capitalize() for h in H}
LABELS[H.DEADLINE_VERY_SOON]="Deadline within two days (demo heuristic)"
LABELS[H.SERVICE_UNKNOWN_OR_UNSUPPORTED]="Service needs tailor review"
LABELS[H.POSSIBLE_PROMPT_INJECTION]="Message contains possible instructions to override safeguards"
def evaluate(extraction,business,now,message):
    e=extraction; t=message.lower(); reasons=[]; missing=[]
    def add(h):
        if h not in reasons: reasons.append(h)
    if re.search(r"price|cost|quote|how much|\$|dollars?|euros?|£|€",t):add(H.PRICE_REQUESTED)
    if re.search(r"promise|guarantee|ready by|turnaround|how long|can you.*(?:by|finish)|will.*ready",t):add(H.TURNAROUND_PROMISE_REQUESTED)
    deadline_text,deadline_date=resolve_deadline(message,now)
    if e.deadline_text or e.deadline_date or deadline_text:add(H.DEADLINE_NEEDS_CONFIRMATION)
    deadline=e.deadline_date or deadline_date
    # Our triage heuristic, never a shop policy. Past deadlines also need urgent human review.
    if deadline and (deadline-now.date()).days<=2:add(H.DEADLINE_VERY_SOON)
    services=business.services_public
    verified=services.value if services.status=="verified" and isinstance(services.value,list) else []
    unsupported=business.unsupported_or_unknown_services.value or []
    if not e.items or any(not i.alteration_types or any(a not in verified or a in unsupported for a in i.alteration_types) for i in e.items):add(H.SERVICE_UNKNOWN_OR_UNSUPPORTED)
    if any(set(i.material_flags)&{"leather","silk","beaded","lined","formal","stretch"} for i in e.items):add(H.SPECIAL_MATERIAL)
    if e.customer_has_garment is False:add(H.GARMENT_NOT_YET_OWNED)
    if not e.items or any(i.garment=="unspecified" or not i.alteration_types for i in e.items):
        add(H.MISSING_GARMENT_INFO); missing.append("garment and alteration details")
    if not (e.contact.email or e.contact.phone):add(H.MISSING_CONTACT);missing.append("phone or email")
    if not e.is_in_scope or re.search(r"dry[ -]?clean|lost my|damaged my|opening hours|where are you",t):add(H.OUT_OF_SCOPE)
    if re.search(r"ignore.*(?:rules|instructions)|system prompt|override|pretend|developer message|you are now|reveal.*prompt",t):add(H.POSSIBLE_PROMPT_INJECTION)
    return reasons,missing
