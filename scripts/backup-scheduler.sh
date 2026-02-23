#!/usr/bin/env bash
# BlackRoad Archive — Automated Backup Scheduler
# Install: crontab -e
#   0 2 * * * /Users/alexa/blackroad/tools/backup/backup-scheduler.sh >> ~/.blackroad/logs/backup.log 2>&1
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
log()   { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) ${GREEN}✓${NC} $1"; }
error() { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) ${RED}✗${NC} $1" >&2; }
info()  { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) ${CYAN}→${NC} $1"; }

BACKUP_DIR="${BACKUP_DIR:-$HOME/.blackroad/backups}"
SNAPSHOTS_DIR="${SNAPSHOTS_DIR:-$BACKUP_DIR/snapshots}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)

mkdir -p "$SNAPSHOTS_DIR"

# ── SQLite databases ─────────────────────────────────────────────
backup_databases() {
    info "Backing up SQLite databases..."
    local DB_BACKUP="$SNAPSHOTS_DIR/databases-$TIMESTAMP"
    mkdir -p "$DB_BACKUP"
    
    find "$HOME/.blackroad" -name "*.db" -newer "$BACKUP_DIR/.last_backup" 2>/dev/null | while read db; do
        local name=$(basename "$db")
        sqlite3 "$db" ".backup $DB_BACKUP/$name"
        log "  ↳ $name"
    done
    
    tar -czf "$SNAPSHOTS_DIR/databases-$TIMESTAMP.tar.gz" -C "$SNAPSHOTS_DIR" "databases-$TIMESTAMP"
    rm -rf "$DB_BACKUP"
}

# ── Configuration files ────────────────────────────────────────
backup_configs() {
    info "Backing up configs..."
    tar -czf "$SNAPSHOTS_DIR/configs-$TIMESTAMP.tar.gz" \
        --exclude='*.db' --exclude='*.log' --exclude='.git' \
        "$HOME/.blackroad/vault" 2>/dev/null || true
    log "Configs backed up"
}

# ── IPFS pin (if available) ───────────────────────────────────
pin_to_ipfs() {
    info "Pinning to IPFS..."
    if command -v ipfs &>/dev/null; then
        for f in "$SNAPSHOTS_DIR"/*-"$TIMESTAMP".tar.gz; do
            local cid
            cid=$(ipfs add -q "$f" 2>/dev/null)
            log "  ↳ $(basename $f) → ipfs://$cid"
            echo "$TIMESTAMP $(basename $f) $cid" >> "$BACKUP_DIR/ipfs-pins.log"
        done
    else
        info "IPFS not available — skipping pin"
    fi
}

# ── Cleanup old backups ───────────────────────────────────────
cleanup() {
    info "Removing backups older than $RETENTION_DAYS days..."
    find "$SNAPSHOTS_DIR" -name "*.tar.gz" -mtime "+$RETENTION_DAYS" -delete
    log "Cleanup done"
}

# ── Main ─────────────────────────────────────────────────────
main() {
    info "=== BlackRoad Backup — $TIMESTAMP ==="
    backup_databases
    backup_configs
    pin_to_ipfs
    cleanup
    touch "$BACKUP_DIR/.last_backup"
    log "=== Backup complete ==="
}

main "$@"
