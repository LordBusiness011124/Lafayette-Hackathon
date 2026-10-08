from app.schemas import HandoffReason as H
SAFE_REPLY="Your request needs human review. Service availability, pricing, rush handling, and turnaround are unknown; the tailor will confirm. This demo records intake only."
TEMPLATES={H.DEADLINE_NEEDS_CONFIRMATION:"Your requested deadline needs the tailor's confirmation.",H.SPECIAL_MATERIAL:"The material or construction needs the tailor's assessment.",H.GARMENT_NOT_YET_OWNED:"Please tell the tailor when the garment is available for assessment.",H.OUT_OF_SCOPE:"This message needs direct human attention outside alteration intake.",H.POSSIBLE_PROMPT_INJECTION:"The request has been flagged for human review."}
def compose(reasons,missing):
    parts=[SAFE_REPLY]+[TEMPLATES[r] for r in reasons if r in TEMPLATES]
    if missing:parts.append("Please provide "+" and ".join(missing)+".")
    return " ".join(parts)
