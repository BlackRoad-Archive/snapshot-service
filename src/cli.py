#!/usr/bin/env python3
"""
BlackRoad Snapshot CLI — create, list, restore, and verify snapshots.
"""

import argparse
import json
import sys
from pathlib import Path
from snapshot import SnapshotService


def cmd_create(args):
    svc = SnapshotService(args.output_dir)
    path = svc.create_snapshot(args.source, args.tag)
    print(f"✓ Snapshot created: {path}")


def cmd_list(args):
    svc = SnapshotService(args.output_dir)
    snaps = svc.list_snapshots()
    if not snaps:
        print("No snapshots found.")
        return
    print(f"{'ID':<20} {'Tag':<20} {'Size':<12} {'Created':<25} Hash")
    print("-" * 90)
    for s in snaps:
        snap_id = s.get("snapshot_id", "")[:18]
        tag = s.get("tag", "")[:18]
        size = f"{s.get('size_bytes', 0):,}"
        created = s.get("created_at", "")[:24]
        h = s.get("hash", "")[:12]
        print(f"{snap_id:<20} {tag:<20} {size:<12} {created:<25} {h}")


def cmd_verify(args):
    svc = SnapshotService(args.output_dir)
    ok = svc.verify_snapshot(args.snapshot_id)
    if ok:
        print(f"✓ Snapshot {args.snapshot_id[:16]}... is valid")
    else:
        print(f"✗ Snapshot {args.snapshot_id[:16]}... FAILED verification", file=sys.stderr)
        sys.exit(1)


def cmd_restore(args):
    svc = SnapshotService(args.output_dir)
    ok = svc.restore_snapshot(args.snapshot_id, args.destination)
    if ok:
        print(f"✓ Restored to {args.destination}")
    else:
        print("✗ Restore failed", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="BlackRoad Snapshot Service CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  snapshot create ./src --tag v1.0.0 --output-dir /backups
  snapshot list --output-dir /backups
  snapshot verify abc123... --output-dir /backups
  snapshot restore abc123... /restore/path --output-dir /backups
        """
    )
    parser.add_argument("--output-dir", default="./snapshots", help="Snapshot storage directory")
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p = sub.add_parser("create", help="Create a new snapshot")
    p.add_argument("source", help="Directory or file to snapshot")
    p.add_argument("--tag", default="", help="Optional tag label")
    p.set_defaults(func=cmd_create)

    # list
    p = sub.add_parser("list", help="List all snapshots")
    p.set_defaults(func=cmd_list)

    # verify
    p = sub.add_parser("verify", help="Verify snapshot integrity via PS-SHA∞")
    p.add_argument("snapshot_id", help="Snapshot ID to verify")
    p.set_defaults(func=cmd_verify)

    # restore
    p = sub.add_parser("restore", help="Restore a snapshot")
    p.add_argument("snapshot_id", help="Snapshot ID to restore")
    p.add_argument("destination", help="Destination path")
    p.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
