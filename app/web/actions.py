"""Validate every action payload before domain processing."""

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Home(Payload):
    home: dict[
        Literal["distance", "light", "use", "seating", "problem", "placement", "budget"], str
    ]


class Selection(Payload):
    products: list[str] = Field(min_length=1, max_length=3)


class Preferred(Payload):
    product: str


class Demo(Payload):
    preferred: str
    reason: str = Field(min_length=5, max_length=1000)


class Site(Payload):
    placement: Literal["Wall", "Table"]
    specialist: Literal["yes", "no", "unknown"]
    power: str = Field(min_length=1, max_length=500)
    cable_route: str = Field(min_length=1, max_length=500)
    access: str = Field(min_length=1, max_length=500)
    devices: str = Field(min_length=1, max_length=500)
    notes: str = Field(min_length=5, max_length=1000)


class Extras(Payload):
    extras: list[Literal["soundbar", "protection"]] = Field(max_length=2)


class Payment(Payload):
    method: Literal["full", "finance"]


class Sale(Payload):
    confirmed_total: int = Field(ge=1)


class Consent(Payload):
    given: StrictBool


class Followup(Payload):
    consent: StrictBool
    due_at: str = Field(max_length=100)
    reason: str = Field(min_length=3, max_length=1000)
    owner: str = Field(min_length=2, max_length=100)


class Language(Payload):
    language: Literal["English", "Hindi", "Marathi"]


class Note(Payload):
    text: str = Field(min_length=1, max_length=3000)


class HomeAnswer(Payload):
    field: Literal["distance", "light", "use", "seating", "problem", "placement", "budget"]
    value: str = Field(min_length=1, max_length=500)


class DemoUnavailable(Payload):
    reason: str = Field(default="Display unavailable", min_length=3, max_length=1000)


class DemoFocus(Payload):
    focus: str = Field(default="", max_length=500)


class Correction(Payload):
    reason: str = Field(min_length=10, max_length=1000)


SCHEMAS = {
    "correction": Correction,
    "start_demo": DemoFocus,
    "home": Home,
    "select": Selection,
    "preferred": Preferred,
    "demo": Demo,
    "site": Site,
    "extras": Extras,
    "payment": Payment,
    "sale": Sale,
    "consent": Consent,
    "followup": Followup,
    "language": Language,
    "note": Note,
    "home_answer": HomeAnswer,
    "demo_unavailable": DemoUnavailable,
    **{
        k: Payload
        for k in (
            "confirm_home",
            "end_visit",
            "ask_home",
            "offers",
            "continue_flow",
            "ask_expert",
            "expert_resolved",
            "explain_another",
        )
    },
}


def validate(action, data):
    schema = SCHEMAS.get(action)
    if not schema:
        raise HTTPException(422, "Unknown workflow action")
    try:
        result = schema.model_validate(data).model_dump()
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    if action == "home" and any(len(v) > 500 for v in result["home"].values()):
        raise HTTPException(422, "Home answers must be at most 500 characters")
    return result
