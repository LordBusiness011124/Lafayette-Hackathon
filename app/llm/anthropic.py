import os
import httpx
from app.schemas import ExtractedRequest
from app.llm.openai import SYSTEM
class AnthropicProvider:
    def extract(self,message,now):
        response=httpx.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":os.environ["ANTHROPIC_API_KEY"],"anthropic-version":"2023-06-01"},json={"model":os.getenv("ANTHROPIC_MODEL","claude-sonnet-4-20250514"),"max_tokens":2000,"system":SYSTEM,"messages":[{"role":"user","content":message}],"tools":[{"name":"extract","description":"Extract request","input_schema":ExtractedRequest.model_json_schema()}],"tool_choice":{"type":"tool","name":"extract"}},timeout=30)
        response.raise_for_status()
        return next(c["input"] for c in response.json()["content"] if c["type"]=="tool_use")
