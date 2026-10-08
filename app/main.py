from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4
from threading import Lock
from pathlib import Path
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from app.schemas import Model, Ticket
from app.config import ROOT, load_business
from app.extract import extract
from app.policy import evaluate, LABELS
from app.compose import compose
from app.guard import guard
from app.concierge import router as concierge_router
app=FastAPI(title="Julian's Concierge Demo")
app.include_router(concierge_router)
lock=Lock()
class ChatInput(Model):
    message: str = Field(min_length=1,max_length=5000)
def make_ticket(message,now=None,provider=None,business=None):
    now=now or datetime.now(ZoneInfo("America/New_York"))
    business=business or load_business()
    extraction=extract(message,now,provider)
    reasons,missing=evaluate(extraction,business,now,message)
    return Ticket(id=str(uuid4()),created_at=now,extraction=extraction,handoff_reasons=reasons,missing_fields=missing,customer_reply=guard(compose(reasons,missing),reasons,missing),raw_message=message)
@app.post("/chat",response_model=Ticket)
@app.post("/demo",response_model=Ticket)
def chat(body:ChatInput):
    ticket=make_ticket(body.message)
    path=Path(os.getenv("TICKETS_PATH",str(ROOT/"data/tickets.jsonl")))
    with lock:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("a",encoding="utf-8") as file:file.write(ticket.model_dump_json()+"\n")
    return ticket
@app.get("/config")
def config():
    business=load_business()
    return {"facts":business.model_dump(mode="json"),"unknown_fields":[k for k,f in business if f.status!="verified"],"reason_labels":LABELS,"provider":os.getenv("LLM_PROVIDER","mock")}
@app.get("/")
def index():return FileResponse(ROOT/"web/index.html")
@app.get("/intake")
def intake():return FileResponse(ROOT/"web/intake.html")
app.mount("/static",StaticFiles(directory=ROOT/"web"),name="static")
