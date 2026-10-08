from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict, Field

class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")
class Item(Model):
    garment: Literal["shirt","pants","jacket","dress","skirt","coat","other","unspecified"] = "unspecified"
    garment_detail: str | None = None
    alteration_types: list[Literal["hem","take_in","let_out","sleeve_length","zipper","button","patch","repair","other"]] = Field(default_factory=list)
    material_flags: list[Literal["leather","silk","beaded","lined","formal","stretch","unknown"]] = Field(default_factory=lambda:["unknown"])
class Contact(Model):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
class ExtractedRequest(Model):
    items: list[Item] = Field(default_factory=list)
    deadline_text: str | None = None
    deadline_date: date | None = None
    event: Literal["wedding","interview","prom","graduation","funeral","other","none"] = "none"
    customer_has_garment: bool | Literal["unknown"] = "unknown"
    contact: Contact = Field(default_factory=Contact)
    is_in_scope: bool = True
    notes: str = ""
class HandoffReason(StrEnum):
    PRICE_REQUESTED="PRICE_REQUESTED"
    TURNAROUND_PROMISE_REQUESTED="TURNAROUND_PROMISE_REQUESTED"
    DEADLINE_NEEDS_CONFIRMATION="DEADLINE_NEEDS_CONFIRMATION"
    DEADLINE_VERY_SOON="DEADLINE_VERY_SOON"
    SERVICE_UNKNOWN_OR_UNSUPPORTED="SERVICE_UNKNOWN_OR_UNSUPPORTED"
    SPECIAL_MATERIAL="SPECIAL_MATERIAL"
    GARMENT_NOT_YET_OWNED="GARMENT_NOT_YET_OWNED"
    MISSING_GARMENT_INFO="MISSING_GARMENT_INFO"
    MISSING_CONTACT="MISSING_CONTACT"
    OUT_OF_SCOPE="OUT_OF_SCOPE"
    POSSIBLE_PROMPT_INJECTION="POSSIBLE_PROMPT_INJECTION"
class Fact(Model):
    value: Any = None
    status: Literal["verified","unverified","unknown"] = "unknown"
    source: str | None = None
    retrieved_on: date | None = None
class Business(Model):
    name: Fact
    address: Fact
    phone: Fact
    website: Fact
    hours: Fact
    services_public: Fact
    unsupported_or_unknown_services: Fact
    price_list: Fact
    rush_policy: Fact
    capacity_turnaround: Fact
class Ticket(Model):
    id: str
    created_at: datetime
    status: Literal["PENDING_SHOP_CONFIRMATION"] = "PENDING_SHOP_CONFIRMATION"
    extraction: ExtractedRequest
    handoff_reasons: list[HandoffReason]
    missing_fields: list[str]
    customer_reply: str
    raw_message: str
