"""Read-only UAT routing/auth diagnostics. No credentials are embedded in this file."""

import argparse
import base64
from datetime import UTC, datetime
import getpass
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode


HOSTS = {
    "storefront": "https://reliance-digital.jiox5.de",
    "platform": "https://platform.jiox5.de",
    "partners": "https://partners.jiox5.de",
}
PATHS = {
    "products": "/service/application/catalog/v1.0/products",
    "promotions": "/service/application/cart/v1.0/available-promotions",
}


def variants(app_id, token):
    pair = f"{app_id}:{token}"
    encoded = base64.b64encode(pair.encode()).decode()
    values = {
        "encoded_pair": encoded,
        "basic_encoded_pair": "Basic " + encoded,
        "bearer_encoded_pair": "Bearer " + encoded,
        "raw_token": token,
        "basic_raw_token": "Basic " + token,
        "bearer_raw_token": "Bearer " + token,
        "raw_pair": pair,
    }
    yield "no_auth", {}, {}, "baseline"
    for label, value in values.items():
        support = "source-backed candidate" if label in {
            "basic_encoded_pair", "bearer_encoded_pair"
        } else "speculative"
        yield "header_" + label, {"Authorization": value}, {}, support
    for key in ("authorization", "token"):
        for label, value in values.items():
            yield f"query_{key}_{label}", {}, {key: value}, "speculative"
    yield "query_application_pair", {}, {
        "application_id": app_id, "application_token": token
    }, "speculative"
    yield "query_app_pair", {}, {"app_id": app_id, "app_token": token}, "speculative"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosts", nargs="+", choices=HOSTS, default=list(HOSTS))
    parser.add_argument("--endpoint", choices=PATHS, default="products")
    parser.add_argument("--trailing-slash", action="store_true", help="Also test a trailing slash")
    parser.add_argument("--headers-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="List cases without credentials or HTTP")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--output", type=Path, default=Path("tmp/review/fdk-auth-matrix-expanded.json"))
    args = parser.parse_args()
    if args.delay < 0 or args.timeout < 1:
        parser.error("delay must be nonnegative and timeout must be positive")
    app_id = "DRY_RUN_ID" if args.dry_run else (
        os.getenv("FDK_APPLICATION_ID") or input("Application ID: ").strip()
    )
    token = "DRY_RUN_TOKEN" if args.dry_run else (
        os.getenv("FDK_APPLICATION_TOKEN") or getpass.getpass("Application token: ")
    )
    if not app_id or not token:
        parser.error("Both credentials are required")
    cases = list(variants(app_id, token))
    if args.headers_only:
        cases = [case for case in cases if not case[2]]
    report = {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "note": "Platform and Partners are portal origins, not confirmed REST bases. Query auth is speculative.",
        "cases": [],
    }
    print(report["note"])
    if not args.headers_only:
        print("Query cases send credentials in URLs, which remote infrastructure may log.")
    try:
        for host in args.hosts:
            for slash in ((False, True) if args.trailing_slash else (False,)):
                endpoint = HOSTS[host] + PATHS[args.endpoint] + ("/" if slash else "")
                for name, headers, query, support in cases:
                    params = {"page_size": "1"}
                    if args.endpoint == "products":
                        params["filters"] = "true"
                    params.update(query)
                    url = endpoint + "?" + urlencode(params)
                    safe_url = endpoint + "?" + urlencode({
                        k: "[REDACTED]" if k in query else v for k, v in params.items()
                    })
                    row = {"host": host, "case": name, "support": support, "url": safe_url}
                    if args.dry_run:
                        print(json.dumps(row))
                        continue
                    # JSON quoting safely encodes curl config strings, not shell text.
                    config = "url = " + json.dumps(url) + "\n"
                    for key, value in {"Accept": "application/json", **headers}.items():
                        config += "header = " + json.dumps(f"{key}: {value}") + "\n"
                    command = [
                        "curl.exe", "--config", "-", "--silent", "--show-error",
                        "--ssl-revoke-best-effort", "--max-time", str(args.timeout),
                        "--write-out", "\nFDK_META:%{http_code}|%{content_type}|%{num_redirects}",
                    ]
                    result = subprocess.run(command, input=config, text=True, capture_output=True)
                    body, separator, meta = result.stdout.rpartition("\nFDK_META:")
                    status, content_type, _ = meta.split("|", 2) if separator else ("000", "", "0")
                    row.update(curl_exit=result.returncode, http_status=int(status), content_type=content_type)
                    try:
                        payload = json.loads(body)
                        key = "items" if args.endpoint == "products" else "available_promotions"
                        shape = isinstance(payload, dict) and isinstance(payload.get(key), list)
                        row.update(json=True, expected_shape=shape)
                        if shape:
                            row["item_count"] = len(payload[key])
                    except ValueError:
                        row.update(json=False, expected_shape=False)
                    row["success"] = row["http_status"] == 200 and row["expected_shape"]
                    row["access_denied_html"] = "access denied" in body.lower()
                    row["storefront_not_found"] = "page was not found" in body.lower()
                    # Never save bodies, request headers, stderr or redirect URLs: they may echo secrets.
                    report["cases"].append(row)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
                    print(json.dumps(row), flush=True)
                    if row["http_status"] == 429:
                        print("Stopped on HTTP 429. Results saved.")
                        return
                    time.sleep(args.delay)
    except KeyboardInterrupt:
        print("Stopped. Completed results have been saved.")
    except FileNotFoundError:
        parser.exit(1, "curl.exe not found. Run this script on Windows with curl installed.\n")


if __name__ == "__main__":
    main()
