import os
from app.schemas import ExtractedRequest
from app.dates import resolve_deadline
from app.llm.mock import MockProvider
from app.llm.openai import OpenAIProvider
from app.llm.anthropic import AnthropicProvider
PROVIDERS={"mock":MockProvider,"openai":OpenAIProvider,"anthropic":AnthropicProvider}
def extract(message,now,provider=None):
    provider=provider or PROVIDERS[os.getenv("LLM_PROVIDER","mock")]()
    for attempt in range(2):
        try:
            raw=provider.extract(message,now)
            result=ExtractedRequest.model_validate_json(raw) if isinstance(raw,str) else ExtractedRequest.model_validate(raw)
            result.deadline_text,result.deadline_date=resolve_deadline(message,now)
            return result
        except Exception:
            pass
    return ExtractedRequest(is_in_scope=False,deadline_text=resolve_deadline(message,now)[0],notes="Extraction failed after two attempts; needs human review.")
