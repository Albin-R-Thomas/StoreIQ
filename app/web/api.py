import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.web import domain, flow, intelligence
from app.web.store import audit, get, now, password_hash, put, read_all, transaction, uid

router = APIRouter(prefix="/api")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    phone: str = Field(min_length=10, max_length=15, pattern=r"^\+?\d+$")
    password: str = Field(min_length=1, max_length=200)


class NewCustomer(Input):
    name: str = Field(default="", max_length=100)


class TextInput(Input):
    text: str = Field(min_length=1, max_length=4000)
    request_id: str = Field(
        default_factory=uid, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$"
    )
    expected_version: int | None = Field(default=None, ge=1)


class MessageReceipt(Input):
    status: Literal["processing"]
    request_id: str
    acknowledgement: str
    status_url: str


class Action(Input):
    action: str = Field(max_length=40)
    version: int = Field(ge=1)
    data: dict = Field(default_factory=dict)


class Compare(Input):
    customer_id: str | None = None
    products: list[str] = Field(min_length=2, max_length=3)


class Product(Input):
    id: str = Field(max_length=80)
    brand: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=100)
    size: int = Field(ge=24, le=120)
    panel: Literal["LED", "QLED", "OLED", "Mini LED"]
    price: int = Field(ge=1, le=2000000)
    refresh_rate: int = Field(ge=24, le=240)
    brightness: int = Field(ge=50, le=10000)
    sound: int = Field(ge=1, le=500)
    os: str = Field(max_length=60)
    stock: int = Field(ge=0, le=10000)
    viewing_angle: Literal["wide", "standard"]
    scene: str = Field(max_length=30)
    features: list[str] = Field(max_length=20)
    resolution: str = Field(max_length=60)
    hdmi_ports: int = Field(ge=1, le=10)
    warranty: str = Field(max_length=1000)
    description: str = Field(max_length=2000)
    expected_on: str | None = None
    version: int = Field(ge=1)
    mock: bool = True

    @model_validator(mode="after")
    def valid_date(self):
        if self.expected_on:
            datetime.strptime(self.expected_on, "%Y-%m-%d")
        if any(len(x) > 100 for x in self.features):
            raise ValueError("Feature text too long")
        return self


class Offer(Input):
    id: str = Field(max_length=80)
    title: str = Field(min_length=1, max_length=100)
    starts_on: str
    ends_on: str
    discount: int = Field(ge=0, le=100000)
    brands: list[str] = Field(min_length=1, max_length=20)
    min_size: int = Field(ge=24, le=120)
    conditions: str = Field(max_length=2000)
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def dates(self):
        start = datetime.strptime(self.starts_on, "%Y-%m-%d")
        end = datetime.strptime(self.ends_on, "%Y-%m-%d")
        if end < start:
            raise ValueError("Offer ends before it starts")
        return self


class Knowledge(Input):
    id: str = Field(max_length=100)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=20, max_length=20000)
    version: int = Field(ge=1)


class Commercial(Input):
    id: Literal["terms"]
    version: int = Field(ge=1)
    delivery: int = Field(ge=0, le=100000)
    installation: int = Field(ge=0, le=100000)
    wall_mount: int = Field(ge=0, le=100000)
    specialist_work: int | None = Field(ge=0, le=100000)
    soundbar: int = Field(ge=0, le=100000)
    protection: int = Field(ge=0, le=100000)
    finance_months: int = Field(ge=1, le=36)
    finance_fee: int = Field(ge=0, le=100000)
    finance_apr: Literal[0]
    soundbar_description: str = Field(default="", max_length=2000)
    protection_description: str = Field(default="", max_length=2000)


def public_user(user):
    return {k: user[k] for k in ("id", "name", "phone", "role")}


def rate_limit(key, maximum=30):
    window = int(time.time() // 60)
    with transaction() as db:
        row = db.execute("SELECT window,count FROM rate_limits WHERE key=?", (key,)).fetchone()
        count = row["count"] + 1 if row and row["window"] == window else 1
        if count > maximum:
            raise HTTPException(429, "Too many requests. Please wait a minute.")
        db.execute(
            "INSERT INTO rate_limits VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET "
            "window=excluded.window,count=excluded.count",
            (key, window, count),
        )
        db.execute("DELETE FROM rate_limits WHERE window<?", (window - 5,))


def identity(request: Request):
    token = request.cookies.get("storeiq_session", "")
    with transaction() as db:
        session = get(db, "auth", hashlib.sha256(token.encode()).hexdigest())
        if not session or session["expires_at"] < now():
            raise HTTPException(401, "Please sign in")
        user = get(db, "users", session["user_id"])
    if not user:
        raise HTTPException(401, "Account unavailable")
    return public_user(user)


User = Annotated[dict, Depends(identity)]


def admin(user):
    if user["role"] != "admin":
        raise HTTPException(403, "Store admin access required")


@router.post("/auth/login")
def login(body: Login, request: Request, response: Response):
    rate_limit("login:" + (request.client.host if request.client else "local"), 10)
    with transaction() as db:
        user = next(
            (u for u in read_all(db, "users") if u["phone"] == body.phone.removeprefix("+91")), None
        )
        salt = user["salt"] if user else "00" * 16
        candidate = password_hash(body.password, salt)
        if not user or not hmac.compare_digest(candidate, user["password"]):
            raise HTTPException(401, "Phone or password is incorrect")
        token = uid() + uid()
        put(
            db,
            "auth",
            {
                "id": hashlib.sha256(token.encode()).hexdigest(),
                "user_id": user["id"],
                "expires_at": (datetime.now(UTC) + timedelta(hours=12)).isoformat(),
            },
        )
        audit(db, user["id"], "login", user["id"])
    response.set_cookie(
        "storeiq_session",
        token,
        httponly=True,
        samesite="strict",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        max_age=43200,
    )
    return public_user(user)


@router.get("/auth/me")
def me(user: User):
    return user


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    with transaction() as db:
        db.execute(
            "DELETE FROM records WHERE kind='auth' AND id=?",
            (hashlib.sha256(request.cookies.get("storeiq_session", "").encode()).hexdigest(),),
        )
    response.delete_cookie("storeiq_session")
    return {"ok": True}


def reminder_cycle(db):
    for item in read_all(db, "requests"):
        if item["status"] in ["answered", "resolved"]:
            continue
        elapsed = (datetime.now(UTC) - datetime.fromisoformat(item["cycle_at"])).total_seconds()
        for threshold, key, title in [
            (120, "reminded", "Expert request needs a reply"),
            (300, "escalated", "Manager escalation: expert request waiting"),
        ]:
            if elapsed >= threshold and not item.get(key):
                item[key] = True
                for user in read_all(db, "users"):
                    if user["role"] == "admin":
                        notify(db, user["id"], item["customer_id"], title, item["id"])
        put(db, "requests", item)
    for task in read_all(db, "tasks"):
        if (
            task["status"] != "completed"
            and datetime.fromisoformat(task["due_at"]) <= datetime.now(UTC)
            and task.get("reminded_due") != task["due_at"]
        ):
            notify(
                db,
                task["owner"],
                task["customer_id"],
                f"Overdue {task['kind']}: {task['assigned_to']} — "
                + (
                    "consented status update due"
                    if task.get("consent")
                    else "internal follow-up only"
                ),
            )
            task["reminded_due"] = task["due_at"]
            put(db, "tasks", task)


def notify(db, owner, customer_id, title, request_id=None):
    put(
        db,
        "notifications",
        {
            "id": uid(),
            "owner": owner,
            "customer_id": customer_id,
            "title": title,
            "request_id": request_id,
            "read": False,
            "created_at": now(),
        },
    )


@router.get("/bootstrap")
def bootstrap(
    user: User, start: str | None = None, end: str | None = None, associate: str | None = None
):
    with transaction() as db:
        reminder_cycle(db)
        customers = [
            c
            for c in read_all(db, "customers")
            if user["role"] == "admin" or c["owner"] == user["id"]
        ]
        if associate and user["role"] == "admin":
            customers = [c for c in customers if c["owner"] == associate]
        if start or end:
            first, last = domain.date_range(start, end)
            start, end = first.isoformat(), last.isoformat()
            customers = [
                c
                for c in customers
                if any(
                    first
                    <= datetime.fromisoformat(t).astimezone(ZoneInfo("Asia/Kolkata")).date()
                    <= last
                    for t in c["activities"]
                )
            ]
        customers.sort(key=lambda c: c["updated_at"], reverse=True)
        for c in customers:
            c["flow"] = flow.build(db, c)
            c["score"] = domain.score(
                c,
                [t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]],
                domain.quote(db, c),
            )
        permitted = {c["id"] for c in customers}
        index = get(db, "index", "status")
        return {
            "user": user,
            "demo": os.getenv("DEMO_MODE", "true").lower() == "true",
            "customers": customers,
            "products": read_all(db, "products"),
            "offers": read_all(db, "offers"),
            "tasks": [t for t in read_all(db, "tasks") if t["customer_id"] in permitted],
            "requests": [r for r in read_all(db, "requests") if r["customer_id"] in permitted],
            "notifications": [n for n in read_all(db, "notifications") if n["owner"] == user["id"]],
            "questions": [
                {k: v for k, v in q.items() if k not in ("answer", "explanation")}
                for q in read_all(db, "questions")
            ],
            "attempts": [
                a
                for a in read_all(db, "attempts")
                if (
                    a["owner"] == (associate or a["owner"])
                    if user["role"] == "admin"
                    else a["owner"] == user["id"]
                )
                and (
                    not start
                    or datetime.fromisoformat(a["created_at"])
                    .astimezone(ZoneInfo("Asia/Kolkata"))
                    .date()
                    .isoformat()
                    >= start
                )
                and (
                    not end
                    or datetime.fromisoformat(a["created_at"])
                    .astimezone(ZoneInfo("Asia/Kolkata"))
                    .date()
                    .isoformat()
                    <= end
                )
            ],
            "practice": get(db, "practice", user["id"])
            or {"answered": [], "finished": False, "feedback": None},
            "associates": [public_user(u) for u in read_all(db, "users")],
            "knowledge": read_all(db, "knowledge") if user["role"] == "admin" else [],
            "commercial": [
                {"soundbar_description": "", "protection_description": "", **terms}
                for terms in read_all(db, "commercial")
            ],
            "scopes": {
                "customers_tasks_requests": "selected associate and customer activity dates",
                "attempts": "selected associate and attempt dates in IST",
                "notifications": "current user's inbox across dates",
                "practice": "current user's active practice session",
            },
            "index": {k: v for k, v in index.items() if k not in ("chunks", "vectors")},
            "shift": get(
                db, "shifts", user["id"] + datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
            ),
        }


@router.post("/shift")
def shift(body: TextInput, user: User):
    command = body.text.strip().casefold()
    if command not in ["start", "start shift", "tv", "skip_practice", "skip practice today"]:
        raise HTTPException(422, "Unknown shift action")
    with transaction() as db:
        saved = put(
            db,
            "shifts",
            {
                "id": user["id"] + datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
                "owner": user["id"],
                "department": "TV",
                "started_at": now(),
                "practice_skipped": command in ["skip_practice", "skip practice today"],
            },
        )
        if command in ["start", "start shift"]:
            return {
                **saved,
                "lines": ["Which department are you working in today? TV is available."],
                "buttons": [flow.button("TV", "text", "TV")],
            }
        day = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        products = read_all(db, "products")
        offers = [o for o in read_all(db, "offers") if o["starts_on"] <= day <= o["ends_on"]]
        return {
            **saved,
            "lines": [
                f"TV: {sum(p['stock'] > 0 for p in products)} in-stock models; {len(offers)} current offers.",
                "No verified daily change log or video supplied.",
                "Open stock, start practice or start a customer.",
            ],
            "buttons": [
                flow.nav("View stock", "stock"),
                flow.nav("Start practice", "training"),
                flow.nav("New customer", "new_customer"),
            ],
        }


@router.post("/customers", status_code=201)
def create_customer(body: NewCustomer, user: User):
    with transaction() as db:
        return create_customer_record(db, body, user)


def create_customer_record(db, body: NewCustomer, user: User):
    mine = [c for c in read_all(db, "customers") if c["owner"] == user["id"]]
    name = body.name.strip() or "Customer " + datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    duplicate = sum(c.get("base_name", c["name"]).casefold() == name.casefold() for c in mine)
    c = {
        "id": uid(),
        "name": name + (f" {duplicate + 1}" if duplicate else ""),
        "base_name": name,
        "serial": max((c["serial"] for c in mine), default=0) + 1,
        "owner": user["id"],
        "created_at": now(),
        "updated_at": now(),
        "activities": [now()],
        "stage": "assess",
        "home": {},
        "confirmed": False,
        "demo": None,
        "selected": [],
        "preferred": None,
        "payment": None,
        "consent": False,
        "sale": False,
        "language": "English",
        "extras": [],
        "site": {},
        "version": 1,
        "messages": [],
        "notes": [],
    }
    flow.append_prompt(db, c)
    audit(db, user["id"], "create_customer", c["id"])
    put(db, "customers", c)
    return flow.present(db, c)


@router.get("/customers/{id_}")
def customer(id_: str, user: User):
    with transaction() as db:
        c = domain.owned(db, "customers", id_, user)
        return flow.present(db, c)


@router.post("/customers/{id_}/actions")
def action(id_: str, body: Action, user: User):
    from app.web.actions import validate

    if len(json.dumps(body.data)) > 12000:
        raise HTTPException(422, "Action data too large")
    with transaction() as db:
        c = domain.owned(db, "customers", id_, user)
        try:
            values = validate(body.action, body.data)
            domain.require(
                c["version"] == body.version, "This customer changed. Refresh before saving."
            )
            domain.act(db, c, user, body.action, values)
        except HTTPException as exc:
            from app.web.localization import action_error

            raise HTTPException(
                exc.status_code, action_error(body.action, c.get("language"), exc.detail)
            ) from exc
        flow.append_prompt(db, c)
        return flow.present(db, c)


@router.post(
    "/customers/{id_}/messages",
    responses={
        202: {
            "model": MessageReceipt,
            "description": "Message saved; poll status_url for the final result",
        }
    },
)
async def send_message(id_: str, body: TextInput, user: User):
    from app.web.message_jobs import submit

    return await submit(id_, body, user)


@router.get(
    "/customers/{id_}/message-results/{request_id}",
    responses={202: {"model": MessageReceipt, "description": "Message still processing"}},
)
def message_result(id_: str, request_id: str, user: User):
    from app.web.message_jobs import result

    return result(id_, request_id, user)


async def process_message(id_: str, body: TextInput, user: User):
    with transaction() as db:
        c = domain.owned(db, "customers", id_, user)
        old = next(
            (
                m
                for m in c["messages"]
                if m.get("request_id") == body.request_id and m["role"] == "assistant"
            ),
            None,
        )
        previous_input = next(
            (
                m
                for m in c["messages"]
                if m.get("request_id") == body.request_id and m["role"] == "user"
            ),
            None,
        )
        domain.require(
            not previous_input or previous_input["text"] == body.text,
            "Request ID already used with different content",
        )
        if old:
            return flow.reply(db, c, body.request_id, user)
        if body.expected_version is not None:
            domain.require(
                c["version"] == body.expected_version,
                "This customer changed. Refresh before sending.",
            )
        pending = next(
            (
                m
                for m in c["messages"]
                if m.get("request_id") == body.request_id and m["role"] == "user"
            ),
            None,
        )
        if pending and pending.get("busy_until", 0) > time.time():
            raise HTTPException(409, "This message is already being processed")
        answered = {m.get("request_id") for m in c["messages"] if m["role"] == "assistant"}
        domain.require(
            not any(
                m.get("busy_until", 0) > time.time()
                and m["role"] == "user"
                and m.get("request_id") != body.request_id
                and m.get("request_id") not in answered
                for m in c["messages"]
            ),
            "Another message is processing for this visit",
        )
        if pending:
            pending["busy_until"] = time.time() + 120
        else:
            domain.message(
                c,
                "user",
                body.text,
                request_id=body.request_id,
                busy_until=time.time() + 120,
                actor=user["name"],
            )
        c.pop("chat_override", None)
        c.pop("chat_override_text", None)
        if not intelligence.unsafe(body.text) and flow.handle_text(
            db, c, body.text, user, body.request_id
        ):
            for m in c["messages"]:
                if m.get("request_id") == body.request_id:
                    m["busy_until"] = 0
            put(db, "customers", c)
            return flow.reply(db, c, body.request_id, user)
        if c.get("chat_mode") == "expert" and not intelligence.unsafe(body.text):
            linked = get(db, "requests", c.get("active_request_id", ""))
            if (
                linked
                and linked["customer_id"] == c["id"]
                and not any(
                    entry.get("request_id") == body.request_id for entry in linked["thread"]
                )
            ):
                linked["thread"].append(
                    {
                        "by": user["name"],
                        "role": user["role"],
                        "text": body.text,
                        "at": now(),
                        "request_id": body.request_id,
                    }
                )
                if linked["status"] in ["answered", "resolved"]:
                    linked.update(status="waiting", cycle_at=now(), reminded=False, escalated=False)
                put(db, "requests", linked)
                for admin_user in read_all(db, "users"):
                    if admin_user["role"] == "admin":
                        notify(
                            db,
                            admin_user["id"],
                            c["id"],
                            f"Follow-up on expert request #{linked['number']}",
                            linked["id"],
                        )
        for saved_message in c["messages"]:
            if (
                saved_message.get("request_id") == body.request_id
                and saved_message["role"] == "user"
            ):
                saved_message["processing_version"] = c["version"] + 1
        domain.touch(db, c, user, "message")
        baseline = c["version"]
        context = domain.commercial_context(db, c)
    try:
        rate_limit("ai:" + user["id"], 20)
        home = {}
        if (
            not c["confirmed"]
            and c.get("chat_mode", "flow") == "flow"
            and not intelligence.unsafe(body.text)
            and (not flow.is_question(body.text) or flow.multiple_home_facts(body.text))
        ):
            home = await intelligence.extract_home(body.text, c["home"], pending=flow.missing(c))
            c["home"].update(home)
            if not flow.is_question(body.text) or body.text.strip().casefold() in [
                "unknown",
                "not sure",
                "don't know",
                "customer doesn't know",
            ]:
                with transaction() as db:
                    current = domain.owned(db, "customers", id_, user)
                    domain.require(
                        current["version"] == baseline,
                        "The visit changed while the answer was processed. Refresh and retry.",
                    )
                    if (
                        not home
                        and flow.missing(current)
                        and body.text.strip().casefold()
                        in ["unknown", "not sure", "don't know", "customer doesn't know"]
                    ):
                        home[flow.missing(current)] = "Unknown"
                    if not home and flow.missing(current):
                        field = flow.missing(current)
                        hints = {
                            "distance": "Use feet or metres, or say Unknown if it has not been measured.",
                            "placement": "Is it a wall, table or cabinet? Say Unknown if unsure.",
                            "budget": "What rupee range should we use? Say Unknown if undecided.",
                        }
                        domain.message(
                            current,
                            "assistant",
                            "I could not confirm that detail. "
                            + hints.get(field, "Please clarify, or say Unknown."),
                            request_id=body.request_id,
                        )
                    current["home"].update(home)
                    current["chat_mode"] = "flow"
                    current["awaiting_home"] = flow.missing(current)
                    domain.touch(db, current, user, "home_answer_text")
                    flow.append_prompt(db, current)
                    current["messages"][-1]["request_id"] = body.request_id
                    put(db, "customers", current)
                    return flow.present(db, current)
        output = await intelligence.answer(body.text, c, context)
    except HTTPException:
        with transaction() as db:
            current = domain.owned(db, "customers", id_, user)
            for m in current["messages"]:
                if m.get("request_id") == body.request_id and m["role"] == "user":
                    m["busy_until"] = 0
            put(db, "customers", current)
        raise
    with transaction() as db:
        current = domain.owned(db, "customers", id_, user)
        domain.require(
            current["version"] == baseline,
            "The visit changed while the answer was processed. Refresh and retry.",
        )
        if current["version"] == baseline and not current["confirmed"]:
            current["home"].update(home)
        if output["trace"].get("mode") != "blocked":
            current["chat_mode"] = intelligence.coaching_intent(body.text)
            current["expert_question_pending"] = False
        domain.message(
            current,
            "assistant",
            output["text"],
            coaching_type=intelligence.coaching_intent(body.text),
            sources=output["sources"],
            trace=output["trace"],
            request_id=body.request_id,
        )
        domain.touch(db, current, user, "ai_reply")
        return flow.present(db, current)


@router.post("/comparison")
async def comparison(body: Compare, user: User):
    rate_limit("ai:" + user["id"], 20)
    with transaction() as db:
        c = (
            domain.owned(db, "customers", body.customer_id, user)
            if body.customer_id
            else {
                "home": {},
                "messages": [],
                "selected": body.products,
                "confirmed": False,
                "demo": None,
                "language": "English",
            }
        )
        products = [get(db, "products", id_) for id_ in body.products]
        if None in products or len(set(body.products)) != len(products):
            raise HTTPException(422, "Choose two or three different known TVs")
        context = domain.commercial_context(db, c)
    verdict = await intelligence.answer(
        "Compare "
        + ", ".join(p["brand"] + " " + p["model"] for p in products)
        + ". Give an AI verdict for this home, tradeoffs and what to show in a physical demo.",
        c,
        context,
        products,
    )
    return {"products": products, "verdict": verdict}


@router.get("/customers/{id_}/summary")
def summary(id_: str, user: User):
    with transaction() as db:
        return domain.quote(db, domain.owned(db, "customers", id_, user))


@router.get("/customers/{id_}/summary.pdf", response_class=Response)
def summary_pdf(id_: str, user: User):
    from app.web.pdf import render_summary

    with transaction() as db:
        q = domain.quote(db, domain.owned(db, "customers", id_, user))
        audit(db, user["id"], "generate_pdf", id_)
    return Response(
        render_summary(q),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="store-iq-summary-v{q["version"]}.pdf"'
        },
    )


@router.post("/customers/{id_}/share", status_code=201)
def share(id_: str, body: Action, user: User):
    with transaction() as db:
        return share_record(db, id_, body, user)


def share_record(db, id_: str, body: Action, user: User):
    c = domain.owned(db, "customers", id_, user)
    domain.require(c["version"] == body.version, "Summary changed; preview the latest version")
    domain.require(
        c["consent"] and body.data.get("confirmed") is True,
        "Customer consent and explicit preview confirmation are required",
    )
    snapshot = domain.quote(db, c)
    preview = get(db, "share_previews", str(body.data.get("preview_id", "")))
    domain.require(
        preview
        and preview["customer_id"] == id_
        and preview["owner"] == user["id"]
        and not preview.get("used")
        and preview["expires_at"] > now(),
        "Prepare a recipient and PDF preview first",
    )
    domain.require(
        preview["version"] == c["version"] and preview["fingerprint"] == snapshot["fingerprint"],
        "Quote changed; regenerate the preview",
    )
    preview["used"] = True
    put(db, "share_previews", preview)
    snapshot["customer"] = {"serial": c["serial"], "name": c["name"]}
    snapshot["tasks"] = [
        {k: t[k] for k in ("kind", "status", "due_at", "assigned_to")} for t in snapshot["tasks"]
    ]
    if snapshot.get("demo"):
        snapshot["demo"] = {
            "reason": snapshot["demo"]["reason"],
            "preferred": snapshot["demo"]["preferred"],
        }
    if snapshot["product"]:
        snapshot["product"] = {
            k: v for k, v in snapshot["product"].items() if k not in ("stock", "expected_on")
        }
    token = uid() + uid()
    put(
        db,
        "shares",
        {
            "id": hashlib.sha256(token.encode()).hexdigest(),
            "customer_id": id_,
            "owner": c["owner"],
            "snapshot": snapshot,
            "recipient": preview["recipient"],
            "pdf_version": preview["version"],
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "revoked": False,
            "created_at": now(),
        },
    )
    audit(db, user["id"], "share_summary", id_)
    return {"path": "/share/" + token, "expires_in_days": 7, "version": c["version"]}


@router.post("/customers/{id_}/share-preview")
def share_preview(id_: str, body: Action, user: User):

    with transaction() as db:
        return share_preview_record(db, id_, body, user)


def share_preview_record(db, id_: str, body: Action, user: User):
    from app.web.pdf import render_summary

    c = domain.owned(db, "customers", id_, user)
    recipient = str(body.data.get("recipient", "")).strip()
    domain.require(
        c["consent"] and c["version"] == body.version, "Consent and current summary required"
    )
    domain.require(3 <= len(recipient) <= 200, "Enter the intended test recipient")
    q = domain.quote(db, c)
    pdf = render_summary(q)
    preview = {
        "id": uid(),
        "customer_id": id_,
        "owner": user["id"],
        "recipient": recipient,
        "version": c["version"],
        "fingerprint": q["fingerprint"],
        "pdf_hash": hashlib.sha256(pdf).hexdigest(),
        "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
    }
    put(db, "share_previews", preview)
    return {**preview, "summary": q}


@router.delete("/customers/{id_}/share")
def revoke(id_: str, user: User):
    with transaction() as db:
        domain.owned(db, "customers", id_, user)
        for s in read_all(db, "shares"):
            if s["customer_id"] == id_:
                s["revoked"] = True
                put(db, "shares", s)
        audit(db, user["id"], "revoke_links", id_)
    return {"ok": True}


@router.get("/shared/{token}")
def shared(token: str):
    with transaction() as db:
        s = get(db, "shares", hashlib.sha256(token.encode()).hexdigest())
        if not s or s["revoked"] or s["expires_at"] < now():
            raise HTTPException(404, "This summary link has expired or was revoked")
        c = get(db, "customers", s["customer_id"])
        return {
            **s["snapshot"],
            "outdated": c["version"] != s["snapshot"]["version"]
            or s["snapshot"].get("fingerprint") != domain.quote_fingerprint(db, c),
            "expires_at": s["expires_at"],
        }


class ExpertInput(Input):
    customer_id: str
    question: str = Field(min_length=3, max_length=4000)
    blocking: bool = False


@router.post("/requests", status_code=201)
def expert(body: ExpertInput, user: User):
    with transaction() as db:
        return expert_record(db, body, user)


def expert_record(db, body: ExpertInput, user: User):
    c = domain.owned(db, "customers", body.customer_id, user)
    for r in read_all(db, "requests"):
        if (
            r["customer_id"] == c["id"]
            and r["question"].strip().casefold() == body.question.strip().casefold()
        ):
            r["blocking"] = r.get("blocking", False) or body.blocking
            put(db, "requests", r)
            if r["status"] == "resolved":
                r.update(
                    status="waiting",
                    cycle_at=now(),
                    reminded=False,
                    escalated=False,
                    decision_evidence=None,
                )
                r["thread"].append(
                    {"by": user["name"], "role": "event", "text": "reopened", "at": now()}
                )
                put(db, "requests", r)
                for u in read_all(db, "users"):
                    if u["role"] == "admin":
                        notify(db, u["id"], c["id"], f"Reopened request #{r['number']}", r["id"])
            c["active_request_id"] = r["id"]
            c["chat_mode"] = "expert"
            c["expert_waiting"] = True
            domain.touch(db, c, user, "link_expert_request")
            flow.append_prompt(db, c)
            return r
    last = next((m for m in reversed(c["messages"]) if m["role"] == "assistant"), {})
    r = {
        "id": uid(),
        "number": len(read_all(db, "requests")) + 1,
        "owner": c["owner"],
        "customer_id": c["id"],
        "customer_name": c["name"],
        "serial": c["serial"],
        "question": body.question,
        "blocking": body.blocking,
        "context": {"home": c["home"], "selected": c["selected"]},
        "sources": last.get("sources", []),
        "answer": last.get("text", ""),
        "assigned_to": None,
        "status": "waiting",
        "created_at": now(),
        "cycle_at": now(),
        "thread": [],
        "reminded": False,
        "escalated": False,
    }
    put(db, "requests", r)
    c["active_request_id"] = r["id"]
    c["chat_mode"] = "expert"
    c["expert_waiting"] = True
    for u in read_all(db, "users"):
        if u["role"] == "admin":
            notify(db, u["id"], c["id"], f"New expert request #{r['number']}", r["id"])
    domain.message(
        c,
        "event",
        f"Expert request #{r['number']} sent. You can continue other steps.",
        request_id=r["id"],
    )
    domain.touch(db, c, user, "expert_request")
    flow.append_prompt(db, c)
    return r


@router.post("/requests/{id_}/reply")
def reply(id_: str, body: TextInput, user: User):
    admin(user)
    with transaction() as db:
        r = domain.owned(db, "requests", id_, user)
        r["thread"].append({"by": user["name"], "role": "admin", "text": body.text, "at": now()})
        r["status"] = "answered"
        r["assigned_to"] = user["name"]
        put(db, "requests", r)
        c = get(db, "customers", r["customer_id"])
        domain.message(c, "admin", body.text, actor=user["name"], request_id=id_)
        domain.touch(db, c, user, "expert_reply")
        notify(db, r["owner"], c["id"], f"Answered by {user['name']} · request #{r['number']}", id_)
        return r


@router.post("/requests/{id_}/action")
def request_action(id_: str, body: Action, user: User):
    with transaction() as db:
        r = domain.owned(db, "requests", id_, user)
        if body.action == "assign":
            admin(user)
            owners = {u["name"] for u in read_all(db, "users") if u["role"] == "admin"}
            domain.require(body.data.get("owner") in owners, "Choose a saved admin")
            r["assigned_to"] = body.data["owner"]
            if r["status"] in ["waiting", "assigned"]:
                r["status"] = "assigned"
        elif body.action == "resolve":
            r["status"] = "resolved"
            evidence = str(body.data.get("evidence", "")).strip()
            if evidence:
                domain.require(
                    len(evidence) >= 10, "Record the verified answer or alternative and its source"
                )
                r["decision_evidence"] = {"text": evidence, "by": user["name"], "at": now()}
        elif body.action == "reopen":
            r.update(
                status="waiting",
                cycle_at=now(),
                reminded=False,
                escalated=False,
                decision_evidence=None,
            )
        elif body.action == "followup":
            text = str(body.data.get("text", "")).strip()
            domain.require(1 <= len(text) <= 4000, "Enter a follow-up question")
            r["thread"].append(
                {"by": user["name"], "role": user["role"], "text": text, "at": now()}
            )
            if r["status"] in ["answered", "resolved"]:
                r.update(
                    status="waiting",
                    cycle_at=now(),
                    reminded=False,
                    escalated=False,
                    decision_evidence=None,
                )
        else:
            raise HTTPException(422, "Unknown request action")
        r["thread"].append({"by": user["name"], "role": "event", "text": body.action, "at": now()})
        c = get(db, "customers", r["customer_id"])
        domain.message(
            c,
            "event",
            f"Expert request #{r['number']}: {body.action}"
            + (" · " + text if body.action == "followup" else ""),
            actor=user["name"],
            request_id=id_,
        )
        domain.touch(db, c, user, "request_" + body.action)
        for u in read_all(db, "users"):
            if u["role"] == "admin":
                notify(
                    db,
                    u["id"],
                    r["customer_id"],
                    f"Expert request #{r['number']}: {body.action}",
                    r["id"],
                )
        audit(db, user["id"], "request_" + body.action, id_)
        return put(db, "requests", r)


class TaskUpdate(Input):
    status: Literal["pending", "confirmed", "completed", "problem"]
    detail: str = Field(min_length=5, max_length=2000)
    assigned_to: str = Field(min_length=2, max_length=100)
    due_at: datetime


@router.post("/tasks/{id_}")
def task_update(id_: str, body: TaskUpdate, user: User):
    if body.due_at.tzinfo is None:
        raise HTTPException(422, "Task time needs a timezone")
    with transaction() as db:
        return task_update_record(db, id_, body, user)


def task_update_record(db, id_: str, body: TaskUpdate, user: User):
    t = domain.owned(db, "tasks", id_, user)
    c = get(db, "customers", t["customer_id"])
    if t["due_at"] != body.due_at.isoformat() or (
        t["status"] == "completed" and body.status != "completed"
    ):
        t.pop("reminded_due", None)
    if body.status == "completed" and t["kind"] in ["installation", "working_check"]:
        required = "delivery" if t["kind"] == "installation" else "installation"
        domain.require(
            any(
                x["customer_id"] == c["id"] and x["kind"] == required and x["status"] == "completed"
                for x in read_all(db, "tasks")
            ),
            f"Complete {required} first",
        )
    if body.status == "completed" and t["kind"] == "working_check":
        domain.require(
            all(
                x in body.detail.casefold() for x in ["picture", "sound", "devices", "satisfaction"]
            ),
            "Confirm picture, sound, devices and satisfaction in the evidence",
        )
        c["stage"] = "closed"
    elif body.status == "problem" and c["stage"] == "closed":
        c["stage"] = "handover"
    t.update(
        status=body.status,
        detail=body.detail,
        assigned_to=body.assigned_to,
        due_at=body.due_at.isoformat(),
        updated_at=now(),
    )
    put(db, "tasks", t)
    if body.status != "completed" and t["kind"] in [
        "delivery",
        "installation",
        "working_check",
    ]:
        if c["stage"] == "closed":
            c["stage"] = "handover"
        dependent = {
            "delivery": ["installation", "working_check"],
            "installation": ["working_check"],
        }.get(t["kind"], [])
        for other in read_all(db, "tasks"):
            if (
                other["customer_id"] == c["id"]
                and other["kind"] in dependent
                and other["status"] == "completed"
            ):
                other.update(
                    status="pending",
                    detail="Reconfirmation required after upstream task reopened",
                    updated_at=now(),
                )
                put(db, "tasks", other)
    domain.message(c, "event", f"{t['kind']}: {body.status} · {body.detail}", actor=user["name"])
    domain.touch(db, c, user, "task_update")
    return t


class TrainingInput(Input):
    question_id: str
    choice: int = Field(ge=0, le=2)


@router.post("/training")
def training(body: TrainingInput, user: User):
    with transaction() as db:
        q = get(db, "questions", body.question_id)
        if not q:
            raise HTTPException(404, "Question not found")
        result = {
            "id": uid(),
            "owner": user["id"],
            "question_id": q["id"],
            "choice": body.choice,
            "correct": q["answer"] == body.choice,
            "topic": q["topic"],
            "created_at": now(),
        }
        put(db, "attempts", result)
        session = get(db, "practice", user["id"]) or {
            "id": user["id"],
            "answered": [],
            "finished": False,
            "cycle": 1,
        }
        if q["id"] not in session["answered"]:
            session["answered"].append(q["id"])
        session["feedback"] = {**result, "answer": q["answer"], "explanation": q["explanation"]}
        put(db, "practice", session)
        return {**result, "answer": q["answer"], "explanation": q["explanation"]}


@router.post("/training/session")
def training_session(body: Action, user: User):
    with transaction() as db:
        session = get(db, "practice", user["id"]) or {
            "id": user["id"],
            "answered": [],
            "finished": False,
            "cycle": 1,
        }
        if body.action == "finish":
            session.update(finished=True, feedback=None)
        elif body.action == "repeat":
            session.update(answered=[], finished=False, feedback=None, cycle=session["cycle"] + 1)
        elif body.action == "next":
            session["feedback"] = None
        else:
            raise HTTPException(422, "Choose next, finish or repeat")
        return put(db, "practice", session)


@router.post("/notifications/{id_}/read")
def notification_read(id_: str, user: User):
    with transaction() as db:
        n = domain.owned(db, "notifications", id_, user)
        n["read"] = True
        return put(db, "notifications", n)


def save_admin(kind, id_, body, user):
    admin(user)
    data = body.model_dump()
    if id_ != body.id or intelligence.unsafe(json.dumps(data)):
        raise HTTPException(422, "Invalid ID or instruction-like content")
    with transaction() as db:
        existing = get(db, kind, id_)
        if not existing:
            raise HTTPException(404, "Record not found")
        domain.require(
            existing["version"] == body.version, "Record changed; refresh before editing"
        )
        if kind == "products":
            dirty = intelligence.stable_chunks([existing], []) != intelligence.stable_chunks(
                [data], []
            )
            data["mock"] = True
        else:
            dirty = kind == "knowledge"
        data["version"] += 1
        put(db, kind, data)
        if dirty:
            index = get(db, "index", "status")
            index["dirty"] = True
            put(db, "index", index)
        audit(db, user["id"], "edit_" + kind, id_)
        return data


@router.put("/admin/products/{id_}")
def edit_product(id_: str, body: Product, user: User):
    return save_admin("products", id_, body, user)


@router.put("/admin/offers/{id_}")
def edit_offer(id_: str, body: Offer, user: User):
    return save_admin("offers", id_, body, user)


@router.put("/admin/knowledge/{id_}")
def edit_knowledge(id_: str, body: Knowledge, user: User):
    return save_admin("knowledge", id_, body, user)


@router.put("/admin/commercial/{id_}")
def edit_commercial(id_: str, body: Commercial, user: User):
    return save_admin("commercial", id_, body, user)


@router.post("/admin/reindex")
async def rebuild(user: User):
    admin(user)
    rate_limit("index:" + user["id"], 3)
    result = await intelligence.reindex()
    with transaction() as db:
        audit(db, user["id"], "reindex", str(result["version"]))
    return {k: v for k, v in result.items() if k not in ("chunks", "vectors")}


async def reminders():
    while True:
        await asyncio.sleep(30)
        with transaction() as db:
            reminder_cycle(db)
