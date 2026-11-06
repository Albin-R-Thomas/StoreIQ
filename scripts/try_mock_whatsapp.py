"""Exercise the running mock channel without a phone, provider or AI request."""

import argparse
import getpass
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--phone", default="9000000001")
    args = parser.parse_args()
    password = getpass.getpass("Store IQ password: ")
    with httpx.Client(base_url=args.url, timeout=60) as client:
        login = client.post("/api/auth/login", json={"phone": args.phone, "password": password})
        login.raise_for_status()
        response = client.post("/api/customers", json={"name": "Mock WhatsApp visitor"})
        response.raise_for_status()
        customer = response.json()
        events = [
            {"kind": "action", "action": "ask_home"},
            *(
                {"kind": "text", "text": answer}
                for answer in [
                    "8 feet",
                    "Bright daylight",
                    "Cricket and movies",
                    "Side seats",
                    "Reflections",
                    "Wall",
                    "70000",
                    "Correct",
                ]
            ),
        ]
        for values in events:
            payload = {
                "event_id": str(uuid4()),
                "customer_id": customer["id"],
                "version": customer["version"],
                **values,
            }
            response = client.post("/api/messaging/mock/events", json=payload)
            response.raise_for_status()
            result = response.json()
            for item in result["messages"]:
                print("\nBOT (simulated; " + item["status"] + ")")
                print("\n".join(item["message"]["lines"]))
                print("Buttons: " + " | ".join(b["label"] for b in item["message"]["buttons"]))
            response = client.get("/api/customers/" + customer["id"])
            response.raise_for_status()
            customer = response.json()
        print(f"\nSaved customer #{customer['serial']}: {customer['id']}")
        print("Resume this visit in the website. No WhatsApp message was sent.")


if __name__ == "__main__":
    main()
