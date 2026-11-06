"""Saved, channel-neutral text inputs. Business mutations use the existing gates."""

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.web import domain
from app.web.actions import validate
from app.web.localization import BUTTONS
from app.web.store import audit, get, now, put, read_all

IST = ZoneInfo("Asia/Kolkata")


def translated(c, en, hi, mr):
    return {"Hindi": hi, "Marathi": mr}.get(c.get("language"), en)


def canonical(text):
    text = re.sub(r"\s+", " ", text).strip().casefold()
    for en, variants in BUTTONS.items():
        if text in [v.casefold() for v in variants]:
            return en.casefold()
    return text


def say(db, c, user, request_id, lines, *, buttons=None, touch=True, **metadata):
    if isinstance(lines, str):
        lines = lines.splitlines()
    # Details are retained over separate messages, never silently truncated.
    for offset in range(0, len(lines), 3):
        domain.message(
            c,
            "assistant",
            "\n".join(lines[offset : offset + 3]),
            request_id=request_id,
            buttons=(buttons or []) if offset + 3 >= len(lines) else [],
            **metadata,
        )
    c["text_prompt"] = {"lines": lines[-3:], "buttons": buttons or []}
    if touch:
        domain.touch(db, c, user, "text_workflow")
    else:
        put(db, "customers", c)
        audit(db, user["id"], "text_workflow", c["id"])
    return True


def act(db, c, user, name, values=None):
    return domain.act(db, c, user, name, validate(name, values or {}))


def finish(db, c, user, rid, name, values=None):
    from app.web import flow

    c.pop("text_input", None)
    c.pop("text_prompt", None)
    act(db, c, user, name, values)
    flow.append_prompt(db, c)
    c["messages"][-1]["request_id"] = rid
    put(db, "customers", c)
    return True


def date_value(text):
    """Explicit store-local or offset timestamps; ambiguous dates are clarified."""
    text = text.strip().replace(" IST", "+05:30").replace(" ist", "+05:30")
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        value = datetime.strptime(text, "%d/%m/%Y %H:%M")
    return value.replace(tzinfo=IST) if value.tzinfo is None else value


def answer_yes(text):
    return {
        "yes": True,
        "consent given": True,
        "हाँ": True,
        "हां": True,
        "हो": True,
        "no": False,
        "no consent": False,
        "नहीं": False,
        "नाही": False,
    }.get(canonical(text))


SITE = {
    "placement": ("Wall or table/cabinet placement?", "दीवार या मेज पर?", "भिंत की टेबलवर?"),
    "power": (
        "Is the power socket suitable and accessible?",
        "बिजली का सॉकेट उपलब्ध है?",
        "वीजेचा सॉकेट उपलब्ध आहे का?",
    ),
    "cable_route": ("Is the cable route clear?", "केबल का रास्ता साफ है?", "केबलचा मार्ग मोकळा आहे का?"),
    "access": (
        "Any wall, space, lift or access restrictions?",
        "जगह, दीवार या पहुंच की कोई सीमा?",
        "जागा, भिंत किंवा प्रवेशाची मर्यादा आहे का?",
    ),
    "devices": (
        "Which connected devices need checking?",
        "कौन से उपकरण जोड़ने हैं?",
        "कोणती उपकरणे जोडायची आहेत?",
    ),
    "specialist": (
        "Is specialist work required? Yes, no or unknown.",
        "विशेष काम चाहिए? yes, no या unknown।",
        "तज्ज्ञाचे काम हवे? yes, no किंवा unknown.",
    ),
}


def prompt_site(db, c, user, rid):
    pending = c["text_input"]
    field = next((f for f in SITE if not pending["values"].get(f)), None)
    if field:
        pending["field"] = field
        return say(db, c, user, rid, translated(c, *SITE[field]))
    values = pending["values"]
    values["notes"] = "; ".join(f"{k}: {v}" for k, v in values.items())[:1000]
    return finish(db, c, user, rid, "site", values)


def cost_lines(db, c):
    from app.web.flow import money

    q = domain.quote(db, c)
    lines = [
        f"{line['label']}{' (optional)' if line.get('optional') else ''}: {money(line['amount'])}."
        for line in q["lines"]
    ]
    lines.append(f"Required: {money(q['required_total'])}; optional: {money(q['optional_total'])}.")
    lines.append(
        "Final total pending: " + "; ".join(q["missing"])
        if q["missing"]
        else f"Final payable: {money(q['total'])}."
    )
    if q["finance"]:
        f = q["finance"]
        lines.append(
            f"Upfront {money(f['upfront'])} + {f['months']} EMIs of {money(f['emi'])} + fees {money(f['fees'])} = {money(f['total'])}; APR {f['apr']}%, subject to approval."
        )
    return lines


def customer_list(db, c, user, rid, command):
    state = c.setdefault("text_list", {"page": 0})
    if command == "customer list" or command == "my customers" or command == "change dates":
        state.update(page=0, choosing_dates=True)
        return say(
            db, c, user, rid, "Which customers? Today, Yesterday, Date range or All customers."
        )
    if command == "date range":
        state.update(choosing_dates=True)
        return say(db, c, user, rid, "Enter start and end dates: YYYY-MM-DD to YYYY-MM-DD.")
    if command in ["today", "yesterday", "customers today", "customers yesterday"]:
        date = datetime.now(IST).date() - timedelta(days=int("yesterday" in command))
        state.update(start=date.isoformat(), end=date.isoformat(), page=0, choosing_dates=False)
    elif command == "all customers":
        state.update(start=None, end=None, page=0, choosing_dates=False)
    elif command in ["next", "previous"]:
        state["page"] = max(0, state["page"] + (1 if command == "next" else -1))
    elif "from" in command or " to " in command:
        dates = re.findall(
            r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}\s+[a-z]+\s+\d{4}", command
        )
        try:
            parsed = []
            for value in dates:
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"]:
                    try:
                        parsed.append(datetime.strptime(value, fmt).date().isoformat())
                        break
                    except ValueError:
                        continue
            if len(parsed) != 2:
                raise ValueError()
            domain.date_range(*parsed)
            state.update(start=parsed[0], end=parsed[1], page=0, choosing_dates=False)
        except (ValueError, HTTPException):
            return say(
                db,
                c,
                user,
                rid,
                "Choose a valid date range with the start before the end. Use YYYY-MM-DD to YYYY-MM-DD.",
            )
    allowed = [
        v for v in read_all(db, "customers") if user["role"] == "admin" or v["owner"] == user["id"]
    ]
    if state.get("start"):
        first, last = domain.date_range(state["start"], state["end"])
        allowed = [
            v
            for v in allowed
            if any(
                first <= datetime.fromisoformat(t).astimezone(IST).date() <= last
                for t in v["activities"]
            )
        ]
    allowed.sort(key=lambda v: v["updated_at"], reverse=True)
    if command.isdigit():
        matches = [v for v in allowed if v["serial"] == int(command)]
        if len(matches) != 1:
            return say(
                db,
                c,
                user,
                rid,
                "Choose a serial from this list. Admins can use the website associate filter to disambiguate serials.",
            )
        target = matches[0]
        c.pop("text_list", None)
        return say(
            db,
            c,
            user,
            rid,
            f"Resuming {target['serial']}. {target['name']}. Saved step: {target['stage']}.",
            resume_customer_id=target["id"],
        )
    state["page"] = min(state["page"], max(0, (len(allowed) - 1) // 3))
    lines = [f"Dates: {state.get('start') or 'All'} to {state.get('end') or 'All'}."]
    page = allowed[state["page"] * 3 : state["page"] * 3 + 3]
    lines += [
        f"{v['serial']}. {v['name']} - {v['stage']}"
        + (f" ({get(db, 'users', v['owner'])['name']})" if user["role"] == "admin" else "")
        for v in page
    ]
    lines += (
        ["Type the customer serial number to continue. Next / Previous / Change dates."]
        if page
        else ["No matching customers. Today / Yesterday / Date range / All customers."]
    )
    return say(db, c, user, rid, lines)


def handle(db, c, text, user, rid):
    """Return True only for recognized deterministic workflow input."""
    from app.web import api, flow

    command = canonical(text)
    if re.search(
        r"what.*(?:next question|should i ask)|which question|कोणता प्रश्न|कौन सा प्रश्न|अगला सवाल",
        command,
    ):
        if re.search(r"cricket|क्रिकेट", command) and not c["home"].get("use") and not c["confirmed"]:
            c["home"]["use"] = "Cricket"
        return finish(db, c, user, rid, "ask_home")
    if command.startswith("customer understood "):
        kind = next(
            (
                m.get("coaching_type")
                for m in reversed(c["messages"])
                if m.get("coaching_type") in ["validate", "translate"] and m.get("sources")
            ),
            None,
        )
        domain.require(kind is not None, "Explain a supported belief or feature first")
        detail = text[len("customer understood ") :].strip()
        domain.require(len(detail) >= 10, "Record the customer's response, at least ten characters")
        c.setdefault("coaching_evidence", {})[kind] = {
            "text": detail,
            "by": user["name"],
            "at": now(),
        }
        return say(db, c, user, rid, "Customer response saved as coaching evidence.")
    if command in ["cancel", "取消", "रद्द", "रद्द करा"]:
        c.pop("text_input", None)
        c.pop("text_list", None)
        c.pop("text_prompt", None)
        c.pop("awaiting_demo_preference", None)
        return finish(db, c, user, rid, "continue_flow")
    if (
        command
        in [
            "customer list",
            "my customers",
            "customers today",
            "customers yesterday",
            "all customers",
            "change dates",
        ]
        or re.match(r"customers\s+(from|between)\b", command)
        or (
            c.get("text_list")
            and (
                command.isdigit()
                or command in ["next", "previous", "today", "yesterday", "date range"]
                or " to " in command
            )
        )
    ):
        return customer_list(db, c, user, rid, command)
    if command == "new customer" or command.startswith("new customer "):
        name = "" if command == "new customer" else text[len("new customer") :].strip()
        target = api.create_customer_record(db, api.NewCustomer(name=name), user)
        return say(
            db,
            c,
            user,
            rid,
            f"New customer {target['serial']}. {target['name']}.",
            resume_customer_id=target["id"],
        )
    if command in ["start shift", "tv", "skip practice today"]:
        day = datetime.now(IST).date().isoformat()
        if command == "start shift":
            return say(db, c, user, rid, "Which department? TV is available. Type TV.")
        put(
            db,
            "shifts",
            {
                "id": user["id"] + day,
                "owner": user["id"],
                "department": "TV",
                "started_at": now(),
                "practice_skipped": command == "skip practice today",
            },
        )
        stock = [p for p in read_all(db, "products") if p["stock"] > 0]
        offers = [o for o in read_all(db, "offers") if o["starts_on"] <= day <= o["ends_on"]]
        return say(
            db,
            c,
            user,
            rid,
            [
                f"TV today: {len(stock)} in-stock models. {len(offers)} current offers; eligibility needs assessment and demo.",
                "No verified daily change log or training video supplied.",
                "Practice is on the Training page. Type New customer, Customer list or View stock.",
            ],
        )
    # Interruption commands retain partial inputs, but leave their prompt until resumed.
    if command in [
        "ask an expert",
        "ask follow-up",
        "resolved",
        "hindi",
        "marathi",
        "english",
        "no consent",
        "consent given",
        "end visit",
        "customer left",
    ]:
        c.pop("text_prompt", None)
        if command == "no consent" and c.get("text_input", {}).get("kind") in [
            "share",
            "recipient",
        ]:
            c.pop("text_input", None)
        return False
    if command in ["edit", "edit details"]:
        domain.require(not c["sale"], "Purchased items are frozen; start a new visit")
        c["text_input"] = {"kind": "home_edit", "field": None}
        return say(
            db,
            c,
            user,
            rid,
            "Which home detail? distance, light, use, seating, problem, placement or budget.",
        )
    if c.get("awaiting_demo_preference") and not flow.is_question(text):
        matches = [
            p
            for p in read_all(db, "products")
            if p["id"] in c["selected"] and (p["model"].casefold() in command or p["id"] in command)
        ]
        if command in ["a", "b", "c"] and ord(command) - ord("a") < len(c["selected"]):
            matches = [get(db, "products", c["selected"][ord(command) - ord("a")])]
        if len(matches) == 1:
            parts = re.split(r"\bbecause\b|क्योंकि|कारण", text, maxsplit=1, flags=re.I)
            if len(parts) == 2 and len(parts[1].strip()) >= 5:
                c.pop("awaiting_demo_preference", None)
                return finish(
                    db,
                    c,
                    user,
                    rid,
                    "demo",
                    {"preferred": matches[0]["id"], "reason": parts[1].strip()},
                )
            c["text_input"] = {"kind": "demo_reason", "preferred": matches[0]["id"]}
            c.pop("awaiting_demo_preference", None)
            return say(
                db, c, user, rid, "Why did the customer prefer this TV after the physical demo?"
            )
    if command == "continue flow" and c.get("text_input"):
        if c["text_input"]["kind"] == "site":
            return prompt_site(db, c, user, rid)
        return say(
            db,
            c,
            user,
            rid,
            c["text_input"].get("prompt", "Continue the pending input or type Cancel."),
        )
    if command in ["see score", "score"]:
        scores = domain.score(
            c,
            [t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]],
            domain.quote(db, c),
        )
        return say(
            db, c, user, rid, [f"{s['step']}: {s['points']}/2 - {s['status']}" for s in scores]
        )
    if command in ["summary", "open summary", "full cost", "cost breakdown", "show charges"]:
        return say(
            db,
            c,
            user,
            rid,
            cost_lines(db, c) + [f"Summary/PDF: /api/customers/{c['id']}/summary.pdf"],
        )
    if command in ["generate pdf", "download pdf"]:
        return say(
            db,
            c,
            user,
            rid,
            f"Download the current version {c['version']} PDF: /api/customers/{c['id']}/summary.pdf",
        )
    if command in ["compare", "show comparison", "view stock", "stock details"]:
        products = (
            [get(db, "products", x) for x in c["selected"]]
            if c["selected"]
            else read_all(db, "products")
        )
        return say(
            db,
            c,
            user,
            rid,
            [
                f"{p['brand']} {p['model']}: {p['size']} inch, {p['refresh_rate']} Hz, INR {p['price']:,}; stock {p['stock']}."
                for p in products
                if p
            ]
            + ["Use matched settings for a physical demo; reading this does not complete it."],
        )
    if command.startswith("visit note ") or command.startswith("note "):
        note = text.split(" ", 2)[-1] if command.startswith("visit note ") else text[5:]
        return finish(db, c, user, rid, "note", {"text": note})
    if command == "ask admin":
        question = next(
            (
                m["text"]
                for m in reversed(c["messages"])
                if m["role"] == "user"
                and canonical(m["text"])
                not in ["ask admin", "ask an expert", "resolved", "ask follow-up"]
            ),
            "",
        )
        domain.require(bool(question), "Ask the expert question before escalating")
        # Material uncertainty is conservative: never let a chat escalation unlock closing.
        blocking = bool(
            re.search(
                r"compatib|install|charge|cost|price|finance|mount|specialist", question, re.I
            )
        )
        put(db, "customers", c)
        r = api.expert_record(
            db, api.ExpertInput(customer_id=c["id"], question=question, blocking=blocking), user
        )
        c.update(domain.owned(db, "customers", c["id"], user))
        return say(
            db,
            c,
            user,
            rid,
            [
                f"Request #{r['number']} sent. You can continue with other questions.",
                "Waiting for assignment."
                if not r["assigned_to"]
                else f"Assigned to {r['assigned_to']}.",
            ],
        )
    if command in ["share summary", "confirm share"] or c.get("text_input", {}).get("kind") in [
        "recipient",
        "share",
    ]:
        pending = c.get("text_input", {})
        domain.require(c["consent"], "Customer consent is required before sharing")
        if command == "share summary":
            c["text_input"] = {"kind": "recipient"}
            return say(
                db,
                c,
                user,
                rid,
                "Who is the intended test recipient? Type a test name. No external delivery occurs.",
            )
        if pending.get("kind") == "recipient":
            recipient = text.strip()
            domain.require(
                3 <= len(recipient) <= 200, "Enter a test recipient name, 3-200 characters"
            )
            say(
                db,
                c,
                user,
                rid,
                [f"Preview for {recipient}: {domain.quote(db, c)['kind']}."]
                + cost_lines(db, c)
                + ["Review the PDF, then type Confirm share or Cancel."],
                recipient=recipient,
            )
            preview = api.share_preview_record(
                db,
                c["id"],
                api.Action(action="preview", version=c["version"], data={"recipient": recipient}),
                user,
            )
            c["text_input"] = {
                "kind": "share",
                "preview_id": preview["id"],
                "version": c["version"],
            }
            put(db, "customers", c)
            return True
        domain.require(
            command == "confirm share" and pending.get("kind") == "share",
            "Prepare a recipient preview before Confirm share",
        )
        shared = api.share_record(
            db,
            c["id"],
            api.Action(
                action="share",
                version=pending["version"],
                data={"preview_id": pending["preview_id"], "confirmed": True},
            ),
            user,
        )
        c.pop("text_input", None)
        return say(
            db,
            c,
            user,
            rid,
            ["Test share recorded; no external message sent.", shared["path"]],
            touch=False,
            share=shared,
        )
    if command == "revoke share":
        for s in read_all(db, "shares"):
            if s["customer_id"] == c["id"]:
                s["revoked"] = True
                put(db, "shares", s)
        return say(db, c, user, rid, "Previous summary links revoked.")
    if command == "site check":
        domain.require(
            c["demo"] and not c["sale"], "Complete the demo before checking the installation site"
        )
        c["text_input"] = {"kind": "site", "values": {}}
        return prompt_site(db, c, user, rid)
    if command in ["confirm sale", "sale confirmation"]:
        q = domain.quote(db, c)
        domain.require(
            c["payment"] and q["total"] is not None and not c["sale"],
            "Complete demo, site and payment preference before confirming a sale",
        )
        amount = q["finance"]["total"] if q["finance"] else q["total"]
        c["text_input"] = {"kind": "sale", "amount": amount, "fingerprint": q["fingerprint"]}
        return say(
            db,
            c,
            user,
            rid,
            f"Confirm the test sale for INR {amount:,}? Type Confirm {amount} or Cancel. No payment is taken.",
        )
    if command in ["optional extras", "done"] or re.match(
        r"(?:add|remove)\s+(?:soundbar|protection)\b", command
    ):
        domain.require(not c["sale"], "Purchased items are frozen")
        if command == "optional extras":
            terms = get(db, "commercial", "terms")
            return say(
                db,
                c,
                user,
                rid,
                [
                    f"Soundbar INR {terms['soundbar']:,}; protection INR {terms['protection']:,}. Optional, never required.",
                    "Type Add soundbar, Remove soundbar, Add protection or Remove protection.",
                    "Coverage not confirmed unless approved terms are supplied. Type Done to review cost.",
                ],
            )
        if command != "done":
            operation, item = command.split()[:2]
            selected = set(c["extras"])
            selected.add(item) if operation == "add" else selected.discard(item)
            act(db, c, user, "extras", {"extras": sorted(selected)})
        return say(db, c, user, rid, cost_lines(db, c))
    if command in ["save for later", "save follow-up", "they will decide later"]:
        c["text_input"] = {"kind": "followup", "field": "reason", "values": {}}
        return say(
            db,
            c,
            user,
            rid,
            translated(
                c,
                "What is pending or the follow-up reason?",
                "फॉलो-अप का कारण?",
                "पाठपुराव्याचे कारण?",
            ),
        )
    if command in ["completed", "problem"] or re.match(
        r"(?:delivery|installation|working check)\s+(?:completed|problem)\b", command
    ):
        tasks = [t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]]
        explicit = next(
            (
                k
                for k in ["delivery", "installation", "working_check"]
                if command.startswith(k.replace("_", " "))
            ),
            None,
        )
        task = (
            next((t for k in [explicit] if k for t in tasks if t["kind"] == k), None)
            if explicit
            else next(
                (
                    t
                    for k in ["delivery", "installation", "working_check"]
                    for t in tasks
                    if t["kind"] == k and t["status"] != "completed"
                ),
                None,
            )
        )
        domain.require(
            task is not None, "Choose a saved delivery, installation or working check task"
        )
        c["text_input"] = {
            "kind": "task",
            "field": "detail",
            "values": {
                "task_id": task["id"],
                "status": "problem" if "problem" in command else "completed",
            },
        }
        return say(
            db,
            c,
            user,
            rid,
            "What happened? For working check, confirm picture, sound, devices and satisfaction individually.",
        )
    if command == "demo unavailable":
        c["text_input"] = {"kind": "demo_unavailable"}
        return say(db, c, user, rid, "Why is the physical demo unavailable? Offers remain locked.")
    if command == "need another demo":
        c["text_input"] = {"kind": "demo_focus"}
        return say(db, c, user, rid, "Which difference should the next physical demo check?")
    pending = c.get("text_input")
    if not pending:
        return False
    # Genuine questions may interrupt collection without becoming site/task evidence.
    if flow.is_question(text):
        return False
    kind = pending["kind"]
    if kind == "home_edit":
        if not pending["field"]:
            if command not in domain.HOME_FIELDS:
                return say(
                    db,
                    c,
                    user,
                    rid,
                    "Choose distance, light, use, seating, problem, placement or budget.",
                )
            pending["field"] = command
            return say(db, c, user, rid, domain.HOME_FIELDS[command])
        return finish(db, c, user, rid, "home", {"home": {pending["field"]: text}})
    if kind == "demo_reason":
        return finish(db, c, user, rid, "demo", {"preferred": pending["preferred"], "reason": text})
    if kind == "site":
        clauses = re.split(r"[,;\n]", text)
        if len(clauses) > 1:
            patterns = {
                "power": r"\b(socket|power)\b",
                "cable_route": r"\bcable(?: route)?\b",
                "access": r"\b(access|lift|space)\b",
                "devices": r"\b(devices?|set top box|hdmi source)\b",
            }
            for clause in clauses:
                clause = clause.strip()
                if re.fullmatch(r"wall|wall mount(?:ing)?", clause, re.I):
                    pending["values"]["placement"] = "Wall"
                elif re.fullmatch(r"table|cabinet|stand", clause, re.I):
                    pending["values"]["placement"] = "Table"
                elif re.search(r"specialist", clause, re.I):
                    pending["values"]["specialist"] = (
                        "unknown"
                        if re.search(r"unknown|unsure|not confirmed", clause, re.I)
                        else "no"
                        if re.search(r"\bno\b|not required", clause, re.I)
                        else "yes"
                        if re.search(r"\byes\b|required|needed", clause, re.I)
                        else "unknown"
                    )
                else:
                    for field, pattern in patterns.items():
                        if re.search(pattern, clause, re.I):
                            pending["values"][field] = clause[:500]
            return prompt_site(db, c, user, rid)
        field = pending["field"]
        value = text.strip()
        if field == "placement":
            value = (
                "Wall"
                if re.search(r"wall|दीवार|भिंत", command)
                else "Table"
                if re.search(r"table|cabinet|stand|मेज|टेबल", command)
                else ""
            )
            if not value:
                return say(db, c, user, rid, translated(c, *SITE[field]))
        elif field == "specialist":
            value = {True: "yes", False: "no"}.get(answer_yes(text), "unknown")
        elif canonical(text) in ["unknown", "not sure", "पता नहीं", "माहीत नाही"]:
            value = "Unknown"
        if not value or len(value) > 500:
            return say(db, c, user, rid, "Answer this check in 1-500 characters or type Unknown.")
        pending["values"][field] = value
        return prompt_site(db, c, user, rid)
    if kind == "sale":
        match = re.fullmatch(r"confirm\s+(\d[\d,]*)", command)
        domain.require(
            match is not None, "Type Confirm followed by the displayed amount, or Cancel"
        )
        domain.require(
            domain.quote(db, c)["fingerprint"] == pending["fingerprint"],
            "Quote changed; type Confirm sale to review it again",
        )
        domain.require(
            int(match[1].replace(",", "")) == pending["amount"],
            "Confirm the exact displayed payable amount",
        )
        return finish(db, c, user, rid, "sale", {"confirmed_total": pending["amount"]})
    if kind in ["demo_focus", "demo_unavailable"]:
        return finish(
            db,
            c,
            user,
            rid,
            "start_demo" if kind == "demo_focus" else "demo_unavailable",
            {"focus" if kind == "demo_focus" else "reason": text},
        )
    if kind in ["followup", "task"]:
        field = pending["field"]
        values = pending["values"]
        if field == "consent":
            value = answer_yes(text)
            if value is None:
                return say(db, c, user, rid, "Record contact permission explicitly: Yes or No.")
        elif field == "due_at":
            try:
                date = date_value(text)
                if date <= datetime.now(UTC):
                    raise ValueError()
                value = date.isoformat()
            except ValueError:
                return say(
                    db,
                    c,
                    user,
                    rid,
                    "Enter a future date and time: YYYY-MM-DD HH:MM IST, or an ISO timestamp with timezone.",
                )
        else:
            value = text.strip()
            if len(value) < (5 if field == "detail" else 3):
                return say(db, c, user, rid, "Please provide a specific answer.")
        values[field] = value
        fields = (
            ["reason", "consent", "due_at", "owner"]
            if kind == "followup"
            else ["detail", "owner", "due_at"]
        )
        next_field = next((f for f in fields if f not in values), None)
        if next_field:
            pending["field"] = next_field
            prompts = {
                "consent": "May we contact the customer? Yes or No; No keeps this task internal.",
                "owner": "Who owns the next update?",
                "due_at": "Agree a future next-update time: YYYY-MM-DD HH:MM IST.",
            }
            pending["prompt"] = prompts[next_field]
            return say(db, c, user, rid, prompts[next_field])
        if kind == "followup":
            return finish(db, c, user, rid, "followup", values)
        put(db, "customers", c)
        task = api.task_update_record(
            db,
            values["task_id"],
            api.TaskUpdate(
                status=values["status"],
                detail=values["detail"],
                assigned_to=values["owner"],
                due_at=values["due_at"],
            ),
            user,
        )
        c.update(domain.owned(db, "customers", c["id"], user))
        c.pop("text_input", None)
        return say(
            db,
            c,
            user,
            rid,
            f"{task['kind']}: {task['status']}. Owner: {task['assigned_to']}; next update {task['due_at']}.",
        )
    return False
