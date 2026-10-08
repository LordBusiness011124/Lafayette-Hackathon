import re
from app.compose import SAFE_REPLY, compose
PATTERN=re.compile(r"\$|£|€|\b(?:free|guarantee|guaranteed|will be ready|ready by|we can do|we will|no problem)\b|\b\d+(?:[.,]\d+)?\s*(?:usd|dollars?|euros?|pounds?)\b",re.I)
def violations(reply):
    return [m.group() for m in PATTERN.finditer(reply)]
def guard(reply,reasons=(),missing=()):
    # Allow only deterministic, reviewed templates. This also blocks invented policies
    # and promised dates, including wording a keyword scanner cannot anticipate.
    allowed=compose(reasons,missing)
    return reply if reply==allowed and not violations(reply) else SAFE_REPLY
