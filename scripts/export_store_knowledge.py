"""Export stable approved facts for review. No stock, prices or offers included."""

from pathlib import Path

from app.web.intelligence import stable_chunks
from app.web.store import initialize, read_all, transaction

initialize()
with transaction() as db:
    chunks = stable_chunks(read_all(db, "products"), read_all(db, "knowledge"))
document = "# Store IQ approved demonstration knowledge\n\n"
document += (
    "All store and TV figures below are synthetic contest facts, not manufacturer claims.\n\n"
)
document += (
    "Prices, inventory, arrivals, dated offers, charges and finance are intentionally excluded. "
)
document += "They are supplied as structured message context at request time. "
document += (
    "The admin edits the authoritative records in Store management; this is a review export.\n\n"
)
document += "\n\n".join(
    f"## {chunk['title']}\n\nReference: `{chunk['id']}`\n\n{chunk['text']}" for chunk in chunks
)
destination = Path("docs/store-knowledge.md")
destination.write_text(document + "\n", encoding="utf-8")
print(f"Exported {len(chunks)} stable fact passages to {destination}")
