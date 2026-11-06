"""Rotate a local account password and revoke its sessions. Password never echoes."""

import getpass
import secrets
import sys

from app.web.store import audit, password_hash, put, read_all, transaction

if len(sys.argv) != 2:
    raise SystemExit("Usage: python -m scripts.rotate_web_password <account-phone>")
password = getpass.getpass("New password (12+ characters): ")
if len(password) < 12 or password in ("Associate@123", "Admin@123"):
    raise SystemExit("Choose a unique password with at least 12 characters.")
if password != getpass.getpass("Repeat password: "):
    raise SystemExit("Passwords did not match.")
with transaction() as db:
    user = next((u for u in read_all(db, "users") if u["phone"] == sys.argv[1]), None)
    if not user:
        raise SystemExit("Account not found.")
    user["salt"] = secrets.token_hex(16)
    user["password"] = password_hash(password, user["salt"])
    put(db, "users", user)
    for session in read_all(db, "auth"):
        if session["user_id"] == user["id"]:
            db.execute("DELETE FROM records WHERE kind='auth' AND id=?", (session["id"],))
    audit(db, "local-operator", "rotate_password", user["id"])
print("Password rotated; existing sessions revoked.")
