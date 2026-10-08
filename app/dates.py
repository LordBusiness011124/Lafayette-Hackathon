import re
from datetime import date, timedelta
WEEKDAYS = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
def resolve_deadline(message, now):
    text = message.lower()
    iso = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if iso:
        try: return iso.group(), date.fromisoformat(iso.group())
        except ValueError: return iso.group(), None
    if "tomorrow" in text: return "tomorrow", now.date()+timedelta(days=1)
    if "today" in text: return "today", now.date()
    if "this weekend" in text:
        return "this weekend", now.date()+timedelta(days=(5-now.weekday())%7)
    for i, day in enumerate(WEEKDAYS):
        match = re.search(r"\b(?:(next|this)\s+)?"+day+r"\b",text)
        if match:
            delta=(i-now.weekday())%7
            if match.group(1)=="next": delta += 7
            return match.group(),now.date()+timedelta(days=delta)
    match = re.search(r"\b(soon|asap|urgent|rush)\b",text)
    return (match.group(),None) if match else (None,None)
