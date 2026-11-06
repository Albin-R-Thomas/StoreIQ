"""Server-owned conversational prompts and buttons for the text-only web journey."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.web import domain
from app.web.intelligence import HOME_FIELDS
from app.web.localization import localize_flow
from app.web.store import get, put, read_all


def button(label, kind, name, data=None):
    return {"label": label, "kind": kind, "name": name, "data": data or {}}


def action(label, name, data=None):
    return button(label, "action", name, data)


def form(label, name, data=None):
    return button(label, "input", name, data)


def nav(label, name):
    return button(label, "navigate", name)


def money(value):
    return "Not confirmed" if value is None else f"INR {value:,}"


def missing(c):
    return next((key for key in HOME_FIELDS if not c["home"].get(key, "").strip()), None)


def build(db, c):
    """Pure presentation: viewing a prompt never changes business state."""
    mode = c.get("chat_mode", "flow")
    question = missing(c)
    quote = domain.quote(db, c)
    base = {
        "step": c["stage"],
        "mode": mode,
        "question": question,
        "placeholder": "Share the customer's answer, or ask a question…",
        "quote": quote,
        "buttons": [],
        "lines": [],
    }
    if c.get("text_prompt"):
        base.update(c["text_prompt"])
        return base
    if c.get("chat_override"):
        base.update(
            lines=[
                c.get("chat_override_text")
                or "Use the action below to continue with the saved customer."
            ],
            buttons=[c["chat_override"]],
        )
    elif mode == "followup_saved":
        base.update(
            lines=[
                "The follow-up has an owner, agreed time and recorded contact permission.",
                "The selected TV and pending expert questions stay with this visit.",
                "Continue, save the visit, or review the summary.",
            ],
            buttons=[
                action("Continue flow", "continue_flow"),
                action("End visit", "end_visit"),
                nav("Open summary", "summary"),
            ],
        )
    elif mode == "expert":
        base.update(
            lines=[
                "What would you like to check? Type your question."
                if c.get("expert_question_pending")
                else "Check the answer and its supporting facts.",
                "Resolve this question, involve an admin, or ask a follow-up.",
            ],
            buttons=[
                action("Resolved", "expert_resolved"),
                form("Ask admin", "expert"),
                action("Ask follow-up", "ask_expert"),
            ],
            placeholder="Type your expert question or follow-up…",
        )
        linked = get(db, "requests", c.get("active_request_id", ""))
        if c.get("expert_waiting") and linked and linked["status"] in ["waiting", "assigned"]:
            base.update(
                lines=[
                    f"Request #{linked['number']}: "
                    + (
                        f"Assigned to {linked['assigned_to']}."
                        if linked["assigned_to"]
                        else "Waiting for assignment."
                    ),
                    "Request sent. You can continue with other questions.",
                    "The answer remains unconfirmed until an admin replies.",
                ],
                buttons=[
                    action("Continue flow", "continue_flow"),
                    nav("View request", "requests"),
                    form("Save follow-up", "followup"),
                ],
            )
    elif mode == "validate":
        base.update(
            lines=[
                "Show the difference for this customer's home.",
                "The visit stays at the same step while you clear their doubt.",
            ],
            buttons=[
                nav("Show comparison", "compare"),
                action("Ask an expert", "ask_expert"),
                action("Continue flow", "continue_flow"),
            ],
        )
    elif mode == "translate":
        base.update(
            lines=[
                "Explain the feature in terms of this home.",
                "Choose another model or label if this was not the right TV.",
            ],
            buttons=[
                nav("Compare", "compare"),
                action("Explain another", "explain_another"),
                form("Wrong model", "select"),
            ],
        )
    elif c["stage"] in ["review", "closed"]:
        tasks = [t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]]
        scores = domain.score(c, tasks, domain.quote(db, c))
        earned = sum(s["points"] for s in scores)
        pending = [s["step"] for s in scores if s["points"] < 2]
        improvements = {
            "Validate": "acknowledge the true part, clarify the difference, then record the customer's response",
            "Assess": "ask the next missing home question before recommending",
            "Translate": "explain one feature for this home and record what the customer understood",
            "Demonstrate": "show the same clip and record the customer's preferred TV and reason",
            "Complete": "check site needs and confirm every required charge",
            "Close": "review the payable amount before explicit sale confirmation",
            "Follow through": "confirm picture, sound, devices and satisfaction after installation",
        }
        base.update(
            lines=[
                f"Visit score: {earned}/{2 * sum(s['applicable'] for s in scores)}"
                + (" final." if c["stage"] == "closed" else "; remaining steps are pending."),
                "Done well: "
                + (next((s["step"] for s in scores if s["points"]), "visit details saved"))
                + ".",
                "Next time: "
                + (improvements[pending[0]] if pending else "keep checking until the TV works")
                + ".",
            ],
            buttons=[
                form("See score", "score"),
                action("Continue flow", "continue_flow"),
                nav("New customer", "new_customer"),
            ],
        )
    elif c["sale"]:
        if not c.get("consent_recorded"):
            base.update(
                lines=[
                    f"Confirm {quote['product']['brand']} {quote['product']['model']}; payable {money(quote['finance']['total'] if quote['finance'] else quote['total'])}.",
                    "Delivery and installation have separate owners; requested slots are pending.",
                    "May we share the customer summary and updates?",
                ],
                buttons=[
                    action("Consent given", "consent", {"given": True}),
                    action("No consent", "consent", {"given": False}),
                    nav("Review details", "summary"),
                ],
            )
        else:
            tasks = [
                t
                for t in read_all(db, "tasks")
                if t["customer_id"] == c["id"] and t["status"] != "completed"
            ]
            task = next(
                (
                    t
                    for kind in ("delivery", "installation", "working_check", "followup")
                    for t in tasks
                    if t["kind"] == kind
                ),
                None,
            )
            if task:
                base.update(
                    lines=[
                        f"{task['kind'].replace('_', ' ').capitalize()}: {task['status']}. Requested slots need confirmation.",
                        f"Owner: {task['assigned_to']}. Next update: {task['due_at'][:16]} UTC.",
                        "Confirm only what was actually completed, or record the issue.",
                    ],
                    buttons=[
                        form("Completed", "task", {"task_id": task["id"], "status": "completed"}),
                        form("Problem", "task", {"task_id": task["id"], "status": "problem"}),
                        action("Ask an expert", "ask_expert"),
                    ],
                )
            else:
                base.update(
                    lines=[
                        "Delivery, installation and working check are recorded.",
                        "Open the saved summary or review the conversation.",
                    ],
                    buttons=[
                        nav("Open summary", "summary"),
                        action("End visit", "end_visit"),
                        nav("New customer", "new_customer"),
                    ],
                )
    elif not c["confirmed"]:
        if question:
            base.update(
                lines=[
                    f'Ask: "{HOME_FIELDS[question]}"',
                    "Tell me the customer's answer. I’ll remember the rest.",
                ],
                buttons=[
                    action("Ask customer", "ask_home"),
                    action("Unknown", "home_answer", {"field": question, "value": "Unknown"}),
                    form("Edit details", "home"),
                ],
                placeholder=f"Customer’s answer · {question}…",
            )
        else:
            h = c["home"]
            base.update(
                lines=[
                    f"Home: {h['distance']}; {h['light']}; {h['seating']}; {h['placement']}.",
                    f"Use: {h['use']}. Wants: {h['problem']}. Range: {h['budget']}.",
                    "Is this right?",
                ],
                buttons=[
                    action("Correct", "confirm_home"),
                    form("Edit", "home"),
                    action("Ask customer", "ask_home"),
                ],
            )
    elif not c["demo"]:
        if c["stage"] == "demo":
            base.update(
                lines=c.get("demo_plan") or domain.demo_plan(db, c),
                buttons=[
                    form("Demo done", "demo"),
                    form("Need another demo", "start_demo"),
                    form("Demo unavailable", "demo_unavailable"),
                ],
            )
        elif not c["selected"]:
            base.update(
                lines=[
                    "No in-stock TV matches the saved range and preferences.",
                    "Change the range or preferences with the customer, or ask an expert.",
                ],
                buttons=[
                    form("Change options", "select"),
                    nav("Stock details", "stock"),
                    action("Ask an expert", "ask_expert"),
                ],
            )
        else:
            products = [get(db, "products", id_) for id_ in c["selected"]]
            base.update(
                lines=[
                    f"{chr(65 + i)}: {p['brand']} {p['model']} — {domain.recommendation_reason(p, c, products[0] if i else None)}."
                    for i, p in enumerate(products)
                    if p
                ],
                buttons=[
                    action("Demo TV" if len(c["selected"]) == 1 else "Demo A/B", "start_demo"),
                    form("Change options", "select"),
                    nav("Stock details", "stock"),
                ],
            )
            if len(products) == 1:
                base["lines"].append(
                    "Only one in-stock TV matches the saved range and preferences. Demonstrate this TV without claiming a comparison."
                )
    elif quote.get("product") and quote["product"]["stock"] == 0:
        base.update(
            lines=[
                f"{quote['product']['model']} is currently out of stock.",
                f"Confirmed expected availability: {quote['product']['expected_on'] or 'Not confirmed'}. Reconfirm price and offers on return.",
                "May we follow up? If yes, agree a time and owner.",
            ],
            buttons=[
                form("Save follow-up", "followup"),
                action("Other TV", "confirm_home"),
                action("End visit", "end_visit"),
            ],
        )
    elif c["stage"] == "complete" or not c["site"].get("confirmed"):
        amount = money(quote["total"] if quote["total"] is not None else quote["subtotal"])
        charges = "; ".join(
            f"{line['label']}: {money(line['amount'])}"
            for line in quote["lines"]
            if not line.get("optional")
        )
        base.update(
            lines=[
                charges + ".",
                "Final total pending: " + "; ".join(quote["missing"])
                if quote["missing"]
                else f"Confirmed required total: {money(quote['required_total'])}.",
                f"Known selected cost {amount}; optional extras {money(quote['optional_total'])}. Check site before continuing.",
            ],
            buttons=[
                form("Optional extras", "extras"),
                form("Site check", "site"),
                action("Continue", "offers"),
            ],
        )
    elif not c["payment"]:
        offer = quote["offer"]
        base.update(
            lines=[
                f"{quote['product']['model']} fits the saved home and demonstrated preference.",
                (
                    f"Eligible offer: {offer['title']}, {money(offer['discount'])}; ends {offer['ends_on']}. {offer['conditions']}"
                    if offer
                    else "No currently eligible promotional offer is confirmed."
                ),
                f"Final payable: {money(quote['total'])}. How would they like to proceed?",
            ],
            buttons=[
                action("Pay in full", "payment", {"method": "full"}),
                action("Finance", "payment", {"method": "finance"}),
                form("Save for later", "followup"),
            ],
        )
    else:
        finance = quote["finance"]
        detail = (
            f"Upfront {money(finance['upfront'])} + {finance['months']} EMIs of {money(finance['emi'])} + fees {money(finance['fees'])} = {money(finance['total'])}; APR {finance['apr']}%, subject to approval."
            if finance
            else f"Pay in full preference: {money(quote['total'])}."
        )
        base.update(
            lines=[
                detail,
                "No payment has been collected and no sale is recorded yet.",
                "Confirm the test sale explicitly, save it, or review the summary.",
            ],
            buttons=[
                form("Confirm sale", "sale"),
                form("Save for later", "followup"),
                nav("Open summary", "summary"),
            ],
        )
    base["lines"] = base["lines"][:3]
    return localize_flow(base, c)


def present(db, c):
    tasks = [t for t in read_all(db, "tasks") if t["customer_id"] == c["id"]]
    return {**c, "flow": build(db, c), "score": domain.score(c, tasks, domain.quote(db, c))}


def reply(db, c, request_id, user):
    switched = next(
        (
            m.get("resume_customer_id")
            for m in reversed(c["messages"])
            if m.get("request_id") == request_id and m.get("resume_customer_id")
        ),
        None,
    )
    return present(db, domain.owned(db, "customers", switched, user) if switched else c)


def append_prompt(db, c):
    flow = build(db, c)
    domain.message(c, "assistant", "\n".join(flow["lines"]), buttons=flow["buttons"], guided=True)
    put(db, "customers", c)


COMMANDS = {
    "correct": ("confirm_home", {}),
    "demo a/b": ("start_demo", {}),
    "start demo": ("start_demo", {}),
    "need another demo": ("start_demo", {}),
    "continue": ("offers", {}),
    "continue flow": ("continue_flow", {}),
    "pay in full": ("payment", {"method": "full"}),
    "finance": ("payment", {"method": "finance"}),
    "consent given": ("consent", {"given": True}),
    "no consent": ("consent", {"given": False}),
    "ask an expert": ("ask_expert", {}),
    "ask follow-up": ("ask_expert", {}),
    "resolved": ("expert_resolved", {}),
    "explain another": ("explain_another", {}),
    "end visit": ("end_visit", {}),
    "customer left": ("end_visit", {}),
    **{
        lang.casefold(): ("language", {"language": lang})
        for lang in ("English", "Hindi", "Marathi")
    },
}


INPUT_COMMANDS = {
    "edit": "home",
    "demo done": "demo",
    "demo unavailable": "demo_unavailable",
    "change options": "select",
    "optional extras": "extras",
    "site check": "site",
    "save follow-up": "followup",
    "save for later": "followup",
    "confirm sale": "sale",
    "ask admin": "expert",
    "see score": "score",
}
NAV_COMMANDS = {
    "summary": "summary",
    "open summary": "summary",
    "compare": "compare",
    "show comparison": "compare",
    "view stock": "stock",
    "stock details": "stock",
    "practice": "training",
    "customer list": "customers",
    "start shift": "shift",
    "my customers": "customers",
    "view history": "history",
    "new customer": "new_customer",
    "share summary": "summary",
    "generate pdf": "summary",
    "download pdf": "summary",
}


def is_question(text):
    return bool(
        re.search(
            r"\?|^\s*(what|how|which|does|can|is|are|explain|check|compare)\b|customer says|क्या|कौन|कैसे|कोण|काय|कसा|विचारू|समझाऊँ",
            text,
            re.I,
        )
    )


def multiple_home_facts(text):
    groups = (
        r"\b(feet|ft|metres?|meters?)\b",
        r"\b(bright|sunlight|daylight|dark)\b",
        r"\b(cricket|sports?|movies?|gaming)\b",
        r"\b(side|sides|seating)\b",
        r"\b(wall|table)\b",
        r"\b(budget|range|lakh|rupees)\b",
    )
    return sum(bool(re.search(pattern, text, re.I)) for pattern in groups) > 1


def handle_text(db, c, text, user, request_id):
    """Handle exact commands and explicitly requested single-field answers without AI."""
    from app.web import conversation

    command = conversation.canonical(text)
    if conversation.handle(db, c, text, user, request_id):
        return True
    c.pop("text_prompt", None)
    pending_field = missing(c)
    exact_answers = {
        "distance": r"\d+(?:\.\d+)?\s*(?:feet|ft|meters?|metres?)",
        "light": r"(?:bright(?: daylight)?|sunny|dark|dim|no direct sunlight)",
        "use": r"(?:cricket|sports|movies|gaming|netflix|channels)(?: and (?:movies|cricket|gaming))?",
        "seating": r"(?:sides|on the sides|side seating|front|in front|straight ahead)",
        "problem": r"(?:motion blur|blurry picture|muffled dialogue|poor sound|reflections)",
        "placement": r"(?:wall|table|cabinet|stand)",
        "budget": r"(?:\d[\d,]*(?:\s*(?:k|lakh|rupees))?)",
    }
    if (
        not c["confirmed"]
        and c.get("chat_mode", "flow") == "flow"
        and pending_field
        and (
            command in ["unknown", "not sure", "don't know"]
            or re.fullmatch(exact_answers[pending_field], command)
        )
    ):
        domain.act(
            db,
            c,
            user,
            "home_answer",
            {
                "field": pending_field,
                "value": "Unknown" if command in ["unknown", "not sure", "don't know"] else text,
            },
        )
        append_prompt(db, c)
        c["messages"][-1]["request_id"] = request_id
        put(db, "customers", c)
        return True
    price_models = [
        p
        for p in read_all(db, "products")
        if p["model"].casefold() in command
        or p["id"].casefold() in command
        or (p["brand"].casefold() in command and p["model"].split()[-1].casefold() in command)
    ]
    if command == "demo done":
        c["awaiting_demo_preference"] = True
        domain.message(
            c,
            "assistant",
            "Which TV did they prefer, and why? Type the model and reason.",
            request_id=request_id,
        )
        domain.touch(db, c, user, "demo_preference_question")
        return True
    if c.get("awaiting_demo_preference"):
        matches = [
            p
            for p in read_all(db, "products")
            if p["id"] in c["selected"] and p["model"].casefold() in command
        ]
        if len(matches) == 1 and "because" in command:
            reason = text[command.index("because") + 7 :].strip()
            if len(reason) >= 5:
                domain.act(db, c, user, "demo", {"preferred": matches[0]["id"], "reason": reason})
                c.pop("awaiting_demo_preference", None)
                append_prompt(db, c)
                c["messages"][-1]["request_id"] = request_id
                put(db, "customers", c)
                return True
    if c.get("awaiting_preference") == "max_size" and re.fullmatch(
        r"\d{2,3}(?:\s*(?:inch|inches|in|\"))?", command
    ):
        size = int(re.search(r"\d+", command)[0])
        domain.require(24 <= size <= 120, "Choose a TV size from 24 to 120 inches")
        c.setdefault("preferences", {})["max_size"] = size
        c.pop("awaiting_preference", None)
        c["selected"] = [p["id"] for p in domain.recommendations(db, c)] if c["confirmed"] else []
        domain.message(
            c, "assistant", f"Maximum screen size saved: {size} inches.", request_id=request_id
        )
        domain.touch(db, c, user, "preferences")
        append_prompt(db, c)
    elif re.search(r"\bcustomers\b", command) and re.search(
        r"from|yesterday|today|dates|between", command
    ):
        dates = re.findall(
            r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}\s+[a-z]+\s+\d{4}", command
        )
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        try:
            if "yesterday" in command:
                first = last = today - timedelta(days=1)
            elif "today" in command:
                first = last = today
            elif len(dates) in [1, 2]:
                parsed = []
                for value in dates:
                    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"]:
                        try:
                            parsed.append(datetime.strptime(value, fmt).date())
                            break
                        except ValueError:
                            pass
                    else:
                        raise ValueError()
                first, last = domain.date_range(parsed[0].isoformat(), parsed[-1].isoformat())
            else:
                raise ValueError()
            matches = [
                v
                for v in read_all(db, "customers")
                if (user["role"] == "admin" or v["owner"] == user["id"])
                and any(
                    first
                    <= datetime.fromisoformat(t).astimezone(ZoneInfo("Asia/Kolkata")).date()
                    <= last
                    for t in v["activities"]
                )
            ]
            data = {"start": first.isoformat(), "end": last.isoformat()}
            buttons = [
                button("Open customers", "navigate", "customers", data),
                nav("Change dates", "customers"),
            ]
            reply = f"{len(matches)} customers active from {first} to {last}. Open the filtered list to resume a saved visit."
        except (ValueError, HTTPException):
            buttons = [nav("Change dates", "customers")]
            reply = "Choose a valid date range with the start before the end. Use YYYY-MM-DD or an unambiguous date such as 1 Nov 2026."
        domain.message(c, "assistant", reply, buttons=buttons, request_id=request_id)
        c["chat_override"] = buttons[0]
        c["chat_override_text"] = reply
        domain.touch(db, c, user, "customer_date_search")
        return True
    elif re.search(r"change options|smaller size|other brand|another brand|lower range", command):
        domain.require(
            not c["sale"], "Purchased items are frozen; start a new visit for another selection"
        )
        reference = get(
            db, "products", c.get("preferred") or (c["selected"][0] if c["selected"] else "")
        )
        if not reference:
            reference = next(
                (
                    p
                    for m in reversed(c["messages"])
                    for p in read_all(db, "products")
                    if p["model"].casefold() in m["text"].casefold()
                ),
                None,
            )
        preferences = c.setdefault("preferences", {})
        if "smaller" in command:
            if reference:
                preferences["max_size"] = reference["size"] - 1
            else:
                c["awaiting_preference"] = "max_size"
                domain.message(
                    c,
                    "assistant",
                    "What maximum screen size should I use? Type the size in inches.",
                    request_id=request_id,
                )
        if re.search(r"other brand|another brand", command) and reference:
            preferences["exclude_brand"] = reference["brand"]
        if "lower range" in command:
            c["home"].pop("budget", None)
            c["confirmed"] = False
            c["awaiting_home"] = "budget"
        c.update(demo=None, payment=None, preferred=None, site={})
        c["selected"] = [p["id"] for p in domain.recommendations(db, c)] if c["confirmed"] else []
        c["stage"] = "recommend" if c["confirmed"] else "assess"
        domain.message(
            c,
            "assistant",
            "Preferences saved: "
            + str(preferences)
            + ". "
            + (
                "What spending range should I use?"
                if "lower range" in command
                else "I will use these constraints for the stock shortlist."
            ),
            request_id=request_id,
        )
        domain.touch(db, c, user, "preferences")
        append_prompt(db, c)
    elif re.search(r"\b(price|cost|how much)\b", command) and len(price_models) == 1:
        p = price_models[0]
        domain.message(
            c,
            "assistant",
            f"{p['brand']} {p['model']}: current TV price {money(p['price'])}. Installation and optional items are separate. Source: approved store catalogue.",
            sources=[
                {
                    "id": p["id"],
                    "title": "Approved structured catalogue",
                    "text": f"TV price: {p['price']}",
                }
            ],
            request_id=request_id,
        )
        domain.touch(db, c, user, "price_question")
        append_prompt(db, c)
    elif command in COMMANDS:
        name, values = COMMANDS[command]
        domain.act(db, c, user, name, values)
        append_prompt(db, c)
    elif command in INPUT_COMMANDS or command in NAV_COMMANDS:
        target = INPUT_COMMANDS.get(command) or NAV_COMMANDS[command]
        kind = "input" if command in INPUT_COMMANDS else "navigate"
        domain.message(
            c,
            "assistant",
            "Use the action below to continue with the saved customer.",
            buttons=[button(text.strip(), kind, target)],
            guided=True,
            request_id=request_id,
        )
        c["chat_override"] = {"label": text.strip(), "kind": kind, "name": target, "data": {}}
        domain.touch(db, c, user, "chat_command")
        return True
    elif (
        c.get("awaiting_home")
        and c.get("chat_mode", "flow") == "flow"
        and not c["confirmed"]
        and bool(
            re.fullmatch(
                r"unknown|not sure|don't know|(?:[0-9]+(?:\.[0-9]+)?\s*(?:feet|ft|meters?|metres?))",
                command,
            )
        )
        and (command in ["unknown", "not sure", "don't know"] or c["awaiting_home"] == "distance")
        and not re.search(r"\?|customer says|explain|offer|price|expert|compare", command)
    ):
        field = c["awaiting_home"]
        domain.act(
            db,
            c,
            user,
            "home_answer",
            {
                "field": field,
                "value": "Unknown"
                if command in ["unknown", "not sure", "don't know"]
                else text[:500],
            },
        )
        append_prompt(db, c)
    else:
        return False
    c["messages"][-1]["request_id"] = request_id
    put(db, "customers", c)
    return True
