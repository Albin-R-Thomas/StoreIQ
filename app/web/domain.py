"""Deterministic journey rules. Model output cannot change these records."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.web.intelligence import HOME_FIELDS
from app.web.store import audit, get, now, put, read_all, uid


def require(condition, message):
    if not condition:
        raise HTTPException(409, message)


def date_range(start, end):
    try:
        first = datetime.strptime(start or end, "%Y-%m-%d").date()
        last = datetime.strptime(end or start, "%Y-%m-%d").date()
        if last < first:
            raise ValueError()
        return first, last
    except ValueError as exc:
        raise HTTPException(422, "Choose a valid inclusive date range") from exc


def owned(db, kind, id_, user):
    item = get(db, kind, id_)
    if not item:
        raise HTTPException(404, "Record not found")
    if item.get("owner") != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "This record belongs to another associate")
    return item


def message(customer, role, text, **details):
    customer["messages"].append(
        {"id": uid(), "role": role, "text": text, "created_at": now(), "sources": [], **details}
    )


def touch(db, customer, user, action):
    customer["version"] += 1
    customer["updated_at"] = now()
    customer["activities"].append(now())
    put(db, "customers", customer)
    audit(db, user["id"], action, customer["id"])


def eligible_offers(db, customer, product):
    if not (customer["confirmed"] and customer["demo"]) or customer.get("payment") == "finance":
        return []
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    return [
        o
        for o in read_all(db, "offers")
        if o["starts_on"] <= today <= o["ends_on"]
        and product["brand"] in o["brands"]
        and product["size"] >= o["min_size"]
    ]


def commercial_context(db, c):
    unlocked = c["confirmed"] and bool(c["demo"])
    terms = get(db, "commercial", "terms")
    return {
        "products": read_all(db, "products"),
        "offers": read_all(db, "offers") if unlocked else [],
        "offers_unlocked": unlocked,
        "charges": {
            "delivery": terms["delivery"],
            "installation": terms["installation"],
            "wall_mount": terms["wall_mount"],
            "specialist_work": terms["specialist_work"],
        },
        "finance": {
            "months": terms["finance_months"],
            "apr": terms["finance_apr"],
            "processing_fee": terms["finance_fee"],
            "eligibility": "Synthetic plan, subject to approval. Offers cannot combine with finance.",
        },
    }


def quote(db, c):
    if c.get("sale_quote"):
        saved = dict(c["sale_quote"])
        saved.update(
            kind="Test purchase handover",
            version=c["version"],
            consent=c["consent"],
            generated_at=now(),
            tasks=[t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]],
        )
        return saved
    p = get(db, "products", c.get("preferred") or "")
    terms = get(db, "commercial", "terms")
    lines = []
    missing = []
    offer = None
    if p:
        lines = [
            {"label": p["brand"] + " " + p["model"], "amount": p["price"]},
            {"label": "Standard delivery", "amount": terms["delivery"]},
            {"label": "Standard installation", "amount": terms["installation"]},
        ]
        if c["site"].get("placement") == "Wall":
            lines.append({"label": "Standard wall mount", "amount": terms["wall_mount"]})
        if not c["site"].get("confirmed") or not all(
            c["site"].get(k) for k in ("power", "cable_route", "access", "devices")
        ):
            missing.append("Site check: placement, power, cable route, access and specialist work")
        if c["site"].get("specialist") == "yes":
            if terms["specialist_work"] is None:
                missing.append("Specialist work charge: Not confirmed")
            else:
                lines.append(
                    {"label": "Approved specialist work", "amount": terms["specialist_work"]}
                )
        extras = {
            "soundbar": ("2.1 soundbar", terms["soundbar"]),
            "protection": ("2-year protection plan", terms["protection"]),
        }
        lines += [
            {
                "label": extras[e][0],
                "amount": extras[e][1],
                "optional": True,
                "description": terms.get(e + "_description")
                or "Coverage and terms not confirmed; ask admin before recommending.",
            }
            for e in c["extras"]
            if e in extras
        ]
        offers = eligible_offers(db, c, p)
        if offers:
            offer = max(offers, key=lambda o: o["discount"])
            lines.append({"label": offer["title"], "amount": -min(offer["discount"], p["price"])})
    else:
        missing.append("Preferred TV")
    subtotal = sum(line["amount"] for line in lines)
    finance = None
    if c.get("payment") == "finance" and p:
        # Integer rupees: rounded-up EMI; residual collected upfront, never hidden.
        months = terms["finance_months"]
        emi = subtotal // months
        upfront = subtotal - emi * months
        finance = {
            "upfront": upfront,
            "months": months,
            "emi": emi,
            "fees": terms["finance_fee"],
            "total": subtotal + terms["finance_fee"],
            "apr": terms["finance_apr"],
            "status": "Subject to approval; demo terms",
        }
    tasks = [t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]]
    owner = get(db, "users", c["owner"])
    return {
        "customer": {"id": c["id"], "serial": c["serial"], "name": c["name"]},
        "associate": owner["name"],
        "home": c["home"],
        "site": c["site"],
        "contact_owner": owner["name"],
        "fingerprint": quote_fingerprint(db, c),
        "product": p,
        "lines": lines,
        "subtotal": subtotal,
        "optional_total": sum(line["amount"] for line in lines if line.get("optional")),
        "required_total": sum(line["amount"] for line in lines if not line.get("optional")),
        "total": None if missing else subtotal,
        "missing": missing,
        "offer": offer,
        "finance": finance,
        "payment": c["payment"],
        "kind": "Test purchase handover" if c["sale"] else "Quote · not a purchase",
        "consent": c["consent"],
        "version": c["version"],
        "tasks": tasks,
        "demo": c["demo"],
        "compared": [
            {
                "brand": p["brand"],
                "model": p["model"],
                "size": p["size"],
                "panel": p["panel"],
                "price": p["price"],
                "refresh_rate": p["refresh_rate"],
            }
            for id_ in c["selected"]
            if (p := get(db, "products", id_))
        ],
        "mock": True,
        "generated_at": now(),
    }


def quote_fingerprint(db, c):
    if c.get("sale_quote"):
        return c["sale_quote"].get("fingerprint", "frozen")
    dependencies = {
        "products": [get(db, "products", p) for p in c["selected"]],
        "terms": get(db, "commercial", "terms"),
        "offers": read_all(db, "offers"),
        "date": datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
    }
    return hashlib.sha256(json.dumps(dependencies, sort_keys=True).encode()).hexdigest()


def recommendations(db, c):
    products = [p for p in read_all(db, "products") if p["stock"] > 0]
    budget = c["home"].get("budget", "").casefold().replace(",", "")
    budget = budget.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    for original, unit in [("हज़ार", "thousand"), ("हजार", "thousand"), ("लाख", "lakh")]:
        budget = budget.replace(original, unit)
    amounts = re.findall(r"(\d+(?:\.\d+)?)\s*(lakh|lac|thousand|k|l)?", budget)
    multipliers = {"lakh": 100000, "lac": 100000, "l": 100000, "k": 1000, "thousand": 1000}
    cap = max((float(value) * multipliers.get(unit, 1) for value, unit in amounts), default=10**9)
    within = [p for p in products if p["price"] <= cap]
    products = within  # never quietly stretch the stated budget
    preferences = c.get("preferences", {})
    products = [
        p
        for p in products
        if (
            not preferences.get("exclude_brand")
            or p["brand"].casefold() != preferences["exclude_brand"].casefold()
        )
        and (not preferences.get("max_size") or p["size"] <= preferences["max_size"])
    ]
    use = c["home"].get("use", "").lower()
    light = c["home"].get("light", "").lower()
    distance = c["home"].get("distance", "").casefold()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:feet|ft|metres?|meters?)\b", distance)
    feet = float(match[1]) if match else None
    if feet and any(unit in distance for unit in ["metre", "meter", " m"]):
        feet *= 3.28084
    desired_size = 43 if feet and feet < 6 else 55 if feet and feet <= 9 else 65 if feet else None

    def score(p):
        return (
            (
                3 * (p["refresh_rate"] >= 120)
                if any(x in use for x in ["cricket", "sport", "gaming"])
                else 0
            )
            + (p["brightness"] / 500 if "bright" in light else 2 * (p["panel"] == "OLED"))
            + (
                2 * (p["viewing_angle"] == "wide")
                if "side" in c["home"].get("seating", "").lower()
                else 0
            )
            + (2 if desired_size and p["size"] == desired_size else 0)
        )

    return sorted(products, key=lambda p: (-score(p), p["price"]))[:3]


def new_task(db, c, kind, owner, due, detail="", consent=False):
    item = {
        "id": uid(),
        "customer_id": c["id"],
        "customer_name": c["name"],
        "owner": c["owner"],
        "assigned_to": owner,
        "kind": kind,
        "due_at": due,
        "status": "pending",
        "detail": detail,
        "consent": consent,
        "created_at": now(),
        "updated_at": now(),
    }
    put(db, "tasks", item)
    return item


def recommendation_reason(product, customer, baseline=None):
    if baseline and baseline["id"] != product["id"]:
        delta = product["price"] - baseline["price"]
        reason = f"INR {abs(delta):,} {'less' if delta < 0 else 'more'} than A"
        difference = (
            f"{product['refresh_rate']} Hz versus A's {baseline['refresh_rate']} Hz"
            if product["refresh_rate"] != baseline["refresh_rate"]
            else f"{product['size']}-inch {product['panel']}; check the difference against A in person"
        )
        return reason + "; " + difference
    home = customer["home"]
    reasons = []
    if any(word in home.get("use", "").casefold() for word in ("cricket", "sport", "gaming")):
        reasons.append(f"{product['refresh_rate']} Hz to compare motion for {home['use']}")
    if "bright" in home.get("light", "").casefold():
        reasons.append(f"{product['brightness']} nits to check in your daylight demo")
    if "side" in home.get("seating", "").casefold():
        reasons.append(f"{product['viewing_angle']} viewing angle; check the side seats")
    if not reasons:
        reasons.append(
            f"{product['size']}-inch {product['panel']}; compare for {home.get('use', 'the home')}"
        )
    budget = home.get("budget", "")
    reasons.append(
        "within the stated range"
        if re.search(r"\d", budget)
        else "spending range unknown; confirm fit before deciding"
    )
    tradeoff = (
        "check motion in the demo"
        if product["refresh_rate"] < 120
        else "confirm the price fits the customer"
    )
    return reasons[0] + "; " + tradeoff


def demo_plan(db, c, focus=""):
    names = ", ".join(p["model"] for id_ in c["selected"] if (p := get(db, "products", id_)))
    home = c["home"]
    checks = []
    for field, word, check in [
        ("use", "gaming", "controller response and game input"),
        ("use", "cricket", "ball motion in the same sports clip"),
        ("light", "bright", "reflections in daylight"),
        ("seating", "side", "picture from the family's side seats"),
        ("problem", "dialogue", "dialogue at the customer's listening volume"),
    ]:
        if word in home.get(field, "").casefold():
            checks.append(check)
    return [
        f"Physical demo: {names}.",
        "Check "
        + (
            focus
            or "; ".join(checks[:2])
            or "the customer's main use; ask what difference matters most"
        )
        + ".",
        "Use matched settings where comparing. Record preference and reason only after the demo.",
    ]


def act(db, c, user, action, data):
    c.pop("text_prompt", None)
    from app.web.flow import missing

    if c["sale"] and action in {
        "home",
        "confirm_home",
        "select",
        "preferred",
        "demo",
        "demo_unavailable",
        "start_demo",
        "site",
        "extras",
        "payment",
        "home_answer",
    }:
        raise HTTPException(
            409, "The test sale quote is frozen. Start a new visit to change purchased items."
        )
    if action in {"payment", "sale"}:
        require(
            not any(
                r["customer_id"] == c["id"] and r.get("blocking") and not r.get("decision_evidence")
                for r in read_all(db, "requests")
            ),
            "Resolve blocking compatibility, charge or finance requests before finalisation",
        )
    text = ""
    c.pop("chat_override", None)
    c["chat_mode"] = "flow"
    if action == "ask_home":
        field = missing(c)
        c["awaiting_home"] = field
        text = (
            HOME_FIELDS[field]
            if field
            else "Read the home card to the customer; correct any answer using Edit."
        )
    elif action == "home_answer":
        require(not c["confirmed"], "Edit the home card to change a confirmed assessment")
        require(
            data["field"] == missing(c),
            "That question is no longer pending. Refresh the conversation.",
        )
        require(bool(data["value"].strip()), "Record an answer or choose Unknown")
        c["home"][data["field"]] = data["value"].strip()
        c["awaiting_home"] = missing(c)
        text = "Customer answer saved: " + data["value"].strip()
    elif action == "offers":
        require(c["confirmed"] and c["demo"], "Confirm the home and physical demo before offers")
        require(
            quote(db, c)["total"] is not None,
            "Final total is pending. Complete the site check and confirm every charge first.",
        )
        c["stage"] = "close"
        text = "Assessment, physical demo and complete cost checked. Review the eligible offer and payment choices."
    elif action == "continue_flow":
        if c["stage"] == "review":
            c["stage"] = c.get("resume_stage") or (
                "handover"
                if c["sale"]
                else "close"
                if c["payment"]
                else "complete"
                if c["demo"]
                else "recommend"
                if c["confirmed"]
                else "assess"
            )
        c["awaiting_home"] = missing(c) if not c["confirmed"] else None
        text = "Continuing from the next pending step. Your saved details and requests stay with this customer."
    elif action == "ask_expert":
        c["chat_mode"] = "expert"
        c["expert_waiting"] = False
        c["expert_question_pending"] = True
        text = "What would you like to check? Type your question; I’ll use the home, selected TV and approved facts."
    elif action == "expert_resolved":
        c["expert_question_pending"] = False
        linked = get(db, "requests", c.get("active_request_id", ""))
        if linked and linked["customer_id"] == c["id"]:
            linked["status"] = "resolved"
            linked["thread"].append(
                {"by": user["name"], "role": "event", "text": "resolved", "at": now()}
            )
            put(db, "requests", linked)
        text = "Question marked resolved by the associate. Any linked admin request is resolved; the customer journey stays at its saved step."
    elif action == "explain_another":
        c["chat_mode"] = "translate"
        text = "Type a model number or feature label. I’ll explain it for this customer using approved facts."
    elif action == "home":
        updates = data.get("home", {})
        require(isinstance(updates, dict), "Home details must be an object")
        require(set(updates) <= set(HOME_FIELDS), "Unknown home field")
        c["home"].update({k: str(v)[:500] for k, v in updates.items()})
        c["confirmed"] = False
        c["site"] = {}
        c["demo"] = None
        c["sale"] = False
        c["payment"] = None
        c["awaiting_home"] = missing(c)
        text = "Home details saved. Review and confirm before recommendations."
    elif action == "confirm_home":
        require(
            all(c["home"].get(k) for k in HOME_FIELDS),
            "Complete each home field; use Unknown if the customer does not know.",
        )
        c["confirmed"] = True
        c["awaiting_home"] = None
        c["stage"] = "recommend"
        options = recommendations(db, c)
        c["selected"] = [p["id"] for p in options]
        c["preferred"] = None
        c["demo"] = None
        c["payment"] = None
        text = (
            "\n".join(f"{p['brand']} {p['model']}: {recommendation_reason(p, c)}" for p in options)
            or "No in-stock TV fits the recorded range. Discuss a different range or ask an expert."
        )
    elif action == "select":
        ids = data.get("products", [])
        require(
            isinstance(ids, list) and 1 <= len(ids) <= 3 and len(set(ids)) == len(ids),
            "Select one to three different TVs",
        )
        require(all(get(db, "products", id_) for id_ in ids), "Unknown TV")
        c["selected"] = ids
        c["site"] = {}
        c["demo"] = None
        c["preferred"] = None
        c["payment"] = None
        text = "TV shortlist saved. Use the same clip and picture settings for the physical demo."
    elif action == "preferred":
        require(data.get("product") in c["selected"], "Choose a shortlisted model")
        c["preferred"] = data["product"]
        if c["demo"] and c["demo"]["preferred"] != c["preferred"]:
            c["site"] = {}
            c["demo"] = None
            c["payment"] = None
        text = "Preferred TV saved. This does not confirm a sale."
    elif action == "start_demo":
        require(
            c["confirmed"] and len(c["selected"]) >= 1,
            "Confirm the home and select an available TV first",
        )
        c["selected"] = c["selected"][:2]
        c["stage"] = "demo"
        c["demo_plan"] = demo_plan(db, c, data.get("focus", ""))
        text = "\n".join(c["demo_plan"])
    elif action == "demo":
        require(
            c["confirmed"] and len(c["selected"]) >= 1, "Confirm home and choose a demo TV first"
        )
        require(
            data.get("preferred") in c["selected"] and len(data.get("reason", "").strip()) >= 5,
            "Record the customer's preferred TV and reason after a physical demo",
        )
        if c.get("preferred") != data["preferred"]:
            c["site"] = {}
            c["payment"] = None
        c["demo"] = {
            "preferred": data["preferred"],
            "reason": data["reason"][:1000],
            "at": now(),
            "actor": user["id"],
            "kind": "single TV" if len(c["selected"]) == 1 else "comparison",
        }
        c["preferred"] = data["preferred"]
        c["stage"] = "complete"
        text = "Physical demo evidence saved. Check the installation site and itemised cost next."
    elif action == "demo_unavailable":
        c["demo"] = None
        c["demo_unavailable_reason"] = data.get("reason", "Display unavailable")
        text = "Demo remains incomplete. Arrange another display model or ask an expert; offers stay locked."
        alternatives = [p for p in recommendations(db, c) if p["id"] not in c["selected"]]
        text += (
            " Available alternative: " + ", ".join(p["model"] for p in alternatives)
            if alternatives
            else " No further verified match in this range; ask an expert to arrange a display."
        )
    elif action == "site":
        require(
            data.get("placement") in ["Wall", "Table"]
            and data.get("specialist") in ["yes", "no", "unknown"],
            "Confirm wall/table and specialist work",
        )
        require(
            len(data.get("notes", "").strip()) >= 5,
            "Record power, cable route, wall/access and connected-device checks",
        )
        checks = {
            k: str(data.get(k, "")).strip() for k in ("power", "cable_route", "access", "devices")
        }
        require(
            all(checks.values()),
            "Answer power, cable route, wall/access and device checks individually; use Unknown when needed",
        )
        c["payment"] = None
        c["site"] = {
            **checks,
            "placement": data["placement"],
            "specialist": data["specialist"],
            "notes": data["notes"][:1000],
            "confirmed": data["specialist"] != "unknown"
            and all(
                v.strip() != "?"
                and not re.search(
                    r"\b(?:unknown|not confirmed|not checked|unverified|unsure|maybe|pending|don't know)\b|माहीत नाही|पता नहीं",
                    v,
                    re.I,
                )
                for v in checks.values()
            ),
        }
        c["home"]["placement"] = data["placement"]
        text = "Site check saved. Specialist work remains unconfirmed when required."
    elif action == "extras":
        require(
            isinstance(data.get("extras"), list)
            and set(data["extras"]) <= {"soundbar", "protection"},
            "Unknown optional item",
        )
        c["extras"] = list(set(data["extras"]))
        c["payment"] = None
        text = "Chosen optional extras saved; quote recalculated."
    elif action == "payment":
        require(c["confirmed"] and c["demo"], "Assessment and actual demonstration are required")
        require(
            quote(db, c)["total"] is not None,
            "Confirm all charges and site needs before payment preference",
        )
        require(data.get("method") in ["full", "finance"], "Choose full payment or finance")
        c["payment"] = data["method"]
        c["stage"] = "close"
        text = "Payment preference saved. No payment collected or finance approved. Review the refreshed total before explicit test sale confirmation."
    elif action == "sale":
        q = quote(db, c)
        require(
            c["payment"] and c["demo"] and c["confirmed"] and q["total"] is not None,
            "Complete assessment, demo, site check and payment preference",
        )
        require(not c["sale"], "Sale is already recorded")
        p = get(db, "products", c["preferred"])
        require(
            p and p["stock"] > 0, "Selected TV is out of stock; choose an available alternative"
        )
        require(
            data.get("confirmed_total") == (q["finance"]["total"] if q["finance"] else q["total"]),
            "Quote changed. Review and confirm the current payable amount",
        )
        c["sale"] = True
        c["stage"] = "handover"
        c["sale_quote"] = q
        p["stock"] -= 1
        p["version"] += 1
        put(db, "products", p)
        for kind, days, owner in [
            ("delivery", 1, "Store logistics"),
            ("installation", 2, "Installation desk"),
            ("working_check", 3, user["name"]),
        ]:
            new_task(
                db,
                c,
                kind,
                owner,
                (datetime.now(UTC) + timedelta(days=days)).isoformat(),
                "Requested time; slot pending confirmation",
            )
        text = "Test sale explicitly confirmed. Separate delivery, installation and working-check tasks created. Requested slots are pending."
    elif action == "consent":
        require(isinstance(data.get("given"), bool), "Record explicit consent choice")
        c["consent"] = data["given"]
        c["consent_recorded"] = True
        if not c["consent"]:
            for share in read_all(db, "shares"):
                if share["customer_id"] == c["id"]:
                    share["revoked"] = True
                    put(db, "shares", share)
        text = (
            "Consent recorded for sharing this summary and updates."
            if c["consent"]
            else "Consent declined. Summary remains internal and previous links are revoked."
        )
    elif action == "followup":
        require(isinstance(data.get("consent"), bool), "Record follow-up consent")
        try:
            due = datetime.fromisoformat(data.get("due_at", ""))
            require(
                due.tzinfo is not None and due > datetime.now(UTC),
                "Choose a future time with timezone",
            )
        except ValueError as exc:
            raise HTTPException(422, "Invalid follow-up time") from exc
        require(
            len(data.get("reason", "")) >= 3 and len(data.get("owner", "")) >= 2,
            "Record a reason and owner",
        )
        new_task(
            db,
            c,
            "followup",
            data["owner"][:100],
            due.isoformat(),
            data["reason"][:1000],
            data["consent"],
        )
        c["chat_mode"] = "followup_saved"
        text = (
            "Follow-up saved with owner and agreed time."
            if data["consent"]
            else "Internal follow-up saved. Customer contact is not consented."
        )
    elif action == "language":
        require(data.get("language") in ["English", "Hindi", "Marathi"], "Unsupported language")
        c["language"] = data["language"]
        text = "Coaching language updated. Model names and amounts stay unchanged."
    elif action == "note":
        require(bool(data.get("text", "").strip()), "Enter a visit note")
        c["notes"].append({"text": data["text"][:3000], "by": user["name"], "at": now()})
        text = "Visit note saved to the history."
    elif action == "correction":
        require(c["sale"], "Use the editable quote before sale confirmation")
        new_task(
            db,
            c,
            "purchase_correction",
            "Store manager",
            (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            data["reason"],
            False,
        )
        text = "Purchase correction requested for store-manager review. The confirmed purchase and stock remain frozen; no changed amount is approved by this request."
    elif action == "end_visit":
        if c["stage"] != "closed":
            if c["stage"] != "review":
                c["resume_stage"] = c["stage"]
            c["stage"] = "review"
        text = "Visit saved. Pending tasks and expert requests stay open. Resume this customer any time."
    else:
        raise HTTPException(422, "Unknown workflow action")
    message(c, "event", text, actor=user["name"], action=action)
    touch(db, c, user, action)
    return c


def score(c, tasks, current_quote=None):
    def coaching(kind):
        messages = [m for m in c["messages"] if m.get("coaching_type") == kind]
        supported = any(m.get("sources") for m in messages)
        observed = c.get("coaching_evidence", {}).get(kind)
        return 2 if supported and observed else int(supported)

    complete = (
        bool(c["site"].get("confirmed"))
        and current_quote is not None
        and current_quote["total"] is not None
    )
    points = {
        "Validate": coaching("validate"),
        "Assess": 2 if c["confirmed"] else int(bool(c["home"])),
        "Translate": coaching("translate"),
        "Demonstrate": 2
        if c["demo"]
        else int(c["stage"] == "demo" or bool(c.get("demo_unavailable_reason"))),
        "Complete": 2 if complete else int(bool(c["site"] or c["extras"])),
        "Close": 2 if c["sale"] else int(bool(c["payment"])),
        "Follow through": 2
        if any(t["kind"] == "working_check" and t["status"] == "completed" for t in tasks)
        else int(any(t["status"] in ["confirmed", "completed"] for t in tasks)),
    }
    applicable = {
        "Validate": bool(points["Validate"]),
        "Assess": True,
        "Translate": bool(c["confirmed"] or points["Translate"]),
        "Demonstrate": bool(c["confirmed"]),
        "Complete": bool(c["demo"]),
        "Close": complete,
        "Follow through": bool(c["sale"]),
    }
    return [
        {
            "step": k,
            "points": v,
            "applicable": applicable[k] or c["stage"] == "closed",
            "status": "complete"
            if v == 2
            else "partial evidence"
            if v == 1
            else "missed"
            if c["stage"] == "closed"
            else "pending"
            if applicable[k]
            else "not yet applicable",
        }
        for k, v in points.items()
    ]
