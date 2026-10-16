"""SQLite storage: passports, bot conversations, processed WhatsApp message IDs, check counters.

Phone numbers are never stored. Conversations are keyed by an HMAC of the WhatsApp ID.
Scam-check text is not stored, only a SHA-256 of it and the verdict, for aggregate counts.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seq (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS passports (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, credential TEXT NOT NULL, signature TEXT NOT NULL,
  assurance TEXT NOT NULL, owner_hash TEXT NOT NULL, evidence_path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (user_hash TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS seen_messages (msg_id TEXT PRIMARY KEY, seen_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, channel TEXT NOT NULL,
  verdict TEXT NOT NULL, score INTEGER NOT NULL, text_sha TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        c = self._conn()
        try:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(_SCHEMA)
        finally:
            c.close()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        c.row_factory = sqlite3.Row
        return c

    @contextmanager
    def _tx(self):
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except BaseException:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    # ---- passports
    def next_seq(self, name: str) -> int:
        with self._tx() as c:
            c.execute("INSERT INTO seq(name, value) VALUES(?, 1) ON CONFLICT(name) DO UPDATE SET value = value + 1", (name,))
            return c.execute("SELECT value FROM seq WHERE name = ?", (name,)).fetchone()[0]

    def add_passport(self, *, id: str, credential: dict, signature: str, assurance: str,
                     owner_hash: str, evidence_path: str) -> None:
        with self._tx() as c:
            c.execute("INSERT INTO passports VALUES(?,?,?,?,?,?,?)",
                      (id, _now(), json.dumps(credential, ensure_ascii=False), signature, assurance, owner_hash, evidence_path))

    def get_passport(self, id: str) -> dict | None:
        c = self._conn()
        try:
            r = c.execute("SELECT * FROM passports WHERE id = ?", (id,)).fetchone()
        finally:
            c.close()
        if not r:
            return None
        d = dict(r)
        d["credential"] = json.loads(d["credential"])
        return d

    def get_demo_passport(self) -> dict | None:
        c = self._conn()
        try:
            r = c.execute("SELECT id FROM passports WHERE owner_hash = 'demo' ORDER BY created_at LIMIT 1").fetchone()
        finally:
            c.close()
        return self.get_passport(r["id"]) if r else None

    # ---- conversations
    def get_conversation(self, key: str) -> dict | None:
        c = self._conn()
        try:
            r = c.execute("SELECT state FROM conversations WHERE user_hash = ?", (key,)).fetchone()
        finally:
            c.close()
        return json.loads(r["state"]) if r else None

    def save_conversation(self, key: str, conv: dict) -> None:
        with self._tx() as c:
            c.execute("INSERT INTO conversations VALUES(?,?,?) ON CONFLICT(user_hash) DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at",
                      (key, json.dumps(conv, ensure_ascii=False), time.time()))

    def delete_conversation(self, key: str) -> None:
        with self._tx() as c:
            c.execute("DELETE FROM conversations WHERE user_hash = ?", (key,))

    # ---- WhatsApp de-duplication
    def mark_seen(self, msg_id: str) -> bool:
        """True the first time an ID is seen, False for a redelivery."""
        with self._tx() as c:
            cur = c.execute("INSERT OR IGNORE INTO seen_messages VALUES(?,?)", (msg_id, time.time()))
            return cur.rowcount == 1

    # ---- counters
    def log_check(self, channel: str, verdict: str, score: int, text_sha: str) -> None:
        with self._tx() as c:
            c.execute("INSERT INTO checks(ts, channel, verdict, score, text_sha) VALUES(?,?,?,?,?)",
                      (_now(), channel, verdict, score, text_sha))

    def stats(self) -> dict:
        c = self._conn()
        try:
            total = c.execute("SELECT COUNT(*) FROM passports").fetchone()[0]
            demo = c.execute("SELECT COUNT(*) FROM passports WHERE assurance = 'demo'").fetchone()[0]
            by = {r["verdict"]: r["n"] for r in c.execute("SELECT verdict, COUNT(*) AS n FROM checks GROUP BY verdict")}
        finally:
            c.close()
        return {"passports_issued": total, "demo_passports": demo,
                "messages_checked": sum(by.values()), "checks_by_verdict": by}

    def purge_stale(self, days: int = 7) -> int:
        cutoff = time.time() - days * 86400
        with self._tx() as c:
            a = c.execute("DELETE FROM conversations WHERE updated_at < ?", (cutoff,)).rowcount
            b = c.execute("DELETE FROM seen_messages WHERE seen_at < ?", (cutoff,)).rowcount
        return a + b
