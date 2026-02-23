#!/usr/bin/env python3
"""
BlackRoad Archive — Repository Snapshot Tool
Creates timestamped archives of repos with hash verification.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ARCHIVE_DIR = Path.home() / ".blackroad" / "archive"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def snapshot_directory(target: Path, label: str = "") -> dict:
    """
    Create a snapshot manifest for a directory.
    Returns dict with file hashes, timestamp, and total size.
    """
    if not target.exists():
        raise FileNotFoundError(f"Target not found: {target}")

    timestamp = datetime.utcnow().isoformat() + "Z"
    manifest = {
        "label": label or target.name,
        "source": str(target),
        "timestamp": timestamp,
        "files": {},
        "total_size": 0,
        "file_count": 0,
    }

    for path in sorted(target.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            rel = str(path.relative_to(target))
            size = path.stat().st_size
            manifest["files"][rel] = {
                "sha256": sha256_file(path),
                "size": size,
            }
            manifest["total_size"] += size
            manifest["file_count"] += 1

    return manifest


def save_snapshot(manifest: dict) -> Path:
    """Save snapshot manifest to archive directory."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = manifest["timestamp"].replace(":", "-").replace(".", "-")
    out = ARCHIVE_DIR / f"snapshot-{manifest['label']}-{ts}.json"
    out.write_text(json.dumps(manifest, indent=2))
    return out


def verify_snapshot(manifest_path: Path, target: Path) -> tuple[bool, list[str]]:
    """
    Verify a directory against a saved snapshot.
    Returns (all_match, list_of_differences).
    """
    with open(manifest_path) as f:
        manifest = json.load(f)

    diffs = []
    for rel, info in manifest["files"].items():
        path = target / rel
        if not path.exists():
            diffs.append(f"MISSING: {rel}")
            continue
        current = sha256_file(path)
        if current != info["sha256"]:
            diffs.append(f"CHANGED: {rel}")

    # Check for new files
    for path in sorted(target.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            rel = str(path.relative_to(target))
            if rel not in manifest["files"]:
                diffs.append(f"ADDED: {rel}")

    return len(diffs) == 0, diffs


def list_snapshots() -> list[Path]:
    if not ARCHIVE_DIR.exists():
        return []
    return sorted(ARCHIVE_DIR.glob("snapshot-*.json"), reverse=True)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage:")
        print("  snapshot.py create <dir> [label]  — Create snapshot")
        print("  snapshot.py verify <manifest> <dir> — Verify snapshot")
        print("  snapshot.py list                   — List saved snapshots")
        sys.exit(0)

    cmd = args[0]

    if cmd == "create":
        target = Path(args[1]).expanduser().resolve()
        label = args[2] if len(args) > 2 else ""
        print(f"Creating snapshot of {target}...")
        manifest = snapshot_directory(target, label)
        out = save_snapshot(manifest)
        print(f"✓ Snapshot saved: {out}")
        print(f"  Files: {manifest['file_count']} | Size: {manifest['total_size']:,} bytes")

    elif cmd == "verify":
        manifest_path = Path(args[1]).expanduser().resolve()
        target = Path(args[2]).expanduser().resolve()
        print(f"Verifying {target} against {manifest_path.name}...")
        valid, diffs = verify_snapshot(manifest_path, target)
        if valid:
            print("✓ Snapshot matches — no changes detected")
        else:
            print(f"✗ {len(diffs)} difference(s) found:")
            for d in diffs:
                print(f"  {d}")
            sys.exit(1)

    elif cmd == "list":
        snaps = list_snapshots()
        if not snaps:
            print("No snapshots found in ~/.blackroad/archive/")
            return
        for s in snaps:
            data = json.loads(s.read_text())
            print(f"{s.name}  —  {data['label']}  ({data['file_count']} files, {data['total_size']:,} bytes)")


if __name__ == "__main__":
    main()
