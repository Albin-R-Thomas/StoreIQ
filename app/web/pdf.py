"""Generate a paginated customer-safe PDF from the saved quote."""

import re
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

pdfmetrics.registerFont(
    TTFont(
        "StoreDevanagari", str(Path(__file__).with_name("fonts") / "NotoSansDevanagari-Regular.ttf")
    )
)


def render_summary(q):
    stream = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Label",
            fontName="Helvetica",
            fontSize=8,
            leading=13,
            textColor=colors.HexColor("#6c7d65"),
        )
    )
    styles.add(ParagraphStyle(name="Amount", parent=styles["BodyText"], alignment=TA_RIGHT))
    for key in ["BodyText", "Normal"]:
        styles[key].fontSize = 9
        styles[key].leading = 15
    for style in styles.byName.values():
        style.shaping = 1

    def p(text, style="BodyText"):
        clean = (
            str(text).replace("₹", "INR ").replace("×", "x").replace("·", " | ").replace("–", "-")
        )
        clean = re.sub(
            r"([\u0900-\u097f]+)", r'<font name="StoreDevanagari">\1</font>', escape(clean)
        )
        return Paragraph(clean, styles[style])

    story = [
        p("STORE IQ / TV SPECIALIST", "Label"),
        Spacer(1, 9 * mm),
        p(q["customer"]["name"] + " - TV summary", "Title"),
        p(q["kind"], "Heading2"),
        p(
            f"Customer serial: {q['customer']['serial']} | Contact owner: {q.get('contact_owner', q['associate'])}"
        ),
        p(
            f"Prepared by {q['associate']} | Version {q['version']} | {q['generated_at'][:10]}",
            "Label",
        ),
        Spacer(1, 7 * mm),
    ]
    home = [p(f"{k.capitalize()}: {v}") for k, v in q["home"].items()]
    home_rows = [home[i : i + 2] for i in range(0, len(home), 2)]
    if home_rows and len(home_rows[-1]) == 1:
        home_rows[-1].append("")
    if home_rows:
        home_table = Table(home_rows, colWidths=[82 * mm, 83 * mm])
        home_table.setStyle(
            TableStyle(
                [("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]
            )
        )
        story.append(home_table)
    story += [Spacer(1, 7 * mm), p("Your complete solution", "Heading2")]
    if q.get("compared"):
        story.append(
            p("Demo shortlist: " + ", ".join(v["brand"] + " " + v["model"] for v in q["compared"]))
        )
    if q.get("site"):
        story.append(p("Installation site", "Heading3"))
        story.extend(
            p(f"{k.replace('_', ' ')}: {v}") for k, v in q["site"].items() if k != "confirmed"
        )
    if q["product"]:
        story.append(
            p(
                q["product"]["brand"]
                + " "
                + q["product"]["model"]
                + f" / {q['product']['size']} inch {q['product']['panel']}"
            )
        )
    rows = [[p(line["label"]), p(f"INR {line['amount']:,}", "Amount")] for line in q["lines"]]
    rows.append(
        [
            p("Known subtotal" if q["total"] is None else "Payable total"),
            p(f"INR {q['subtotal']:,}", "Amount"),
        ]
    )
    table = Table(rows, colWidths=[125 * mm, 40 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e0e7d9")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#edf3e5")),
            ]
        )
    )
    story.append(table)
    story.append(
        p(
            f"Required items: INR {q.get('required_total', q['subtotal']):,} | Optional items: INR {q.get('optional_total', 0):,}"
        )
    )
    story.extend(
        p(line["label"] + ": " + line["description"])
        for line in q["lines"]
        if line.get("description")
    )
    if q["missing"]:
        story += [Spacer(1, 5 * mm), p("Final total pending", "Heading3")]
        story.extend(p(m) for m in q["missing"])
    if q["offer"]:
        story += [
            Spacer(1, 5 * mm),
            p(q["offer"]["title"], "Heading3"),
            p(q["offer"]["conditions"]),
            p(f"Valid {q['offer']['starts_on']} to {q['offer']['ends_on']}", "Label"),
        ]
    if q["finance"]:
        f = q["finance"]
        story += [
            p("Full finance cost", "Heading3"),
            p(
                f"Upfront INR {f['upfront']:,} + {f['months']} EMIs of INR {f['emi']:,} + fee INR {f['fees']:,} = INR {f['total']:,}. APR {f['apr']}%. {f['status']}."
            ),
        ]
    if q["demo"]:
        story += [p("Why this screen", "Heading3"), p(q["demo"]["reason"])]
    if q["tasks"]:
        story.append(p("Delivery, installation and working check", "Heading3"))
        for task in q["tasks"]:
            story.append(
                p(
                    f"{task['kind'].replace('_', ' ')}: {task['status']} | {task['assigned_to']} | {task['due_at'][:16]} UTC"
                )
            )
    story += [
        Spacer(1, 8 * mm),
        p(
            "Synthetic contest data. No real payment collected. Requested slots require confirmation. Unconfirmed amounts remain pending. Original-language text is available in the web summary.",
            "Label",
        ),
    ]

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#8c9c80"))
        canvas.drawString(22 * mm, 13 * mm, "Store IQ | Customer summary | Synthetic demo")
        canvas.drawRightString(188 * mm, 13 * mm, f"Page {doc.page}")

    SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title="Store IQ customer summary",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
