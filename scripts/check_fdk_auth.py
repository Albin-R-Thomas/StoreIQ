"""Small read-only auth matrix; credentials stay out of files and process arguments."""

import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import subprocess
from datetime import UTC, datetime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    app_id = os.getenv("FDK_APPLICATION_ID") or input("Application ID: ").strip()
    token = os.getenv("FDK_APPLICATION_TOKEN") or getpass.getpass("Application token: ")
    encoded = base64.b64encode(f"{app_id}:{token}".encode()).decode()
    results = []
    for slash in (False, True):
        url = (
            "https://reliance-digital.jiox5.de/service/application/catalog/v1.0/products"
            + ("/" if slash else "")
            + "?page_size=1&filters=true"
        )
        for mode in ("none", "Basic", "Bearer"):
            config = f'url = "{url}"\nheader = "Accept: application/json"\n'
            if mode != "none":
                config += f'header = "Authorization: {mode} {encoded}"\n'
            command = [
                "curl.exe", "--config", "-", "--silent", "--show-error",
                "--ssl-revoke-best-effort", "--max-time", "20",
                "--write-out", "\nFDK_META:%{http_code}|%{content_type}|%{redirect_url}",
            ]
            # Do not follow redirects: diagnose routing without forwarding credentials.
            response = subprocess.run(command, input=config, text=True, capture_output=True)
            body, separator, metadata = response.stdout.rpartition("\nFDK_META:")
            parts = metadata.split("|", 2) if separator else ["000", "", ""]
            result = dict(
                url=url, auth=mode, curl_exit=response.returncode,
                http_status=int(parts[0]), content_type=parts[1],
                redirect_url=parts[2], response_bytes=len(body.encode()),
            )
            try:
                payload = json.loads(body)
                result["json"] = True
                result["catalogue_shape"] = isinstance(payload, dict) and isinstance(payload.get("items"), list)
                if result["catalogue_shape"]:
                    result["items_count"] = len(payload["items"])
            except ValueError:
                result.update(json=False, catalogue_shape=False)
            result["access_denied_html"] = "access denied" in body.lower()
            result["storefront_not_found"] = "page was not found" in body.lower()
            results.append(result)
            print(json.dumps(result), flush=True)
            if result["http_status"] == 429:
                break
        if results[-1]["http_status"] == 429:
            break
    report = {"recorded_at_utc": datetime.now(UTC).isoformat(), "cases": results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
