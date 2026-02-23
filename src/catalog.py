#!/usr/bin/env python3
"""
BlackRoad Archive — Version Catalog
Track all deployed versions of BlackRoad services.
"""
import os, json, sqlite3, hashlib
from datetime import datetime
from typing import Optional

DB_PATH = os.path.expanduser("~/.blackroad/version-catalog.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            version TEXT NOT NULL,
            environment TEXT NOT NULL DEFAULT 'production',
            deployed_at TEXT DEFAULT (datetime('now')),
            deployed_by TEXT DEFAULT 'ci',
            commit_sha TEXT,
            changelog TEXT,
            status TEXT DEFAULT 'active',
            rollback_version TEXT,
            UNIQUE(service, version, environment)
        )
    """)
    conn.commit()
    return conn

def record_deploy(service: str, version: str, commit_sha: str = "",
                  changelog: str = "", environment: str = "production") -> int:
    db = get_db()
    # Mark previous as superseded
    db.execute(
        "UPDATE versions SET status='superseded' WHERE service=? AND environment=? AND status='active'",
        (service, environment)
    )
    cursor = db.execute(
        """INSERT OR REPLACE INTO versions
        (service, version, environment, commit_sha, changelog, deployed_by)
        VALUES (?, ?, ?, ?, ?, 'blackroad-ci')""",
        (service, version, environment, commit_sha, changelog)
    )
    db.commit()
    print(f"✓ Recorded: {service}@{version} → {environment}")
    return cursor.lastrowid

def get_latest(service: str, environment: str = "production") -> Optional[dict]:
    db = get_db()
    row = db.execute(
        "SELECT * FROM versions WHERE service=? AND environment=? AND status='active' ORDER BY deployed_at DESC LIMIT 1",
        (service, environment)
    ).fetchone()
    return dict(row) if row else None

def rollback(service: str, environment: str = "production") -> Optional[dict]:
    db = get_db()
    current = get_latest(service, environment)
    if not current:
        print(f"✗ No active version for {service}/{environment}")
        return None
    # Get the version before current
    prev = db.execute(
        """SELECT * FROM versions WHERE service=? AND environment=? AND status='superseded'
        ORDER BY deployed_at DESC LIMIT 1""",
        (service, environment)
    ).fetchone()
    if not prev:
        print(f"✗ No previous version to roll back to")
        return None
    
    # Restore previous
    db.execute("UPDATE versions SET status='active' WHERE id=?", (prev["id"],))
    db.execute("UPDATE versions SET status='rolled-back' WHERE id=?", (current["id"],))
    db.commit()
    print(f"↩ Rolled back {service}/{environment} to {prev['version']}")
    return dict(prev)

def list_services() -> list:
    db = get_db()
    rows = db.execute(
        "SELECT service, version, environment, deployed_at, status FROM versions WHERE status='active' ORDER BY service, environment"
    ).fetchall()
    return [dict(r) for r in rows]

# Seed with known BlackRoad services
SERVICES = [
    ("blackroad-gateway", "0.3.0", "d3f8e9a", "Tokenless gateway with PS-SHA∞ storage"),
    ("blackroad-api", "0.4.1", "9c2b1f4", "Task marketplace + memory chain"),
    ("blackroad-web", "1.2.0", "7a5d3e8", "Next.js agent dashboard"),
    ("blackroad-sdk", "0.1.0", "2f9c4b1", "TypeScript + Python SDK"),
    ("blackroad-agents", "0.2.3", "1e8a7c5", "6 core agent classes"),
    ("blackroad-math", "0.1.5", "4b2f8d9", "PS-SHA∞ formal proofs"),
    ("blackroad-infra", "0.5.0", "8c3a1e7", "K8s + Terraform IaC"),
]

if __name__ == "__main__":
    for svc, ver, sha, log in SERVICES:
        record_deploy(svc, ver, sha, log)
    
    print("
=== Active Versions ===")
    for s in list_services():
        print(f"  {s['service']:25} {s['version']:10} {s['environment']:12} {s['deployed_at'][:10]}")
