#!/usr/bin/env python3
"""BlackRoad Archive — Distributed snapshot auditor"""
import hashlib, json, sqlite3, time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB = Path.home() / ".blackroad" / "archive_audit.db"
DB.parent.mkdir(parents=True, exist_ok=True)

@dataclass
class Snapshot:
    id: str
    repo: str
    version: str
    sha256: str
    size_bytes: int
    tags: list
    archived_at: str
    verified: bool = False

def init_db(db):
    db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        id TEXT PRIMARY KEY, repo TEXT, version TEXT,
        sha256 TEXT, size_bytes INTEGER, tags TEXT,
        archived_at TEXT, verified INTEGER DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id TEXT, action TEXT, result TEXT, at TEXT
    )""")
    db.commit()

class ArchiveAuditor:
    def __init__(self):
        self.db = sqlite3.connect(str(DB))
        self.db.row_factory = sqlite3.Row
        init_db(self.db)

    def register(self, snap: Snapshot):
        self.db.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?)",
            (snap.id, snap.repo, snap.version, snap.sha256,
             snap.size_bytes, json.dumps(snap.tags), snap.archived_at, snap.verified)
        )
        self.db.commit()
        self._log(snap.id, "register", "ok")

    def verify(self, snapshot_id: str, data: bytes) -> bool:
        row = self.db.execute("SELECT * FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if not row:
            return False
        computed = hashlib.sha256(data).hexdigest()
        ok = computed == row["sha256"]
        self.db.execute("UPDATE snapshots SET verified=? WHERE id=?", (int(ok), snapshot_id))
        self.db.commit()
        self._log(snapshot_id, "verify", "pass" if ok else "FAIL")
        return ok

    def _log(self, sid, action, result):
        self.db.execute(
            "INSERT INTO audit_log (snapshot_id, action, result, at) VALUES (?,?,?,?)",
            (sid, action, result, datetime.utcnow().isoformat())
        )
        self.db.commit()

    def report(self) -> dict:
        rows = self.db.execute("SELECT * FROM snapshots").fetchall()
        return {
            "total": len(rows),
            "verified": sum(1 for r in rows if r["verified"]),
            "unverified": sum(1 for r in rows if not r["verified"]),
            "snapshots": [dict(r) for r in rows],
        }

if __name__ == "__main__":
    auditor = ArchiveAuditor()
    # Sample snapshot registration
    auditor.register(Snapshot(
        id="snap-001", repo="blackroad-os-web", version="v1.2.0",
        sha256=hashlib.sha256(b"sample").hexdigest(),
        size_bytes=1024*1024*50, tags=["production", "verified"],
        archived_at=datetime.utcnow().isoformat()
    ))
    print(json.dumps(auditor.report(), indent=2))
