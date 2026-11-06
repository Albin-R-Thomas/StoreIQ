import json
from pathlib import Path

from app.main import app

destination = Path(__file__).resolve().parents[1] / "postman/specs/store-iq.openapi.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"Exported {destination}")
