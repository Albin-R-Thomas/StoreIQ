"""Durable single-store storage with transactional updates and an audit trail."""

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("WEB_DATABASE_PATH", "data/store-iq.db"))


def now():
    return datetime.now(UTC).isoformat()


def uid():
    return secrets.token_urlsafe(16)


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


@contextmanager
def transaction():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def read_all(db, kind):
    return [
        json.loads(r[0])
        for r in db.execute("SELECT body FROM records WHERE kind=? ORDER BY rowid", (kind,))
    ]


def get(db, kind, key):
    row = db.execute("SELECT body FROM records WHERE kind=? AND id=?", (kind, key)).fetchone()
    return json.loads(row[0]) if row else None


def put(db, kind, item):
    db.execute(
        "INSERT INTO records(kind,id,body) VALUES(?,?,?) ON CONFLICT(kind,id) "
        "DO UPDATE SET body=excluded.body",
        (kind, item["id"], json.dumps(item)),
    )
    return item


def audit(db, actor, action, target):
    db.execute(
        "INSERT INTO audit(actor,action,target,created_at) VALUES(?,?,?,?)",
        (actor, action, target, now()),
    )


def initialize():
    demo = os.getenv("DEMO_MODE", "true").lower() == "true"
    allow_defaults = os.getenv("ALLOW_DEFAULT_PASSWORDS", "false").lower() == "true"
    with transaction() as db:
        db.execute("PRAGMA journal_mode")
        db.execute(
            "CREATE TABLE IF NOT EXISTS records(kind TEXT NOT NULL,id TEXT NOT NULL,"
            "body TEXT NOT NULL,PRIMARY KEY(kind,id))"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,"
            "action TEXT,target TEXT,created_at TEXT)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,"
            "window INTEGER NOT NULL,count INTEGER NOT NULL)"
        )
        if not read_all(db, "users"):
            for id_, name, phone, role, env, default in [
                (
                    "associate-1",
                    "Aarav Shah",
                    "9000000001",
                    "associate",
                    "ASSOCIATE_PASSWORD",
                    "Associate@123",
                ),
                (
                    "associate-2",
                    "Meera Patel",
                    "9000000002",
                    "associate",
                    "ASSOCIATE_TWO_PASSWORD",
                    "Associate@123",
                ),
                ("admin-1", "Priya Desai", "9000000009", "admin", "ADMIN_PASSWORD", "Admin@123"),
            ]:
                password = os.getenv(env, default if demo else "")
                default_allowed = allow_defaults and password == default
                if not password or (
                    not demo and not default_allowed and (len(password) < 12 or password == default)
                ):
                    raise RuntimeError(f"Configure a unique {env} with at least 12 characters")
                salt = secrets.token_hex(16)
                put(
                    db,
                    "users",
                    {
                        "id": id_,
                        "name": name,
                        "phone": phone,
                        "role": role,
                        "salt": salt,
                        "password": password_hash(password, salt),
                    },
                )
        if not read_all(db, "products"):
            from app.web.seed import seed

            seed(db)
        if not get(db, "commercial", "terms"):
            put(
                db,
                "commercial",
                {
                    "id": "terms",
                    "version": 1,
                    "delivery": 0,
                    "installation": 499,
                    "wall_mount": 1499,
                    "specialist_work": None,
                    "soundbar": 7999,
                    "protection": 3999,
                    "finance_months": 12,
                    "finance_fee": 999,
                    "finance_apr": 0,
                },
            )
        if not demo and not allow_defaults:
            for user in read_all(db, "users"):
                default = "Admin@123" if user["role"] == "admin" else "Associate@123"
                if password_hash(default, user["salt"]) == user["password"]:
                    raise RuntimeError(
                        "Demo passwords are forbidden outside DEMO_MODE. Rotate them first."
                    )
