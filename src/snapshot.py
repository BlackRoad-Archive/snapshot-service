"""
BlackRoad Archive — Snapshot Creation Script
Creates full system snapshots: SQLite DBs + configs → IPFS pin → local archive.
"""
from __future__ import annotations
import subprocess, hashlib, json, tarfile, os, time
from pathlib import Path
from datetime import datetime

ARCHIVE_DIR = Path.home() / ".blackroad" / "snapshots"
BLACKROAD_DIR = Path.home() / ".blackroad"
SNAPSHOT_MANIFEST = "manifest.json"


class SnapshotError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(include_patterns: list[str] | None = None) -> list[Path]:
    patterns = include_patterns or ["**/*.db", "**/*.json", "**/*.yaml", "**/*.toml"]
    files = []
    for pattern in patterns:
        files.extend(BLACKROAD_DIR.glob(pattern))
    return sorted(set(files))


def create_snapshot(label: str = "manual", include_patterns: list[str] | None = None) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    snap_name = f"blackroad-snap-{ts}-{label}"
    snap_path = ARCHIVE_DIR / f"{snap_name}.tar.gz"

    files = collect_files(include_patterns)
    manifest: dict = {
        "label": label,
        "created_at": datetime.now().isoformat(),
        "files": [],
        "total_bytes": 0,
    }

    print(f"Creating snapshot: {snap_name}")
    with tarfile.open(snap_path, "w:gz") as tar:
        for f in files:
            try:
                rel = f.relative_to(Path.home())
                checksum = sha256_file(f)
                size = f.stat().st_size
                tar.add(f, arcname=str(rel))
                manifest["files"].append({"path": str(rel), "sha256": checksum, "size": size})
                manifest["total_bytes"] += size
                print(f"  + {rel}  ({size} bytes)")
            except (PermissionError, OSError) as e:
                print(f"  ! Skipped {f}: {e}")

    # Write manifest inside the archive
    manifest_path = ARCHIVE_DIR / f"{snap_name}-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nSnapshot: {snap_path} ({manifest['total_bytes']} bytes, {len(manifest['files'])} files)")
    return snap_path


def pin_to_ipfs(snap_path: Path) -> str | None:
    """Pin snapshot to IPFS if available."""
    try:
        result = subprocess.run(
            ["ipfs", "add", "-q", str(snap_path)],
            capture_output=True, text=True, timeout=120
        )
        cid = result.stdout.strip()
        if cid:
            print(f"IPFS CID: {cid}")
            return cid
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("IPFS not available — skipping pin")
    return None


def list_snapshots() -> list[dict]:
    if not ARCHIVE_DIR.exists():
        return []
    snaps = []
    for f in sorted(ARCHIVE_DIR.glob("*.tar.gz"), reverse=True):
        manifest_path = ARCHIVE_DIR / f"{f.stem}-manifest.json"
        if manifest_path.exists():
            meta = json.loads(manifest_path.read_text())
        else:
            meta = {"label": "unknown", "files": [], "total_bytes": f.stat().st_size}
        snaps.append({"file": f.name, "size": f.stat().st_size, **meta})
    return snaps


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    if cmd == "create":
        label = sys.argv[2] if len(sys.argv) > 2 else "manual"
        snap = create_snapshot(label)
        pin_to_ipfs(snap)
    elif cmd == "list":
        for s in list_snapshots():
            print(f"{s['file']:60s}  {s['total_bytes']:>12,} bytes  {s.get('created_at','?')}")
    else:
        print("Usage: python3 snapshot.py [create [label] | list]")
