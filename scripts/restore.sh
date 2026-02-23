#!/usr/bin/env bash
# BlackRoad Archive — Disaster Recovery Restore Script
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()   { echo -e "${GREEN}✓${NC} $1"; }
info()  { echo -e "${CYAN}→${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1" >&2; exit 1; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }

SNAPSHOTS_DIR="${SNAPSHOTS_DIR:-./snapshots}"
RESTORE_DIR="${RESTORE_DIR:-./restored}"

cmd_list() {
    info "Available snapshots:"
    ls -1t "$SNAPSHOTS_DIR"/*.tar.gz 2>/dev/null | while read f; do
        size=$(du -sh "$f" | cut -f1)
        date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$f" 2>/dev/null || stat -c "%y" "$f" | cut -d' ' -f1,2 | cut -d'.' -f1)
        echo "  $(basename $f)  [$size]  $date"
    done
}

cmd_restore() {
    local snapshot="${1:-}"
    local target="${2:-$RESTORE_DIR}"
    [ -z "$snapshot" ] && error "Usage: $0 restore <snapshot.tar.gz> [target-dir]"
    [ ! -f "$snapshot" ] && snapshot="$SNAPSHOTS_DIR/$snapshot"
    [ ! -f "$snapshot" ] && error "Snapshot not found: $snapshot"

    mkdir -p "$target"
    info "Restoring $(basename $snapshot) → $target"
    tar -xzf "$snapshot" -C "$target"
    log "Restored to $target"

    # Verify hash if manifest exists
    local manifest="$target/MANIFEST.sha256"
    if [ -f "$manifest" ]; then
        info "Verifying checksums..."
        (cd "$target" && sha256sum --check "$manifest" --quiet)
        log "All checksums verified"
    fi
}

cmd_from_ipfs() {
    local cid="${1:-}"
    [ -z "$cid" ] && error "Usage: $0 from-ipfs <CID>"
    info "Fetching from IPFS: $cid"
    if command -v ipfs &>/dev/null; then
        ipfs get "$cid" -o "$RESTORE_DIR/$cid"
    else
        mkdir -p "$RESTORE_DIR"
        curl -sL "https://ipfs.io/ipfs/$cid" -o "$RESTORE_DIR/$cid.tar.gz"
    fi
    log "Fetched to $RESTORE_DIR/$cid"
    cmd_restore "$RESTORE_DIR/$cid.tar.gz" "$RESTORE_DIR/$cid-extracted"
}

case "${1:-help}" in
    list)         cmd_list ;;
    restore)      cmd_restore "${2:-}" "${3:-}" ;;
    from-ipfs)    cmd_from_ipfs "${2:-}" ;;
    *)
        echo "Usage: $0 <command>"
        echo "  list                        List available snapshots"
        echo "  restore <file> [target]     Restore a snapshot"
        echo "  from-ipfs <CID>             Restore from IPFS CID"
        ;;
esac
